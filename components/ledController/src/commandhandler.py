import random
import string
import os

class CommandHandler:

    def __init__(self, bluetooth_connection):
        auto_generated_id = ''.join(random.choices(string.ascii_uppercase, k=16))
        self._component_id = os.environ.get("SCREENCRASH_COMPONENT_ID", auto_generated_id)
        self._bluetooth_connection = bluetooth_connection
        self._custom_event_handler = None

    def set_event_handler(self, event_handler):
        self._custom_event_handler = event_handler

    def _emit(self, data):
        if self._custom_event_handler:
            self._custom_event_handler(data)
        else:
            print(f"Got an event: {data}")

    def _create_error_msg(self, msg):
        result = {"messageType": "cmd-error", "msg": msg}
        return result
    
    def initial_message(self):
        return {"client": "ledController"}

    def handle_message(self, message):
        try:
            cmd = message["command"]
            id = message.get("id")
            return self._handle_command(cmd, id, message)
        except Exception as e:
            print(e)
            return self._create_error_msg(f"Failed to carry out command. {e}")

    def _handle_command(self, cmd, id, message):
        result = None
        if cmd == "req_component_info":
            result = self._announce_component_info()
        elif cmd == "on":
            print(f"Turning on LED: {id}")
            self._bluetooth_connection.send_text(f"on:{id}")
        elif cmd == "off":
            print(f"Turning off LED: {id}")
            self._bluetooth_connection.send_text(f"off:{id}")
        elif cmd == "toggle":
            print(f"Toggling LED: {id}")
            self._bluetooth_connection.send_text(f"toggle:{id}")
        else:
            print("Unhandled message: {}".format(message))
            result = self._create_error_msg("Unsupported command")

        return result

    def _announce_component_info(self):
        self._emit({
            "messageType": "component_info",
            "componentId": self._component_id,
            "componentName": "ledController",
            "status": "online"
        })
