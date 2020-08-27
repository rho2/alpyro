# **AL**ternative **PY**thon **RO**s
Alternative implementation of a ROS client library in python.

## Installation
```bash
pip install alpyro
```

## Example usage
Publisher
```python
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import String

def test():
    msg = String()
    msg.data = "Hello there"

    return msg

with Node("/pub") as n:
    n.announce("/test", String)
    n.schedule_publish("/test", 10, test)

    n.run_forever()
```

Subscriber
```python
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import String

def callback(msg: String):
    print(msg.data)

with Node("/sub") as n:
    n.subscribe("/test", callback)

    n.run_forever()
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
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import String

def callback(node: Node, msg: String):
    node.publish("/test2", msg)

with Node("/sub") as n:
    n.announce("/test2", String)
    n.subscribe("/test", callback)
    n.run_forever()
```
