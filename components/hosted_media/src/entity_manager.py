class EntityManager:

    def __init__(self, component_id: str):
        self.component_id = component_id
        self.last_created: str = ""

    def create(self, entity_id: str) -> None:
        self.last_created = entity_id

    def get_component_id(self) -> str:
        return self.component_id

    def get_last_created(self) -> str:
        return self.last_created
