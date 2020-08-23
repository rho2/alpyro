from asyncio.events import AbstractEventLoop
import inspect
from typing import Any, List, Tuple
from xml.etree.ElementTree import Element
from aiohttp import web
import xml.etree.ElementTree as ET


def parse_args(params: List[Element]):
    args: List[Any] = []
    for p in params:
        if p.tag == "int" or p.tag == "i4":
            assert p.text
            args.append(int(p.text))
        elif p.tag == "string":
            args.append(p.text)
        elif p.tag == "array":
            data = p.find("data")
            assert not data is None
            args.append(parse_args([e[0] for e in data.findall("value")]))
        # TODO implement the other xmlrpc value types
    return args


def to_xml(value: Any) -> Element:
    v = ET.Element("value")

    if isinstance(value, int):
        i = ET.SubElement(v, "int")
        i.text = str(value)
    elif isinstance(value, str):
        i = ET.SubElement(v, "string")
        i.text = value
    elif isinstance(value, list) or isinstance(value, tuple):
        arr = ET.SubElement(v, "array")
        data = ET.SubElement(arr, "data")
        for e in value:
            data.append(to_xml(e))
    # TODO implement the other xmlrpc value types

    return v


class XMLRPCServer:
    loop: AbstractEventLoop
    addr: Tuple[str, int]

    def __init__(self, loop: AbstractEventLoop) -> None:
        self.loop = loop

    def create_server(self):
        self.loop.run_until_complete(self.start_server())

    async def start_server(self):
        self.server = web.Server(self.handler)
        # TODO add option to specify the address to use
        self.loop_server = await self.loop.create_server(self.server, "127.0.0.1", 0)
        self.addr = self.loop_server.sockets[0].getsockname()
        print("Started the XMLRPC endpoint at address:", self.addr)

    async def handler(self, request):
        root = ET.fromstring(await request.text())

        method = root.find("methodName").text
        params = [e.find("value")[0] for e in root.find("params").findall("param")]

        args = parse_args(params)
        fun = getattr(self, method)

        if inspect.iscoroutinefunction(fun):
            ret = await fun(*args)
        else:
            ret = fun(*args)

        response = ET.Element("methodResponse")
        responseParams = ET.SubElement(response, "params")
        try:
            for p in ret:
                param = ET.SubElement(responseParams, "param")
                param.append(to_xml(p))
        except TypeError:
            param = ET.SubElement(responseParams, "param")
            param.append(to_xml(ret))

        return web.Response(body=ET.tostring(response))

    @property
    def uri(self):
        addr, port = self.addr
        return f"http://{addr}:{port}"

    # TODO add default function which can return a proper rpc error instead of raising an exception
