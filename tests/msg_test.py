from alpyro_msgs.std_msgs.header import Header
from alpyro_msgs.std_msgs.string import String
from alpyro_msgs.sensor_msgs.channelfloat32 import ChannelFloat32
from alpyro_msgs.sensor_msgs.temperature import  Temperature
from alpyro_msgs.sensor_msgs.joyfeedback import JoyFeedback
from alpyro_msgs.shape_msgs.meshtriangle import MeshTriangle
from pytest import approx, raises, fixture
from alpyro.tcp import TCPROSConverter

@fixture
def tcp_converter():
    return TCPROSConverter()

def test_simple_string(tcp_converter):
    s1 = String()
    s1.data = "FooBar"

    s2 = String()
    tcp_converter.decode(s2, tcp_converter.encode(s1))

    assert s1.data == s2.data


def test_list(tcp_converter):
    v1 = ChannelFloat32()
    v1.name = "Name"
    v1.values = [1.1, 1.2, 1.3]

    v2 = ChannelFloat32()
    tcp_converter.decode(v2, tcp_converter.encode(v1))

    assert v1.name == v2.name
    assert v1.values == approx(v2.values)

def test_nested(tcp_converter):
    t1 = Temperature()
    t1.header = Header()
    t1.header.frame_id = "foo"
    t1.header.seq = 42
    t1.temperature = 100.1

    t2 = Temperature()
    tcp_converter.decode(t2, tcp_converter.encode(t1))

    assert t1.temperature == approx(t2.temperature)
    assert t1.header.frame_id == t2.header.frame_id
    assert t1.header.seq == t2.header.seq

def test_constants(tcp_converter):
    j = JoyFeedback()
    j.id = 1
    j.type = JoyFeedback.TYPE_LED

    j2 = JoyFeedback()
    tcp_converter.decode(j2, tcp_converter.encode(j))

    assert j.id == j2.id
    assert j2.type == JoyFeedback.TYPE_LED

def test_fixed_array(tcp_converter):
    t = MeshTriangle()
    t.vertex_indices = [1, 2, 3]

    t2 = MeshTriangle()
    tcp_converter.decode(t2, tcp_converter.encode(t))

    assert t.vertex_indices == t2.vertex_indices

def test_fixed_array_size_mismatch(tcp_converter):
    t = MeshTriangle()
    t.vertex_indices = [1, 2, 3, 4]

    with raises(AssertionError):
        tcp_converter.encode(t)
