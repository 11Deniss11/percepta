#!/usr/bin/env python3
"""Create a Wi-Fi hotspot and stream JPEG frames to its first client over UDP."""

from __future__ import annotations

import io
import ipaddress
import os
import socket
import struct
import subprocess
import time
from pathlib import Path
from typing import Iterator


AP_INTERFACE = os.getenv("AP_INTERFACE", "wlan0")
AP_CONNECTION = os.getenv("AP_CONNECTION", "percepta-hotspot")
AP_SSID = os.getenv("AP_SSID", "Percepta")
AP_PASSWORD = os.getenv("AP_PASSWORD", "percepta-camera")
AP_ADDRESS = os.getenv("AP_ADDRESS", "192.168.50.1")
UDP_PORT = int(os.getenv("UDP_PORT", "5000"))
JPEG_WIDTH = int(os.getenv("JPEG_WIDTH", "640"))
JPEG_HEIGHT = int(os.getenv("JPEG_HEIGHT", "480"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "75"))
FRAME_RATE = float(os.getenv("FRAME_RATE", "10"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
LEASE_TIMEOUT = float(os.getenv("LEASE_TIMEOUT", "300"))
CLIENT_IP_FILE = Path(os.getenv("CLIENT_IP_FILE", "first_client_ip.txt"))

MAGIC = b"PJPG"
PROTOCOL_VERSION = 1
# magic, version, frame number, chunk number, chunk count, JPEG size, timestamp
HEADER = struct.Struct("!4sBIIHHQ")


def run(*args: str) -> str:
    """Run a command and return its output, preserving useful errors."""
    try:
        result = subprocess.run(
            args, check=True, text=True, capture_output=True
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command is not installed: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout).strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}") from exc
    return result.stdout


def start_hotspot() -> None:
    """Create or replace the NetworkManager hotspot connection."""
    stop_hotspot()

    run(
        "ip",
        "neigh",
        "flush",
        "dev",
        AP_INTERFACE,
    )

    run(
        "nmcli",
        "device",
        "wifi",
        "hotspot",
        "ifname",
        AP_INTERFACE,
        "con-name",
        AP_CONNECTION,
        "ssid",
        AP_SSID,
        "password",
        AP_PASSWORD,
    )

    run(
        "nmcli",
        "connection",
        "modify",
        AP_CONNECTION,
        "ipv4.method",
        "shared",
        "ipv4.addresses",
        f"{AP_ADDRESS}/24",
        "ipv6.method",
        "disabled",
    )
    run("nmcli", "connection", "up", AP_CONNECTION)
    print(f"Hotspot {AP_SSID!r} is active on {AP_INTERFACE} ({AP_ADDRESS})")


def stop_hotspot() -> None:
    """Deactivate and remove the hotspot connection if it exists."""
    try:
        run("nmcli", "connection", "down", AP_CONNECTION)
    except RuntimeError as exc:
        message = str(exc).lower()
        if "unknown connection" not in message and "not active" not in message:
            raise

    try:
        run("nmcli", "connection", "delete", AP_CONNECTION)
    except RuntimeError as exc:
        if "unknown connection" not in str(exc).lower():
            raise


def lease_files() -> Iterator[Path]:
    candidates = (
        Path("/var/lib/NetworkManager"),
        Path("/var/lib/misc"),
        Path("/run/NetworkManager"),
    )
    seen: set[Path] = set()
    for directory in candidates:
        if directory.is_dir():
            for path in directory.glob("*lease*"):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    yield path


def first_client_ip(seen_ips: set[str]) -> str | None:
    """Return the first newly observed DHCP client address."""
    try:
        neighbors = run("ip", "-4", "neigh", "show", "dev", AP_INTERFACE)
    except RuntimeError:
        neighbors = ""
    else:
        for line in neighbors.splitlines():
            fields = line.split()
            if not fields or fields[-1:] in (["FAILED"], ["INCOMPLETE"]):
                continue
            ip = fields[0]
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue
            if ip != AP_ADDRESS and ip not in seen_ips:
                seen_ips.add(ip)
                return ip
        # A readable neighbor table is authoritative. Lease files can retain
        # addresses from a previous hotspot session.
        return None

    for path in lease_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 3:
                continue
            ip = fields[2]
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue
            if ip != AP_ADDRESS and ip not in seen_ips:
                seen_ips.add(ip)
                return ip

    return None


def wait_for_first_client() -> str:
    seen_ips: set[str] = set()
    deadline = time.monotonic() + LEASE_TIMEOUT if LEASE_TIMEOUT > 0 else None
    try:
        CLIENT_IP_FILE.unlink()
    except FileNotFoundError:
        pass
    print("Waiting for the first device to join the hotspot...")
    while deadline is None or time.monotonic() < deadline:
        ip = first_client_ip(seen_ips)
        if ip:
            CLIENT_IP_FILE.write_text(f"{ip}\n", encoding="utf-8")
            print(f"Using first client at {ip}:{UDP_PORT}")
            return ip
        time.sleep(1)
    raise TimeoutError("No client joined the hotspot before LEASE_TIMEOUT expired")


def jpeg_frames() -> Iterator[bytes]:
    """Yield JPEGs from Picamera2, with OpenCV as an optional fallback."""
    try:
        from picamera2 import Picamera2  # type: ignore[import-not-found]
    except ImportError:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "Install Picamera2 or opencv-python-headless to capture images"
            ) from exc
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            raise RuntimeError("Unable to open the camera with OpenCV")
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, JPEG_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, JPEG_HEIGHT)
        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Camera stopped returning frames")
                ok, encoded = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                )
                if not ok:
                    raise RuntimeError("Unable to encode camera frame as JPEG")
                yield encoded.tobytes()
        finally:
            camera.release()
    else:
        camera = Picamera2()
        camera.configure(
            camera.create_video_configuration(
                main={"size": (JPEG_WIDTH, JPEG_HEIGHT), "format": "RGB888"}
            )
        )
        camera.start()
        try:
            while True:
                output = io.BytesIO()
                camera.capture_file(output, format="jpeg")
                yield output.getvalue()
        finally:
            camera.stop()
            camera.close()


def stream_jpegs(destination_ip: str) -> None:
    if CHUNK_SIZE <= 0 or CHUNK_SIZE > 65535 - HEADER.size:
        raise ValueError("CHUNK_SIZE must be between 1 and 65510")
    destination = (destination_ip, UDP_PORT)
    interval = 1.0 / FRAME_RATE if FRAME_RATE > 0 else 0
    frame_number = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for jpeg in jpeg_frames():
            started = time.monotonic()
            chunks = [
                jpeg[offset : offset + CHUNK_SIZE]
                for offset in range(0, len(jpeg), CHUNK_SIZE)
            ]
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
            remaining = interval - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)


def main() -> None:
    try:
        start_hotspot()
        client_ip = wait_for_first_client()
        stream_jpegs(client_ip)
    finally:
        stop_hotspot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
