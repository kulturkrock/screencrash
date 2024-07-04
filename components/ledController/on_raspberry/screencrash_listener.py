# This should be copied to the Raspberry
# Currently contains a hard-coded address to Anton's laptop
import asyncio
import socket
import RPi.GPIO as GPIO
import time

serverMACAddress = "0C:60:76:8B:10:F4"
port = 5

GPIO.setmode(GPIO.BCM)
# TODO dynamic
GPIO.setup(14, GPIO.OUT)
GPIO.setup(25, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)

PINS = {"one": 14, "two": 25, "three": 16}

pin_states = {14: False, 25: False, 16: False}
async def listen():
    loop = asyncio.get_event_loop()
    while True:
        print("Trying to connect...")
        try:
            s = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
            )
            s.connect((serverMACAddress, port))
            print("connected")
            while 1:
                data = await loop.sock_recv(s, 1024)
                print(f"Got command: {data}")
                parts = data.decode("utf-8").split(":")
                command = parts[0]
                if command == "on":
                    id = parts[1]
                    pin = PINS[id]
                    print(f"Turning on pin {pin}")
                    GPIO.output(pin, 1)
                    pin_states[pin] = True
                elif command == "off":
                    id = parts[1]
                    pin = PINS[id]
                    print(f"Turning off pin {pin}")
                    GPIO.output(pin, 0)
                    pin_states[pin] = False
                elif command == "toggle":
                    id = parts[1]
                    pin = PINS[id]
                    print(f"Toggling pin {pin}")
                    if pin_states[pin]:
                        GPIO.output(pin, 0)
                        pin_states[pin] = False
                    else:
                        GPIO.output(pin, 1)
                        pin_states[pin] = True
        except OSError as e:
            print(e)
            print("Waiting 5s")
            await asyncio.sleep(5)
        finally:
            s.close()

async def blink():
    while True:
        await asyncio.sleep(1)
        id = "one"
        pin = PINS[id]
        print(f"Toggling pin {pin}")
        if pin_states[pin]:
            GPIO.output(pin, 0)
            pin_states[pin] = False
        else:
            GPIO.output(pin, 1)
            pin_states[pin] = True

async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(listen())
    #loop.create_task(blink())
    while True:
        await asyncio.sleep(10)

asyncio.run(main())