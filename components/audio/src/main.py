import argparse
import websocket
from commandhandler import CommandHandler
from coreconnection import CoreConnection


def main():
    parser = argparse.ArgumentParser(description="Audio component for ScreenCrash")
    parser.add_argument("--enable-ws-debug", action="store_true", help="Enables debug messages from websocket module")
    parser.add_argument("--no-reconnect", action="store_true", help="Do not reconnect if connection is lost")
    parser.add_argument("--reconnect-time", type=int, default=3000, help="Time (in ms) between disconnect and reconnection attempt. Cannot be used with --no-reconnect flag. Default 3000ms")
    args = parser.parse_args()

    if args.enable_ws_debug:
        websocket.enableTrace(True)

    cmd_handler = CommandHandler()
    core_connection = CoreConnection(cmd_handler.initial_message, cmd_handler.handle_message, not args.no_reconnect, args.reconnect_time)
    cmd_handler.set_event_handler(core_connection.send)
    core_connection.run()
    print("Shutting down audio component...")


if __name__ == "__main__":
    main()