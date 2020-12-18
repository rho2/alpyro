from inspect import signature

PRE_SUBS = {}
PRE_PUBS = {}


def subscribe(topic: str):
    def inner(func):
        global PRE_SUBS
        PRE_SUBS[topic] = func
        return func
    return inner


def publish(topic: str, rate: int = 0):
    def inner(func):
        global PRE_PUBS
        PRE_PUBS[topic] = (func, rate, signature(func).return_annotation)
        return func
    return inner
