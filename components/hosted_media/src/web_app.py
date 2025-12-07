from aiohttp import web
from entity_manager import EntityManager


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    async def handle(self, request):
        text = "Last created: " + self.entity_manager.get_last_created()
        return web.Response(text=text)


def get_app(entity_manager: EntityManager):

    request_handler = RequestHandler(entity_manager)
    app = web.Application()
    app.add_routes([web.get("/", request_handler.handle)])
    return app
