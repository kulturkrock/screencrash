from aiohttp import web
from entity_manager import EntityManager
from pathlib import Path
import json
from aiohttp_sse import sse_response
import asyncio
from typing import Any
from video_streamer import VideoStreamer


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.entity_manager.add_webpage_message_listener(self.send_to_subscribers)
        self.subscribe_responses = []

        self.entity_manager.add_create_video_streamer_listener(
            self.register_video_streamer
        )
        self.entity_manager.add_delete_video_streamer_listener(
            self.deregister_video_streamer
        )
        self.video_streamers: dict[str, VideoStreamer] = {}

    async def redirect_to_static(self, request):
        return web.Response(status=302, headers={"location": "static/index.html"})

    def send_to_subscribers(self, message: dict[str, Any]):
        for resp in self.subscribe_responses:
            data = json.dumps(message)
            asyncio.create_task(resp.send(data))

    def register_video_streamer(self, entity_id: str, streamer: VideoStreamer):
        self.video_streamers[entity_id] = streamer

    def deregister_video_streamer(self, entity_id: str):
        del self.video_streamers[entity_id]

    async def subscribe(self, request):
        async with sse_response(request) as resp:
            self.subscribe_responses.append(resp)
            for message in self.entity_manager.get_all_entity_create_messages():
                await resp.send(json.dumps(message))
            await resp.wait()
            self.subscribe_responses.remove(resp)
        return resp


def get_app(entity_manager: EntityManager, asset_dir: Path):

    request_handler = RequestHandler(entity_manager)
    app = web.Application()
    app.add_routes(
        [
            web.get("/", request_handler.redirect_to_static),
            web.static("/static", Path(__file__).parent / "static"),
            web.static("/assets", asset_dir, show_index=True),
            web.get("/api/subscribe", request_handler.subscribe),
        ]
    )
    return app
