import websocket
import json
import os
from time import sleep

class CoreConnection:

    def __init__(self, get_announce_message, on_message_callback, reconnect = True, reconnect_time = 3000):
        self._get_announce_message = get_announce_message
        self._handle_message_callback = on_message_callback
        self._reconnect = reconnect
        self._reconnect_time = reconnect_time
        self._ws = None

    def run(self):
        while self._reconnect:
            url = f"ws://{os.environ.get('CORE', 'localhost:8001')}"
            self._ws = websocket.WebSocketApp(url,
                                            on_open=self._on_open,
                                            on_message=self._on_message,
                                            on_error=self._on_error,
                                            on_close=self._on_close)

            critical_error = self._ws.run_forever(ping_interval=1, ping_payload=self._get_heartbeat_msg())

            # Don't reconnect if user presses Ctrl+C
            if self._reconnect and critical_error:
                sleep(self._reconnect_time / 1000.0)
                print("Reconnecting...")
            else:
                self.stop()

    def send(self, data):
        if self._ws is not None:
            self._ws.send(json.dumps(data))
        else:
            print("Failed to send data on websocket. Seems to be down")

    def stop(self):
        self._reconnect = False
        if self._ws:
            self._ws.close()

    def _get_heartbeat_msg(self):
        return json.dumps({
            "messageType": "heartbeat",
            "component": "audio",
            "channel": 1
        })

    def _on_message(self, ws, message):
        if self._handle_message_callback:
            data = json.loads(message)
            response = self._handle_message_callback(data)
            if not response is None:
                ws.send(json.dumps(response))
        else:
            print("Got message: {} (no message handler)".format(message))

    def _on_open(self, ws):
        print("Connected to core")
        ws.send(json.dumps(self._get_announce_message()))

    def _on_error(self, ws, error):
        # Print errors, but not if user presses Ctrl+C
        if not isinstance(error, KeyboardInterrupt):
            print("Got error: {}".format(error if str(error) else "[Unknown]"))

    def _on_close(self, ws, close_status_code, close_msg):
        extra_info = f"Code={close_status_code}. Message={close_msg}" if close_status_code else ""
        print(f"Connection closed to core. {extra_info}")
        self._ws = None