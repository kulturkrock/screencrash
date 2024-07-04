import socket
import os

class BluetoothConnection:

    def __init__(self):
        self.hostMACAddress = '0C:60:76:8B:10:F4' # MAC address of a Bluetooth adapter on this machine
        if "BT_PORT" in os.environ:
            print(f"Using port {int(os.environ['BT_PORT'])}")
            self.port = int(os.environ["BT_PORT"])
        else:
            self.port = 5 # Arbitrary, must match what raspberry uses
        self.backlog = 1 # Not sure what this is
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.client = None
        
    def listen(self):
        self.socket.bind((self.hostMACAddress,self.port))
        self.socket.listen(self.backlog)
        self.client, _ = self.socket.accept()
        print("connected")
        self.send_text("hello")
    
    def send_text(self, text):
        print(f"Trying to send: {text}")
        self.client.send(bytes(text, "UTF-8"))
        print(f"Sent: {text}")

    def close(self):
        print("Closing socket")	
        self.client.close()
        self.socket.close()