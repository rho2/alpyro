from alpyro.msg import RosMessage, Time, string, time, uint32


class String(RosMessage):
    __msg_typ__ = "std_msgs/String"
    __md5_sum__ = "992ce8a1687cec8c8bd883ec73ca41d1"
    __msg_def__ = "c3RyaW5nIGRhdGEKCg=="

    value: string

    def __repr__(self):
        return self.value


class Header(RosMessage):
    __msg_typ__ = "std_msgs/Header"
    __md5_sum__ = "2176decaecbce78abc3b96ef049fabed"
    __msg_def__ = "dWludDMyIHNlcQp0aW1lIHN0YW1wCnN0cmluZyBmcmFtZV9pZAoK"

    seq: uint32
    stamp: time
    frame_id: string

    def __repr__(self) -> str:
        return f"[{self.stamp}] - {self.seq:010} : {self.frame_id}"
