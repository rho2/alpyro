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
from alpyro_msgs.std_msgs.string import StdString

def test():
    msg = StdString()
    msg.data = "Hello there"

    return msg

with Node("/pub") as n:
    n.announce("/test", StdString)
    n.schedule_publish("/test", 10, test)

    n.run_forever()
```

Subscriber
```python
from alpyro.node import Node
from alpyro_msgs.std_msgs.string import StdString

def callback(msg: StdString):
    print(msg.data)

with Node("/sub") as n:
    n.subscribe("/test", callback)

    n.run_forever()
```