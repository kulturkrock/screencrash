import asyncio
import json
from typing import Dict
import os
from pathlib import Path
import websockets
from websockets.server import WebSocketServerProtocol

from opus import ActionTemplate, load_opus
from peers.component import ComponentPeer
from peers.inventory import InventoryPeer
from performance import Performance
from peers.internal import InternalPeer
from peers.media import MediaPeer
from peers.ui import UI
from peers.ledController import LedControllerPeer
from peers.myggcheck import MyggCheckPeer


class Core:
    """
    This is the main class, keeping track of all state.

    Parameters
    ----------
    port
        The port to run a websocket server on
    """

    def __init__(self, port: int):
        self._port = port

    async def main(self):
        """The main loop."""
        opus_file = os.environ.get("OPUS", "real_opus.yaml")
        sync_assets = os.environ.get("SCREENCRASH_SYNC_ASSETS", "false") == "true"
        exit_on_validation_failure = (
            os.environ.get("SCREENCRASH_EXIT_ON_VALIDATION_FAILURE", "true") == "true"
        )
        print("Loading opus...")
        self._opus = await load_opus(
            Path(__file__).parent.parent.parent / "resources" / opus_file,
            read_asset_data=sync_assets,
            exit_on_validation_failure=exit_on_validation_failure,
        )
        self._performance = Performance(self._opus)
        self._ui = UI(self._opus, self._performance.history)
        self._components: Dict[str, ComponentPeer] = {
            "internal": InternalPeer(sync_assets),
            "media": MediaPeer(sync_assets),
            "inventory": InventoryPeer(sync_assets),
            "ledController": LedControllerPeer(),
            "myggcheck": MyggCheckPeer(),
        }
        self._setup_events()
        self._distribute_assets()

        print("Started!")
        async with websockets.serve(self.socket_listener, "0.0.0.0", self._port):
            await asyncio.Future()  # run forever

    def _setup_events(self):
        self._ui.add_event_listener("next-node", self._performance.next_node)
        self._ui.add_event_listener("prev-node", self._performance.prev_node)
        self._ui.add_event_listener("goto-node", self._performance.goto_node)
        self._ui.add_event_listener("run-actions", self._performance.run_actions)
        self._ui.add_event_listener(
            "run-actions-by-id", self._performance.run_actions_by_id
        )
        self._ui.add_event_listener("choose-path", self._performance.choose_path)
        self._ui.add_event_listener("component-action", self._run_action_on_the_fly)
        self._ui.add_event_listener("component-reset", self._reset_component)
        self._ui.add_event_listener("component-restart", self._restart_component)
        self._performance.add_event_listener(
            "history-changed", self._ui.changed_history
        )
        self._performance.add_event_listener("run-action", self._run_action_by_id)

        for component in self._components.values():
            component.add_event_listener("effect-added", self._ui.effect_added)
            component.add_event_listener("effect-changed", self._ui.effect_changed)
            component.add_event_listener("effect-removed", self._ui.effect_removed)
            component.add_event_listener(
                "info-updated", self._ui.component_info_updated
            )
            component.add_event_listener(
                "state-updated", self._ui.component_state_updated
            )
            component.add_event_listener("log-message", self._ui.log_message)
            component.add_event_listener("disconnected", self._ui.component_removed)

    def _distribute_assets(self):
        for asset in self._opus.assets.values():
            for component in self._components.values():
                if any([component.handles_target(target) for target in asset.targets]):
                    component.add_asset(asset)

    def _run_action_by_id(self, action_id):
        try:
            action = self._opus.action_templates[action_id]
            self._run_action(action)
        except KeyError:
            print(f"Failed to find action or asset for action {action_id}. Skipping.")
            return

    def _run_action_on_the_fly(self, target, cmd, asset_names, params):
        action = ActionTemplate(
            "on_the_fly_action", target, cmd, "Live command", asset_names, params
        )
        self._run_action(action)

    def _run_action(self, action):
        handled = False
        assets = [self._opus.assets[key] for key in action.assets]
        for peer in self._components.values():
            if peer.handles_target(action.target) and peer.nof_instances() > 0:
                try:
                    peer.handle_action(action.target, action.cmd, assets, action.params)
                    handled = True
                except Exception as e:
                    print(f"Failed to run handle_action: {e}")
        if not handled:
            print(
                f"Warning: Action {action.id} not handled by anyone ({action.target})"
            )

        for subaction in action.subactions:
            self._run_action(subaction)

    def _reset_component(self, component_id: str):
        for peer in self._components.values():
            if peer.has_component(component_id):
                peer.reset_component(component_id)

    def _restart_component(self, component_id: str):
        for peer in self._components.values():
            if peer.has_component(component_id):
                peer.restart_component(component_id)

    async def socket_listener(self, websocket: WebSocketServerProtocol, _path: str):
        """
        This function handles an incoming websocket connection.

        Parameters
        ----------
        websocket
            The websocket
        """
        # Wait for a hello
        message = await websocket.recv()
        message_dict = json.loads(message)
        client_type = message_dict["client"]
        if client_type == "ui":
            await self._ui.handle_socket(websocket)
        elif client_type in self._components:
            print(f"Accepted client of type {client_type}")
            await self._components[client_type].handle_socket(websocket, message_dict)
        else:
            print(f"An unsupported client type tried to connect: {client_type}")


if __name__ == "__main__":
    core = Core(8001)
    try:
        asyncio.run(core.main())
    except KeyboardInterrupt:
        print("Exiting")
