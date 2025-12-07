from aiohttp import web
from entity_manager import EntityManager
from pathlib import Path
import json


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    async def redirect_to_static(self, request):
        return web.Response(status=302, headers={"location": "static/index.html"})

    async def get_state(self, request):
        last_created = self.entity_manager.get_last_created()
        return web.Response(text=json.dumps({"last_created": last_created}))


def get_app(entity_manager: EntityManager):

    request_handler = RequestHandler(entity_manager)
    app = web.Application()
    app.add_routes(
        [
            web.get("/", request_handler.redirect_to_static),
            web.static("/static", Path(__file__).parent / "static"),
            web.get("/api/state", request_handler.get_state),
        ]
    )
    return app
