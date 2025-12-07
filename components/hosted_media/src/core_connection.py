from websockets.asyncio.client import connect
import websockets.exceptions
import json
from typing import Any
from entity_manager import EntityManager


def handle_message(message: dict[str, Any], entity_manager: EntityManager):
    cmd = message["command"]
    entity_id = message.get("entityId")
    result = None
    if cmd == "req_component_info":
        return get_component_info(entity_manager)
    elif cmd == "create":
        entity_manager.create(entity_id)
    else:
        raise RuntimeError(f"Unsupported command: {cmd}")


def get_component_info(entity_manager: EntityManager):
    return {
        "messageType": "component_info",
        "componentId": entity_manager.get_component_id(),
        "componentName": "hosted_media",
        "status": "online",
    }


async def core_connection(core_address: str, entity_manager: EntityManager):

    async for websocket in connect("ws://" + core_address):
        try:
            await websocket.send(
                json.dumps({"type": "announce", "client": "media", "channel": 1})
            )
            async for message in websocket:
                try:
                    result = handle_message(json.loads(message), entity_manager)
                    if result is not None:
                        await websocket.send(json.dumps(result))
                except Exception as e:
                    print(e)

        except websockets.exceptions.ConnectionClosed:
            continue
