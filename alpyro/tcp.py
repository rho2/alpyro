from asyncio import Protocol
from typing import Type
from alpyro.msg import RosMessage


def parse_headers(headers: bytes):
    cur = 0
    rcv_headers = {}
    while cur < len(headers):
        l = int.from_bytes(headers[cur : cur + 4], "little", signed=False)

        name, _, val = headers[cur + 4 : cur + 4 + l].decode("utf-8").partition("=")
        rcv_headers[name] = val

        cur += 4 + l

    return rcv_headers


class TCPROSServer(Protocol):
    typ: Type[RosMessage]
    name: str
    topic: str
    send_data: bool = False
    callerid: str

    def __init__(self, typ: Type[RosMessage], name: str, topic: str, callerid: str, f):
        super().__init__()
        self.typ = typ
        self.name = name
        self.topic = topic
        self.callerid = callerid
        self.f = f

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        data_length = int.from_bytes(data[:4], "little", signed=False)
        # TODO handle cases where not all date in received here?
        headers = parse_headers(data[4:])

        assert headers["md5sum"] == self.typ.__md5_sum__
        assert headers["type"] == self.typ.__msg_typ__

        send_headers = self.typ.get_header(self.name, self.topic, extra_header={"latching": "0"})

        self.transport.write(send_headers)
        self.send_data = True

    def connection_lost(self, exc):
        self.f(self.topic, self.callerid)
        self.send_data = False

    # TODO static type checking for this method?
    def publish(self, msg: RosMessage):
        if self.send_data is False:
            return

        assert isinstance(msg, self.typ)

        data = msg.encode()
        data_len = bytearray(len(data).to_bytes(4, "little", signed=False))

        data_len.extend(data)

        self.transport.write(data_len)


class TCPROSClient(Protocol):
    def __init__(self, callback, typ, name, topic):
        self.callback = callback
        self.typ = typ
        self.name = name
        self.topic = topic
        self.read_data = False

    def connection_made(self, transport):
        transport.write(self.typ.get_header(self.name, self.topic))

    def data_received(self, data):
        # TODO verify data length and handle cases were not everthing is received at once
        if self.read_data:
            data_length = int.from_bytes(data[:4], "little", signed=False)

            ins = self.typ()
            ins.decode(bytearray(data[4:]), 0)
            self.callback(ins)
        else:
            data_length = int.from_bytes(data[:4], "little", signed=False)
            headers = parse_headers(data[4:])

            assert headers["md5sum"] == self.typ.__md5_sum__
            assert headers["type"] == self.typ.__msg_typ__
            self.read_data = True

    def connection_lost(self, exc):
        print("The server closed the connection")
