from asyncio.tasks import Task
from typing import Any, Callable, Dict, List, NoReturn, Tuple, Type, get_type_hints
from alpyro_msgs import RosMessage
from dataclasses import dataclass

from asyncio import BaseProtocol, BaseTransport, get_event_loop, sleep
from alpyro.xmlrpc import XMLRPCServer
from alpyro.tcp import TCPROSClient, TCPROSServer

from xmlrpc.client import ServerProxy

MASTER = "http://localhost:11311/"


def get_callback_type(f: Callable[[Any], None]) -> Type[RosMessage]:
    hints = get_type_hints(f)
    it = iter(hints.items())

    _, typ = next(it)
    assert issubclass(typ, RosMessage)

    arg, _ = next(it, ("return", ""))
    assert arg == "return"

    return typ


@dataclass
class Subscription:
    topic: str
    publisher: str
    transport: BaseTransport
    protocol: BaseProtocol


class Node(XMLRPCServer):
    name: str
    subs: Dict[str, Dict[str, Subscription]] = {}
    pubs: Dict[str, Dict[str, TCPROSServer]] = {}
    pub_typ: Dict[str, Type[RosMessage]] = {}

    callbacks: Dict[str, Tuple[Callable[[Any], None], Type[RosMessage]]] = {}

    def __init__(self, name: str) -> None:
        super().__init__(loop=get_event_loop())
        self.name = name

    def __enter__(self):
        self.create_server()
        self.m = ServerProxy(MASTER)
        code, *_ = self.m.getSystemState(self.name)
        assert code == 1
        return self

    def __exit__(self, type, value, traceback):
        for sub_topic, subs in self.subs.items():
            code, msg, _ = self.m.unregisterSubscriber(self.name, sub_topic, self.uri)
            assert code == 1

            for sub in subs.values():
                sub.transport.close()

        for pub_topic, pubs in self.pubs.items():
            code, msg, _ = self.m.unregisterPublisher(self.name, pub_topic, self.uri)
            assert code == 1

        self.loop_server.close()
        self.loop.stop()

    async def __subscribe__(self, pub: str, topic: str, typ: Type[RosMessage], callback: Callable[[Any], None]) -> None:
        if topic in self.subs and pub in self.subs[topic]:
            return

        print(f"requesting topic {topic} from {pub}")

        code, status, params = ServerProxy(pub).requestTopic(self.name, topic, [["TCPROS"]])  # type: ignore
        prot, hostname, port = params  # type: ignore

        transport, protocol = await self.loop.create_connection(
            lambda: TCPROSClient(callback, typ, self.name, topic), hostname, port
        )

        self.subs[topic][pub] = Subscription(topic, pub, transport, protocol)

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        typ = get_callback_type(callback)

        code, msg, pubs  = self.m.registerSubscriber(self.name, topic, typ.__msg_typ__, self.uri) #type: ignore
        assert code == 1

        self.callbacks[topic] = (callback, typ)
        self.subs[topic] = {}

        for p in pubs: #type: ignore
            self.loop.create_task(self.__subscribe__(p, topic, typ, callback))

    def announce(self, topic: str, typ: Type[RosMessage]) -> None:
        code, msg, subs = self.m.registerPublisher(self.name, topic, typ.__msg_typ__, self.uri) #type: ignore
        self.pubs[topic] = {}
        self.pub_typ[topic] = typ

    def run_forever(self) -> None:
        self.loop.run_forever()

    def __delete_pub_serv(self, topic: str, callerid: str) -> None:
        if callerid in self.pubs[topic]:  # avoid double free
            del self.pubs[topic][callerid]

    async def __pub(self, topic: str, rate: int, f: Callable[[], RosMessage]) -> None:
        # TODO cancel this coro when no subscriber are there and restart it again later
        while self.loop.is_running():
            msg = f()

            for ps in self.pubs[topic].values():
                ps.publish(msg)

            await sleep(1.0 / rate)

    def schedule_publish(self, topic: str, rate: int, f: Callable[[], RosMessage]):
        self.loop.create_task(self.__pub(topic, rate, f))

    # XML node API methods

    async def publisherUpdate(self, callerid: str, topic: str, publisher: List[str]) -> None:
        callback, typ = self.callbacks[topic]

        cur_subs = set(self.subs[topic].keys())

        for pub in publisher:
            await self.__subscribe__(pub, topic, typ, callback)
            if pub in cur_subs:
                cur_subs.remove(pub)

        for dead_pub in cur_subs:
            self.subs[topic][dead_pub].transport.close()
            del self.subs[topic][dead_pub].protocol
            del self.subs[topic][dead_pub]

    async def requestTopic(self, callerid: str, topic: str, protocols: List[List[str]]) -> Tuple[int, str, List[Any]]:
        print(f"Node {callerid} wants to get {topic}, creating server for it")
        ros_server = TCPROSServer(self.pub_typ[topic], self.name, topic, callerid, self.__delete_pub_serv)

        server = await self.loop.create_server(lambda: ros_server, "127.0.0.1", 0)
        assert server

        addr, port = server.sockets[0].getsockname()  # type: ignore
        self.pubs[topic][callerid] = ros_server

        code = 1
        msg = "TODO FIXME"
        proto_params = ["TCPROS", addr, port]

        return (code, msg, proto_params)
