import socket
import sys
import time

import sounddevice as sd


HOST = "127.0.0.1"
PORT = 5005
RATE = 44100
BLOCK_SIZE = 1024


def list_devices():
    for number, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            print(number, device["name"])


def get_device(value):
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        pass

    for number, device in enumerate(sd.query_devices()):
        if value.lower() in device["name"].lower():
            return number

    raise ValueError("Microphone not found: " + value)


def main():
    if "--list-devices" in sys.argv:
        list_devices()
        return

    device = None
    if "--device" in sys.argv:
        position = sys.argv.index("--device") + 1
        if position >= len(sys.argv):
            raise ValueError("--device needs a value")
        device = get_device(sys.argv[position])

    while True:
        try:
            print("Connecting to %s:%d..." % (HOST, PORT))
            connection = socket.create_connection((HOST, PORT))
            print("Connected. Press Ctrl+C to stop.")

            with connection:
                # Capture raw mono 16-bit audio in the format expected by the ROS node.
                stream = sd.RawInputStream(
                    samplerate=RATE,
                    blocksize=BLOCK_SIZE,
                    device=device,
                    channels=1,
                    dtype="int16",
                )
                with stream:
                    while True:
                        data, overflowed = stream.read(BLOCK_SIZE)
                        if overflowed:
                            print("Warning: microphone overflowed", file=sys.stderr)
                        connection.sendall(data)
        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except (ConnectionError, OSError) as error:
            print("Connection lost: %s" % error, file=sys.stderr)
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, sd.PortAudioError) as error:
        print("Error: %s" % error, file=sys.stderr)
        sys.exit(1)
