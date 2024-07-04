from dataclasses import dataclass, field
from typing import Any, Dict
from websockets.server import WebSocketServerProtocol

@dataclass
class ComponentInfo:
    componentId: str
    componentName: str
    status: str

@dataclass
class ComponentState:
    info: ComponentInfo
    state: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class ComponentData:
    info: ComponentInfo
    socket: WebSocketServerProtocol
