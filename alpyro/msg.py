from typing import Any, Dict, List, Optional, Type, Final
from typing_extensions import Annotated, get_type_hints
from typing_extensions import get_args, get_origin  # type: ignore[attr-defined]
import struct
from dataclasses import dataclass
import base64

UNSIGNED = False
SIGNED = True

boolean = Annotated[bool, 1, UNSIGNED]

uint8 = Annotated[int, 1, UNSIGNED]
uint16 = Annotated[int, 2, UNSIGNED]
uint32 = Annotated[int, 4, UNSIGNED]
uint64 = Annotated[int, 8, UNSIGNED]

int8 = Annotated[int, 1, SIGNED]
int16 = Annotated[int, 2, SIGNED]
int32 = Annotated[int, 4, SIGNED]
int64 = Annotated[int, 8, SIGNED]

float32 = Annotated[float, 4, SIGNED]
float64 = Annotated[float, 8, SIGNED]

string = Annotated[str, 0, UNSIGNED]

# TODO changes this time implementation to something more useful, e.g. numpy times
class Time:
    secs: uint32
    nsecs: uint32

    def __init__(self, secs: uint32 = 0, nsecs: uint32= 0) -> None:
        self.secs = secs
        self.nsecs = nsecs

    def __repr__(self) -> str:
        return f"{self.secs}:{self.nsecs}"


time = Annotated[Time, 8, UNSIGNED]


class RosMessage:
    __msg_typ__: str
    __md5_sum__: str
    __msg_def__: str

    def _encode_value(self, val: Any, typ: Type[Any], buffer: bytearray) -> None:
        if isinstance(val, RosMessage):
            val.encode(buffer)
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
        elif base == Time:
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

    def encode(self, buffer: Optional[bytearray] = None) -> bytearray:
        if buffer is None:
            buffer = bytearray()

        for name, t in get_type_hints(self, include_extras=True).items():  # type: ignore
            origin = get_origin(t)

            if origin is Final:
                continue

            def_factory = t
            if origin is Annotated and get_origin(get_args(t)[0]) is list:
                def_factory = list

            val = getattr(self, name, def_factory())
            self._encode_value(val, t, buffer)
            # TODO: add missing types: duration
        return buffer

    def _decode_value(self, buffer: bytearray, offset, typ):
        o = get_origin(typ)
        val: Any = None

        if o is None and issubclass(typ, RosMessage):
            val = typ()
            offset = val.decode(buffer, offset)
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
        elif base == Time:
            secs = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
            nsecs = int.from_bytes(buffer[offset + 4 : offset + 8], "little", signed=False)
            val = Time(secs, nsecs)
            offset += 8
        elif get_origin(base) == list:
            t, *_ = get_args(base)
            if size == 0:
                size = int.from_bytes(buffer[offset : offset + 4], "little", signed=False)
                offset += 4

            val = []
            for _ in range(size):
                v, offset = self._decode_value(buffer, offset, t)
                val.append(v)
        # TODO implement other types

        return val, offset

    def decode(self, buffer: bytearray, offset: int = 0) -> int:
        for name, t in get_type_hints(self, include_extras=True).items():  # type: ignore
            if get_origin(t) is Final:
                continue
            val, offset = self._decode_value(buffer, offset, t)
            setattr(self, name, val)
        return offset

    @classmethod
    def get_msg_def(cls):
        return base64.b64decode(cls.__msg_def__.encode("utf-8")).decode("utf-8")

    @classmethod
    def get_header(cls, caller_id: str, topic: str, extra_header: Optional[Dict[str, str]] = None):
        msg = {
            "message_definition": cls.get_msg_def(),
            "callerid": caller_id,
            "md5sum": cls.__md5_sum__,
            "topic": topic,
            "type": cls.__msg_typ__,
        }

        if extra_header:
            msg = {**msg, **extra_header}

        b = bytes()

        for (key, val) in msg.items():
            m = f"{key}={val}"
            b += len(m).to_bytes(4, "little", signed=False)
            b += m.encode("utf-8")

        return len(b).to_bytes(4, "little", signed=False) + b
