from typing import Any, Callable

class ParameterApi:

    def __init__(self, node):
        self.node = node

    def __delitem__(self, key: str):
        code, msg, value = self.node.m.deleteParam(self.node.name, key)

    def __setitem__(self, key:str, value: Any):
        code, msg, value = self.node.m.setParam(self.node.name, key, value)

    def __getitem__(self, key: str):
        code, msg, value = self.node.m.getParam(self.node.name, key)
        return value if code == 1 else None

    def search(self, key:str):
        code, msg, value = self.node.m.searchParam(self.node.name, key)
        return value if code == 1 else None

    def subscribe(self, key: str, callback: Callable):
        code, msg, value = self.node.m.subscribeParam(self.node.name, self.node.uri, key)
        self.node.param_callbacks[key] = callback
        return value if code == 1 else None

    def unsubscribe(self, key: str) -> None:
        code, msg, value = self.node.m.unsubscribeParam(self.node.name, self.node.uri, key)
        del self.node.param_callbacks[key]

    def __contains__(self, key: str):
        code, msg, value = self.node.m.hasParam(self.node.name, key)
        return bool(value)

    def __iter__(self):
        code, msg, value = self.node.m.getParamNames(self.node.name)
        yield from value
