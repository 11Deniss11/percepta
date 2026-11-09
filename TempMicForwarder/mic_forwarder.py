import socket
import sys
import time

import sounddevice as sd


HOST = "127.0.0.1"
PORT = 5005
RATE = 44100
BLOCK_SIZE = 1024


def main():
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
