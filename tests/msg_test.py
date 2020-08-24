from alpyro.msgs.std_msgs import String, Header
from alpyro.msgs.sensor_msgs import ChannelFloat32, Temperature, JoyFeedback
from alpyro.msgs.shape_msgs import MeshTriangle
from pytest import approx, raises

def test_simple_string():
    s1 = String()
    s1.value = "FooBar"
    s_bytes = s1.encode()

    s2 = String()
    s2.decode(s_bytes)

    assert s1.value == s2.value


def test_list():
    v1 = ChannelFloat32()
    v1.name = "Name"
    v1.values = [1.1, 1.2, 1.3]

    v2 = ChannelFloat32()
    v2.decode(v1.encode())

    assert v1.name == v2.name
    assert v1.values == approx(v2.values)

def test_nested():
    t1 = Temperature()
    t1.header.frame_id = "foo"
    t1.header.seq = 42
    t1.temperature = 100.1

    t2 = Temperature()
    t2.decode(t1.encode())

    assert t1.temperature == approx(t2.temperature)
    assert t1.header.frame_id == t2.header.frame_id
    assert t1.header.seq == t2.header.seq

def test_constants():
    j = JoyFeedback()
    j.id = 1
    j.type = JoyFeedback.TYPE_LED

    j2 = JoyFeedback()
    j2.decode(j.encode())

    assert j.id == j2.id
    assert j2.type == JoyFeedback.TYPE_LED

def test_fixed_array():
    t = MeshTriangle()
    t.vertex_indices = [1, 2, 3]

    t2 = MeshTriangle()
    t2.decode(t.encode())

    assert t.vertex_indices == t2.vertex_indices

def test_fixed_array_size_mismatch():
    t = MeshTriangle()
    t.vertex_indices = [1, 2, 3, 4]

    with raises(AssertionError):
        t.encode()