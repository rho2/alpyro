import inspect
from .node import Node
import importlib
from pathlib import Path
from .decorator import subscribe, publish, PRE_PUBS, PRE_SUBS

__all__ = [
    "subscribe",
    "publish"
]


def get_importing_module():
    for frame in inspect.stack():
        mod = inspect.getmodule(frame[0])
        if mod is not None and mod.__file__ != __file__:
            return mod

    raise RuntimeError("Could not find importing module")


def _launch():
    mod = get_importing_module()
    if mod.__name__ != '__main__':
        return

    mod_i = importlib.import_module(Path(mod.__file__).stem, mod.__package__)

    n = Node(f"/{mod_i.__file__}")

    with n:
        for t, fun in PRE_SUBS.items():
            n.subscribe(t, fun)
        for t, (fun, rate, typ) in PRE_PUBS.items():
            n.announce(t, typ)
            if rate:
                n.schedule_publish(t, rate, fun)

        n.run_forever()


_launch()
