from typing import List
from alpyro.msg import RosMessage, float32, float64, string, uint32, uint8
import alpyro.msgs.std_msgs as std_msgs
from alpyro.msgs.std_msgs import Header


class Image(RosMessage):

    __msg_def__ = "c3RkX21zZ3MvSGVhZGVyIGhlYWRlcgogIHVpbnQzMiBzZXEKICB0aW1lIHN0YW1wCiAgc3RyaW5nIGZyYW1lX2lkCnVpbnQzMiBoZWlnaHQKdWludDMyIHdpZHRoCnN0cmluZyBlbmNvZGluZwp1aW50OCBpc19iaWdlbmRpYW4KdWludDMyIHN0ZXAKdWludDhbXSBkYXRhCgo="
    __md5_sum__ = "060021388200f6f0f447d0fcd9c64743"
    __msg_typ__ = "sensor_msgs/Image"

    header: std_msgs.Header
    height: uint32
    width: uint32
    encoding: string
    is_bigendian: uint8
    step: uint32
    data: List[uint8]


class ChannelFloat32(RosMessage):
    __msg_def__ = "c3RyaW5nIG5hbWUKZmxvYXQzMltdIHZhbHVlcwoK"
    __md5_sum__ = "3d40139cdd33dfedcb71ffeeeb42ae7f"
    __msg_typ__ = "sensor_msgs/ChannelFloat32"

    name: string
    values: List[float32]

class Temperature(RosMessage):
    __msg_def__= "c3RkX21zZ3MvSGVhZGVyIGhlYWRlcgogIHVpbnQzMiBzZXEKICB0aW1lIHN0YW1wCiAgc3RyaW5nIGZyYW1lX2lkCmZsb2F0NjQgdGVtcGVyYXR1cmUKZmxvYXQ2NCB2YXJpYW5jZQoK"
    __md5_sum__ = "ff71b307acdbe7c871a5a6d7ed359100"
    __msg_typ__ = "sensor_msgs/Temperature"

    header: std_msgs.Header = Header()
    temperature: float64
    variance: float64
