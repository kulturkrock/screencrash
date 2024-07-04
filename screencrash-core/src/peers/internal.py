from typing import Any, List, Dict
from opus import Asset
from peers.component import ComponentPeer


class InternalPeer(ComponentPeer):
    """
    Peer for basic internal actions, such as logging etc.

    Parameters
    ----------
    sync_assets
        Whether to sync assets
    """

    def __init__(self, sync_assets: bool):
        super().__init__(["internal"], sync_assets)

    async def handle_socket(self, *_):
        """This method will raise an exception if called."""
        raise Exception(
            "An InternalPeer cannot get an external connection. Someone is messing with you.")

    def nof_instances(self):
        return 1    # Always available

    def handle_action(self, target_type: str, cmd: str, assets: List[Asset], params: Dict[str, Any]):
        """Process the given action."""
        if cmd == "print":
            print(params.get("text", "[print command found no text to print]"))
        elif cmd == "nop":
            # No operation. Do nothing.
            pass
        else:
            super().handle_action(target_type, cmd, assets, params)
