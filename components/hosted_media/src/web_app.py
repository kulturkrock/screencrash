from aiohttp import web
from entity_manager import EntityManager
from pathlib import Path
import json
from aiohttp_sse import sse_response
import asyncio


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    async def redirect_to_static(self, request):
        return web.Response(status=302, headers={"location": "static/index.html"})

    async def get_state(self, request):
        last_created = self.entity_manager.get_last_created()
        return web.Response(text=json.dumps({"last_created": last_created}))

    async def subscribe(self, request):
        async with sse_response(request) as resp:
            while resp.is_connected():
                last_created = self.entity_manager.get_last_created()
                data = json.dumps({"last_created": last_created})
                await resp.send(data)
                await asyncio.sleep(1)
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
