# **AL**ternative **PY**thon **RO**s
Alternative implementation of a ROS client library in python.

## Example usage
Publisher
```python
from alpyro.node import Node
from alpyro.msgs.std_msgs import StdString

def test():
    msg = StdString()
    msg.value = "Hello there"

    return msg

with Node("/pub") as n:
    n.announce("/test", StdString)
    n.schedule_publish("/test", 10, test)

    n.run_forever()
```

Subscriber
```python
from alpyro.node import Node
from alpyro.msgs.std_msgs import StdString

def callback(msg: StdString):
    print(msg.value)

with Node("/sub") as n:
    n.subscribe("/test", callback)

    n.run_forever()
```