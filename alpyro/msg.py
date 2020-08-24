from typing import Optional, Protocol, Type, Dict
from typing_extensions import Annotated
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

class Duration:
    secs: uint32
    nsecs: uint32

    def __init__(self, secs: uint32 = 0, nsecs: uint32= 0) -> None:
        self.secs = secs
        self.nsecs = nsecs

    def __repr__(self) -> str:
        return f"{self.secs}:{self.nsecs}"

time = Annotated[Time, 8, UNSIGNED]
duration = Annotated[Duration, 8, UNSIGNED]

class RosMessage:
    __msg_typ__: str
    __md5_sum__: str
    __msg_def__: str

    @classmethod
    def get_msg_def(cls):
        return base64.b64decode(cls.__msg_def__.encode("utf-8")).decode("utf-8")

class Converter(Protocol):
    def decode(self, msg: RosMessage, buffer: bytearray, offset: int = 0) -> int:
        ...

    def encode(self, msg: RosMessage, buffer: Optional[bytearray] = None) -> bytearray:
        ...

    def encode_header(self, cls: Type[RosMessage], caller_id: str, topic: str, extra: Optional[Dict[str, str]] = None):
        ...

    def decode_header(self, headers: bytes) -> Dict[str, str]:
        ...