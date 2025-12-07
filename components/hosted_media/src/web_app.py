from aiohttp import web
from entity_manager import EntityManager
from pathlib import Path
import json
from aiohttp_sse import sse_response
import asyncio
from typing import Any


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.entity_manager.add_message_listener(self.send_to_subscribers)
        self.subscribe_responses = []

    async def redirect_to_static(self, request):
        return web.Response(status=302, headers={"location": "static/index.html"})

    async def get_state(self, request):
        last_created = self.entity_manager.get_last_created()
        return web.Response(text=json.dumps({"last_created": last_created}))

    def send_to_subscribers(self, message: dict[str, Any]):
        for resp in self.subscribe_responses:
            data = json.dumps(message)
            asyncio.create_task(resp.send(data))

    async def subscribe(self, request):
        async with sse_response(request) as resp:
            self.subscribe_responses.append(resp)
            await resp.wait()
            self.subscribe_responses.remove(resp)
        return resp


def get_app(entity_manager: EntityManager):

    request_handler = RequestHandler(entity_manager)
    app = web.Application()
    app.add_routes(
        [
            web.get("/", request_handler.redirect_to_static),
            web.static("/static", Path(__file__).parent / "static"),
            web.get("/api/subscribe", request_handler.subscribe),
            web.get("/api/state", request_handler.get_state),
        ]
    )
    return app
