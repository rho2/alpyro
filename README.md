# **AL**ternative **PY**thon **RO**s
Alternative implementation of a ROS client library in python.

## Installation
```bash
pip install alpyro
```

## Example usage
Publisher
```python
from alpyro_msgs.std_msgs.string import String
from alpyro.magic import publish

@publish("/test2", rate=10)
def write_str() -> String:
    s = String()
    s.data = "Hello there!"
    return s

```

Subscriber
```python
from alpyro_msgs.std_msgs.string import String
from alpyro.magic import subscribe

@subscribe("/test")
def callback(msg: String):
    print(msg.data)
```

Get the node or the last message in the message factory:
```python
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import String

def test(node: Node, msg: Optional[String]):
    if msg is None:
        msg = String()
        msg.data = f"Hello from {node.name}"

    msg.data += "."

    return msg

with Node("/pub") as n:
    n.announce("/test", String)
    n.schedule_publish("/test", 10, test)

    n.run_forever()
```

Get the node in a callback:
```python
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import String

def callback(msg: String, node: Node):
    print(node.name, msg.data)

with Node("/sub") as n:
    n.subscribe("/test", callback)

    n.run_forever()
```

Simple relay node:
```python
from alpyro_msgs.std_msgs.string import String
from alpyro.magic import subscribe, publish
from alpyro.node import Node

@publish("/test2", rate=0)
def write_str() -> String:
    s = String()
    s.data = "Hello there!"
    return s

@subscribe("/chatter")
def read_str(s: String, n: Node) -> None:
    n.publish("/test2", s)
```

Missing stuff:
- [ ] services
- [ ] option to use sim_time instead of walltime
- [ ] parse remapping args