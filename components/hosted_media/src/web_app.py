from aiohttp import web, ClientConnectionResetError
from entity_manager import EntityManager
from pathlib import Path
import json
from aiohttp_sse import sse_response
import asyncio
from typing import Any
from media_streamer import MediaStreamer
import aiofiles
from datetime import datetime


class RequestHandler:

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.entity_manager.add_webpage_message_listener(self.send_to_subscribers)
        self.subscribe_responses = []

        self.entity_manager.add_create_media_streamer_listener(
            self.register_media_streamer
        )
        self.entity_manager.add_delete_media_streamer_listener(
            self.deregister_media_streamer
        )
        self.media_streamers: dict[str, MediaStreamer] = {}

    async def redirect_to_static(self, request: web.Request):
        return web.Response(status=302, headers={"location": "static/index.html"})

    def send_to_subscribers(self, message: dict[str, Any]):
        for resp in self.subscribe_responses:
            data = json.dumps(message)
            asyncio.create_task(resp.send(data))

    def register_media_streamer(self, entity_id: str, streamer: MediaStreamer):
        self.media_streamers[entity_id] = streamer

    def deregister_media_streamer(self, entity_id: str):
        del self.media_streamers[entity_id]

    async def stream(self, request: web.Request):
        try:
            stream_id = request.match_info["stream_id"]
            stream_type = request.match_info["stream_type"]
        except KeyError:
            return web.Response(status=400)
        if not (stream_type == "audio" or stream_type == "video"):
            return web.Response(status=400)
        try:
            streamer = self.media_streamers[stream_id]
        except KeyError:
            return web.Response(status=404)
        response = web.StreamResponse(
            headers={
                "Content-Type": streamer.get_mimetype(stream_type),
            }
        )
        try:
            await response.prepare(request)

            async with aiofiles.open(streamer.get_output_file(stream_type), "rb") as f:
                while True:
                    chunk = await f.read(1_000_000)
                    if len(chunk) > 0:
                        print(f"{datetime.now().isoformat()} Sending {len(chunk)}")
                        await response.write(chunk)
                    elif not streamer.is_done():
                        await asyncio.sleep(0.1)
                    else:
                        break

            await response.write_eof()
        except ClientConnectionResetError:
            print("Client went away")

        return response

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
            web.get("/api/stream/{stream_id}/{stream_type}", request_handler.stream),
        ]
    )
    return app
