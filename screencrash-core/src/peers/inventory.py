from typing import Any, List, Dict
from opus import Asset

from peers.component import ComponentPeer


class InventoryPeer(ComponentPeer):
    """
    Handles communication with inventory component.

    Parameters
    ----------
    """

    def __init__(self, sync_assets: bool):
        super().__init__(["inventory"], sync_assets)
        self._active_achievement_requests = {}

    def handle_component_message(self, component_id: str, message_type: str, message: object):
        if message_type == "configuration":
            self.handle_component_state_update(component_id, { "configuration": message["data"] })
        elif message_type == "items":
            self.handle_component_state_update(component_id, { "items": message["items"] })
        elif message_type == "money":
            self.handle_component_state_update(component_id, { "money": message["money"], "currency": message.get("currency", "money") })
        elif message_type == "achievements":
            self.handle_component_state_update(component_id, { "achievements": message["achievements"] })
        elif message_type == "items_visibility":
            self.handle_component_state_update(component_id, { "items_visibility": message["visible"] })
        elif message_type == "achievement_reached":
            self.handle_achievement_reached(component_id, message["achievement"])
        else:
            super().handle_component_message(message_type, message)

    def handle_component_disconnect(self, component_id):
        super().handle_component_disconnect(component_id)
        if component_id in self._active_achievement_requests:
            del self._active_achievement_requests[component_id]

    def handle_achievement_reached(self, component_id, achievement):
        if component_id not in self._active_achievement_requests:
            self._active_achievement_requests[component_id] = []

        for ach in self._active_achievement_requests[component_id]:
            if ach.get("name") == achievement.get("name"):
                print("Already added achievement notification in list, skipping...")
                return # Already added in list

        self._active_achievement_requests[component_id].append(achievement)
        self.handle_component_state_update(component_id, { "achievementsReached": self._active_achievement_requests[component_id] })

    def handle_action(self, target_type: str, cmd: str, assets: List[Asset], params: Dict[str, Any]):
        """Process the given action."""
        data = {
            "command": cmd,
            "channel": 1,
            "type": target_type
        }
        data.update(params)
        self.send_command(data)