import threading

from config import StreamConfig
from audio_stream import stream_audio
from hotspot import start, stop, wait_for_client
from udp_stream import stream

def main():
    config = StreamConfig()
    audio_stop = threading.Event()
    audio_thread = None
    try:
        # Start networking before waiting for the host and camera stream.
        start(config)
        destination_ip = wait_for_client(config)
        audio_thread = threading.Thread(
            target=stream_audio,
            args=(config, destination_ip, audio_stop),
            name="audio-stream",
            daemon=True,
        )
        audio_thread.start()
        stream(config, destination_ip)
    finally:
        audio_stop.set()
        if audio_thread is not None:
            audio_thread.join(timeout=3)
        stop(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
