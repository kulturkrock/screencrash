from typing import Any, List, Dict
from opus import Asset

from peers.component import ComponentPeer


class MyggCheckPeer(ComponentPeer):
    """
    Handles communication with myggcheck component.
    Does nothing with commands, just passes them on.

    Parameters
    ----------
    """

    def __init__(self):
        super().__init__(["myggcheck"], False)

    def handle_action(
        self, target_type: str, cmd: str, assets: List[Asset], params: Dict[str, Any]
    ):
        """Process the given action."""
        data = {"command": cmd, "channel": 1, "type": target_type}
        data.update(params)
        self.send_command(data)
