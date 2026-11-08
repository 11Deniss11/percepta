from config import StreamConfig
from hotspot import start, stop, wait_for_client
from udp_stream import stream

def main():
    config = StreamConfig()
    try:
        # Start networking before waiting for the host and camera stream.
        start(config)
        stream(config, wait_for_client(config))
    finally:
        stop(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
