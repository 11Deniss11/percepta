import socket
import struct
import time

from camera import capture_frame, close_camera, open_camera


MAGIC = b"PJPG"
PROTOCOL_VERSION = 2
HEADER = struct.Struct("!4sBIIHIQ")
MAX_PACKET_PAYLOAD = 65535 - HEADER.size


def stream(config, destination_ip):
    if not 0 < config.chunk_size <= MAX_PACKET_PAYLOAD:
        raise ValueError(f"CHUNK_SIZE must be between 1 and {MAX_PACKET_PAYLOAD}")

    destination = (destination_ip, config.udp_port)
    interval = 1.0 / config.frame_rate if config.frame_rate > 0 else 0
    frame_number = 0
    next_frame_time = time.monotonic()
    camera = open_camera(config)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        try:
            while True:
                # Keep a steady cadence without sleeping after a slow frame.
                wait = next_frame_time - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                started = time.monotonic()
                jpeg = capture_frame(camera)
                if len(jpeg) > 0xFFFFFFFF:
                    raise ValueError("JPEG is too large for the UDP frame format")

                # Send every part immediately; waiting between packets adds latency.
                chunks = []
                for offset in range(0, len(jpeg), config.chunk_size):
                    chunks.append(jpeg[offset:offset + config.chunk_size])
                if len(chunks) > 65535:
                    raise ValueError("JPEG is too large for the UDP frame format")

                for chunk_number, chunk in enumerate(chunks):
                    packet = HEADER.pack(
                        MAGIC,
                        PROTOCOL_VERSION,
                        frame_number,
                        chunk_number,
                        len(chunks),
                        len(jpeg),
                        time.time_ns(),
                    ) + chunk
                    sock.sendto(packet, destination)

                frame_number = (frame_number + 1) & 0xFFFFFFFF
                next_frame_time = started + interval
                if next_frame_time < time.monotonic():
                    next_frame_time = time.monotonic()
        finally:
            close_camera(camera)
