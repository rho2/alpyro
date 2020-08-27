import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, get_args, get_origin, get_type_hints
from alpyro_msgs import RosMessage
from dataclasses import dataclass
from asyncio import BaseProtocol, BaseTransport, get_event_loop, sleep
from alpyro.xmlrpc import XMLRPCServer, XMLRPCValue
from alpyro.tcp import TCPROSClient, TCPROSServer
from xmlrpc.client import ServerProxy
import os

# this should be List[Tuple[str, XMLRPCValue, ...]] but such as construct is not allowed
_PROTO_INFO = List[Tuple[str, ...]]

_MSG_FACTORY = Union[
    Callable[[], RosMessage],
    Callable[["Node"], RosMessage],
    Callable[[Optional[RosMessage]],  RosMessage],
    Callable[[Optional[RosMessage], "Node"],  RosMessage],
    Callable[["Node", Optional[RosMessage]],  RosMessage],
]

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
    core: str

    subs: Dict[str, Dict[str, Subscription]]
    pubs: Dict[str, Dict[str, TCPROSServer]]
    topic_typ: Dict[str, Type[RosMessage]]

    callbacks: Dict[str, Callable[[Any], None]]

    def __init__(self, name: str, core: Optional[str] = None) -> None:
        super().__init__(loop=get_event_loop())
        self.name = name
        self.subs = {}
        self.pubs = {}
        self.topic_typ = {}
        self.callbacks = {}

        self.core = core if core else os.getenv("ROS_MASTER_URI", "http://localhost:11311/")

    def __enter__(self):
        self.create_server()
        self.m = ServerProxy(self.core)
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

        self.callbacks[topic] = callback
        self.topic_typ[topic] = typ
        self.subs[topic] = {}

        for p in pubs: #type: ignore
            self.loop.create_task(self.__subscribe__(p, topic, typ, callback))

    def announce(self, topic: str, typ: Type[RosMessage]) -> None:
        code, msg, subs = self.m.registerPublisher(self.name, topic, typ.__msg_typ__, self.uri) #type: ignore
        self.pubs[topic] = {}
        self.topic_typ[topic] = typ

    def run_forever(self) -> None:
        self.loop.run_forever()

    def __delete_pub_serv(self, topic: str, callerid: str) -> None:
        if callerid in self.pubs[topic]:  # avoid double free
            del self.pubs[topic][callerid]

    async def __pub(self, topic: str, rate: int, f: _MSG_FACTORY) -> None:
        # TODO cancel this coro when no subscriber are there and restart it again later
        msg = None

        depends = get_type_hints(f)
        del depends["return"]

        include_msg = ""
        include_self = ""
        for name, typ in depends.items():
            if get_origin(typ) == Union:
                ros_typ, none = get_args(typ)
                assert issubclass(ros_typ, RosMessage)
                assert none == type(None)
                include_msg = name
            elif typ == Node:
                include_self = name
            else:
                raise Exception(f"Typ {typ} cant be inserted")

        while self.loop.is_running():
            args: Dict[str, Any] = {}
            if include_msg:
                args[include_msg]  = msg
            if include_self:
                args[include_self] = self

            msg = f(**args) #type: ignore

            for ps in self.pubs[topic].values():
                ps.publish(msg)

            await sleep(1.0 / rate)

    def schedule_publish(self, topic: str, rate: int, f:_MSG_FACTORY):
        self.loop.create_task(self.__pub(topic, rate, f))

    # XML node API methods
    # TODO
    async def getBusState(self, caller_id: str) -> Tuple[int, str, List[XMLRPCValue]]:
        ...
    # TODO
    async def getBusInfo(self, caller_id: str) -> Tuple[int, str, List[XMLRPCValue]]:
        ...
    # TODO
    async def getMasterUri(self, caller_id: str) -> Tuple[int, str, str]:
        return (1, "OK", self.core)
    # TODO
    async def shutdown(self, caller_id: str, msg: str = "") -> Tuple[int, str, int]:
        ...

    async def getPid(self, caller_id: str) -> Tuple[int, str, int]:
        return (1, "OK", os.getpid())

    async def getSubscriptions(self, caller_id: str) -> Tuple[int, str, List[Tuple[str, str]]]:
        return 1, "OK", [ (topic, self.topic_typ[topic].__msg_typ__) for topic in self.subs ]

    async def getPublications(self, caller_id: str) -> Tuple[int, str, List[Tuple[str, str]]]:
        return 1, "OK", [ (topic, self.topic_typ[topic].__msg_typ__) for topic in self.pubs ]
    # TODO
    async def paramUpdate(self, caller_id: str, key: str, val: XMLRPCValue) -> Tuple[int, str, int]:
        ...

    async def publisherUpdate(self, caller_id: str, topic: str, publisher: List[str]) -> Tuple[int, str, int]:
        callback = self.callbacks[topic]
        typ = self.topic_typ[topic]

        cur_subs = set(self.subs[topic].keys())

        for pub in publisher:
            await self.__subscribe__(pub, topic, typ, callback)
            if pub in cur_subs:
                cur_subs.remove(pub)

        for dead_pub in cur_subs:
            self.subs[topic][dead_pub].transport.close()
            del self.subs[topic][dead_pub].protocol
            del self.subs[topic][dead_pub]

        return (1, "OK", 0)

    async def requestTopic(self, caller_id: str, topic: str, protocols: _PROTO_INFO) -> Tuple[int, str, _PROTO_INFO]:
        print(f"Node {caller_id} wants to get {topic}, creating server for it")
        ros_server = TCPROSServer(self.topic_typ[topic], self.name, topic, caller_id, self.__delete_pub_serv)

        server = await self.loop.create_server(lambda: ros_server, "127.0.0.1", 0)
        assert server

        addr, port = server.sockets[0].getsockname()  # type: ignore
        self.pubs[topic][caller_id] = ros_server

        code = 1
        msg = "TODO FIXME"
        proto_params = ["TCPROS", addr, port]

        return (code, msg, proto_params)