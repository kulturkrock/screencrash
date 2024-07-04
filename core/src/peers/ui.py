import base64
from dataclasses import asdict
import json
import time
import traceback
from typing import Any, Dict, List
import websockets
from websockets.server import WebSocketServerProtocol

from opus import Opus, Node, ActionTemplate
from peers.component_info import ComponentInfo, ComponentState
from util.event_emitter import EventEmitter


class UI(EventEmitter):
    """
    Handles communication with UIs.

    This has a websocket server that the UI can connect to.

    Parameters
    ----------
    opus
        The opus. Some contents are sent in the initial handshake with a client.
    initial_history
        The initial history
    """

    EFFECT_TYPES = {
        "unknown": 0,
        "audio": 1,
        "video": 2,
        "image": 3,
        "web": 4,
    }

    MAX_NOF_LOGS = 1000

    def __init__(self, opus: Opus, initial_history: List[str]):
        super().__init__()
        self._opus = opus
        self._history = initial_history
        self._components: Dict[str, ComponentState] = {}
        self._effects = {}
        self._websockets: List[WebSocketServerProtocol] = []
        self._logs = []

    def changed_history(self, history: List[str]):
        """Update the history and send to clients."""
        self._history = history
        websockets.broadcast(self._websockets, json.dumps({
            "messageType": "history",
            "data": self._history
        }))

    def _send_effects_update(self):
        websockets.broadcast(self._websockets, json.dumps({
            "messageType": "effects",
            "data": list(self._effects.values())
        }))

    def _send_components_update(self):
        websockets.broadcast(self._websockets, json.dumps({
            "messageType": "components",
            "data": [asdict(component) for component in self._components.values()]
        }))

    def _send_logs_update(self):
        websockets.broadcast(self._websockets, json.dumps({
            "messageType": "logs",
            "data": self._logs
        }))

    def effect_added(self, event_data):
        entity_id = event_data["entityId"]
        event_data["type"] = self.EFFECT_TYPES.get(event_data["effectType"], 0)
        del event_data["effectType"]
        self._effects[entity_id] = event_data
        self._send_effects_update()
    
    def effect_changed(self, event_data):
        entity_id = event_data["entityId"]
        event_data["type"] = self.EFFECT_TYPES.get(event_data["effectType"], 0)
        del event_data["effectType"]
        if not entity_id in self._effects:
            print(f"Tried to update effect {entity_id} but it doesnt exist. Skipping")
            return
        self._effects[entity_id].update(event_data)
        self._send_effects_update()
    
    def effect_removed(self, event_data):
        entity_id = event_data["entityId"]
        if entity_id in self._effects:
            del self._effects[entity_id]
            self._send_effects_update()
        else:
            print(f"Tried to remove effect but couldnt find it")

    def log_message(self, level: str, timestamp: float, origin: str, message: str):
        self._logs.append({
            "level": level,
            "timestamp": timestamp,
            "origin": origin,
            "message": message,
        })
        while len(self._logs) > self.MAX_NOF_LOGS:
            self._logs.pop(0)
        websockets.broadcast(self._websockets, json.dumps({
            "messageType": "log-added",
            "data": self._logs[-1]
        }))

    def clear_logs(self):
        self._logs = []
        self._send_logs_update()

    def component_info_updated(self, component: ComponentInfo) -> None:
        if component.componentId in self._components:
            self._components[component.componentId].info = component
        else:
            self._components[component.componentId] = ComponentState(component, {})
        self._send_components_update()

    def component_state_updated(self, component_id: str, state: Dict[str, Any]):
        if component_id in self._components:
            self._components[component_id].state.update(state)
        self._send_components_update()

    def component_removed(self, component_id: str) -> None:
        if component_id in self._components:
            del self._components[component_id]
            self._send_components_update()

    def _prepare_node_for_send(self, node: Node) -> Dict[str, Any]:
        data = asdict(node)
        data["actions"] = [asdict(self._opus.action_templates.get(action)) for action in node.actions]
        if type(node.next) == list:
            for nextChoice in data["next"]:
                nextChoice["actions"] = [asdict(self._opus.action_templates.get(action)) for action in nextChoice["actions"]]
        return data

    async def handle_socket(self, websocket: WebSocketServerProtocol):
        """This handles one websocket connection."""
        self._websockets.append(websocket)
        # Handshake
        await websocket.send(json.dumps({
            "messageType": "nodes",
            "data": {key: self._prepare_node_for_send(node) for key, node in self._opus.nodes.items()}
        }))
        await websocket.send(json.dumps({
            "messageType": "uiconfig",
            "data": asdict(self._opus.ui_config)
        }))
        await websocket.send(json.dumps({
            "messageType": "history",
            "data": self._history
        }))
        await websocket.send(json.dumps({
            "messageType": "components",
            "data": [asdict(component) for component in self._components.values()]
        }))
        await websocket.send(json.dumps({
            "messageType": "effects",
            "data": list(self._effects.values())
        }))
        await websocket.send(json.dumps({
            "messageType": "logs",
            "data": self._logs
        }))
        base64_script = base64.b64encode(
            self._opus.script).decode("utf-8")
        await websocket.send(json.dumps({
            "messageType": "script",
            "data": f"data:application/pdf;base64,{base64_script}"
        }))
        # Handle messages from the client
        async for message in websocket:
            try:
                message_dict = json.loads(message)
                message_type = message_dict["messageType"]
                if message_type == "next-node":
                    run_actions = message_dict.get("runActions", True)
                    self.emit("next-node", run_actions)
                elif message_type == "choose-path":
                    choice_index = message_dict["choiceIndex"]
                    run_actions = message_dict.get("runActions", True)
                    self.emit("choose-path", choice_index, run_actions)
                elif message_type == "prev-node":
                    self.emit("prev-node")
                elif message_type == "goto-node":
                    self.emit("goto-node", message_dict["node"])
                elif message_type == "run-actions":
                    self.emit("run-actions")
                elif message_type == "run-actions-by-id":
                    self.emit("run-actions-by-id", message_dict["actions"])
                elif message_type == "component-action":
                    target = message_dict["target_component"]
                    cmd = message_dict["cmd"]
                    asset_names = message_dict["assets"]
                    params = message_dict["params"]
                    self.emit("component-action", target, cmd, asset_names, params)
                elif message_type == "clear-logs":
                    self.clear_logs()
                elif message_type == "component-reset":
                    component_id = message_dict["componentId"]
                    self.emit("component-reset", component_id)
                elif message_type == "component-restart":
                    component_id = message_dict["componentId"]
                    self.emit("component-restart", component_id)
                else:
                    print(f"WARNING: Unknown message type {message_type}")
                    self.log_message("warning", time.time(), "core", f"Unknown message type from UI {message_type}")
            except Exception as e:
                print(f"Failed to handle UI message. Got error {e}")
                self.log_message("error", time.time(), "core", f"Failed to handle UI message. Got error {e}")
                traceback.print_exc()
        # Websocket is closed
        self._websockets.remove(websocket)
