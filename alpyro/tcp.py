from asyncio import Protocol
import struct
from typing import Dict, Optional, Type, Final, Any
from alpyro_msgs import  Duration, RosMessage, Time, Converter
from typing_extensions import Annotated, get_type_hints
from typing_extensions import get_args, get_origin  # type: ignore[attr-defined]

class TCPROSConverter:
    def _decode_value(self, msg: RosMessage, buffer: bytes, offset, typ):
        o = get_origin(typ)
        val: Any = None

        if o is None and issubclass(typ, RosMessage):
            val = typ()
            offset = self.decode(val, buffer, offset)
            return val, offset

        base, size, signed = get_args(typ)

        if base == str:
            l = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
            val = buffer[offset + 4 : offset + 4 + l].decode("utf-8")
            offset += 4 + l
        elif base == int:
            val = int.from_bytes(buffer[offset : offset + size], "little", signed=signed)
            offset += size
        elif base == float:
            val, *_ = struct.unpack("<f" if size == 4 else "<d", buffer[offset : offset + size])
            offset += size
        elif base == bytes:
            if size == 0:
                size = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
                offset += 4
            val = buffer[offset : offset + size]
            offset += size
        elif base == Time or base == Duration:
            secs = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
            nsecs = int.from_bytes(buffer[offset + 4 : offset + 8], "little", signed=False)
            val = base(secs, nsecs)
            offset += 8
        elif get_origin(base) == list:
            t, *_ = get_args(base)
            if size == 0:
                size = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
                offset += 4

            val = []
            for _ in range(size):
                v, offset = self._decode_value(msg, buffer, offset, t)
                val.append(v)

        return val, offset

    def decode(self, msg: RosMessage, buffer: bytes, offset: int = 0) -> int:
        for name, t in get_type_hints(msg, include_extras=True).items():  # type: ignore
            if get_origin(t) is Final:
                continue
            val, offset = self._decode_value(msg, buffer, offset, t)
            setattr(msg, name, val)
        return offset

    def _encode_value(self, val: Any, typ: Type[Any], buffer: bytearray) -> None:
        if isinstance(val, RosMessage):
            self.encode(val, buffer)
            return

        o = get_origin(typ)

        assert o == Annotated
        base, size, signed = get_args(typ)

        if base == str:
            buffer.extend(len(val).to_bytes(4, "little", signed=False))
            buffer.extend(val.encode("utf-8"))
        elif base == int:
            buffer.extend(val.to_bytes(size, "little", signed=signed))
        elif base == float:
            buffer.extend(struct.pack("<f" if size == 4 else "<d", val))
        elif base == bytes:
            if size == 0:
                byte_length = len(val)
                buffer.extend(byte_length.to_bytes(4, "little", signed=False))
            else:
                assert len(val) == size
            buffer.extend(val)
        elif base == Time or base == Duration:
            buffer.extend(val.secs.to_bytes(4, "little", signed=False))
            buffer.extend(val.nsecs.to_bytes(4, "little", signed=False))
        elif get_origin(base) == list:
            typ, *_ = get_args(base)

            if size == 0:
                byte_length = len(val)
                buffer.extend(byte_length.to_bytes(4, "little", signed=False))
            else:
                assert len(val) == size
            for v in val:
                self._encode_value(v, typ, buffer)

    def encode(self, msg: RosMessage, buffer: Optional[bytearray] = None) -> bytearray:
        if buffer is None:
            buffer = bytearray()

        for name, t in get_type_hints(msg, include_extras=True).items():  # type: ignore
            origin = get_origin(t)

            if origin is Final:
                continue

            def_factory = t
            if origin is Annotated and get_origin(get_args(t)[0]) is list:
                def_factory = list

            val = getattr(msg, name, def_factory())
            self._encode_value(val, t, buffer)
        return buffer

    def encode_header(self, cls: Type[RosMessage], caller_id: str, topic: str, extra: Optional[Dict[str, str]] = None):
        msg = {
            "message_definition": cls.get_msg_def(),
            "callerid": caller_id,
            "md5sum": cls.__md5_sum__,
            "topic": topic,
            "type": cls.__msg_typ__,
        }

        if extra:
            msg = {**msg, **extra}

        b = bytes()

        for (key, val) in msg.items():
            m = f"{key}={val}"
            b += len(m).to_bytes(4, "little", signed=False)
            b += m.encode("utf-8")

        return len(b).to_bytes(4, "little", signed=False) + b

    def decode_header(self, headers: bytes) -> Dict[str, str]:
        cur = 0
        rcv_headers: Dict[str, str] = {}
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
    converter: Converter

    def __init__(self, typ: Type[RosMessage], name: str, topic: str, callerid: str, f):
        super().__init__()
        self.typ = typ
        self.name = name
        self.topic = topic
        self.callerid = callerid
        self.f = f
        self.converter = TCPROSConverter()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        data_length = int.from_bytes(data[:4], "little", signed=False)
        # TODO handle cases where not all date in received here?
        headers = self.converter.decode_header(data[4:])

        assert headers["md5sum"] == self.typ.__md5_sum__
        assert headers["type"] == self.typ.__msg_typ__

        send_headers = self.converter.encode_header(self.typ, self.name, self.topic, extra ={"latching": "0"})

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

        data = self.converter.encode(msg)
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
        self.converter = TCPROSConverter()
        self.current_buffer = None
        self.msg_len = 0

    def connection_made(self, transport):
        transport.write(self.converter.encode_header(self.typ, self.name, self.topic))

    def _msg_finished(self):
        ins = self.typ()
        self.converter.decode(ins, self.current_buffer, 0)
        self.callback(ins)
        self.current_buffer = None

    def _build_msg(self, data: bytes):
        if self.current_buffer is None:
            data_length = int.from_bytes(data[:4], "little", signed=False)
            self.msg_len = data_length
            self.current_buffer = bytes()
            data = data[4:]

        missing_len = self.msg_len - len(self.current_buffer)

        if len(data) < missing_len:
            self.current_buffer += (data)
        elif len(data) == missing_len:
            self.current_buffer += (data)
            self._msg_finished()
        else:
            self.current_buffer += (data[:missing_len])
            self._msg_finished()
            self._build_msg(data[missing_len:])

    def data_received(self, data):
        if self.read_data:
            self._build_msg(data)
        else:
            data_length = int.from_bytes(data[:4], "little", signed=False)
            headers = self.converter.decode_header(data[4:])

            assert headers["md5sum"] == self.typ.__md5_sum__
            assert headers["type"] == self.typ.__msg_typ__
            self.read_data = True

    def connection_lost(self, exc):
        print("The server closed the connection")

