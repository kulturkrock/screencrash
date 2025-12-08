from websockets.asyncio.client import connect
import websockets.exceptions
import json
from typing import Any
from entity_manager import EntityManager
import traceback
import asyncio


def handle_message(message: dict[str, Any], entity_manager: EntityManager):
    cmd = message["command"]
    if cmd == "req_component_info":
        return get_component_info(entity_manager)
    else:
        return entity_manager.handle_message(message)


def get_component_info(entity_manager: EntityManager):
    return {
        "messageType": "component_info",
        "componentId": entity_manager.get_component_id(),
        "componentName": "hosted_media",
        "status": "online",
    }


async def core_connection(core_address: str, entity_manager: EntityManager):

    current_websocket = None

    def send_message(message: dict[str, Any]) -> None:
        asyncio.create_task(current_websocket.send(json.dumps(message)))

    entity_manager.add_core_message_listener(send_message)

    async for websocket in connect("ws://" + core_address):
        try:
            current_websocket = websocket
            await websocket.send(
                json.dumps({"type": "announce", "client": "media", "channel": 1})
            )
            async for message in websocket:
                try:
                    print("Got message: " + message)
                    result = handle_message(json.loads(message), entity_manager)
                    if result is not None:
                        await websocket.send(json.dumps(result))
                except Exception:
                    traceback.print_exc()

        except websockets.exceptions.ConnectionClosed:
            continue
