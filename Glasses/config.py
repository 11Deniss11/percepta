import os
from pathlib import Path


class StreamConfig:
    def __init__(self):
        # Environment variables make the same script usable on different setups.
        self.ap_interface = os.getenv("AP_INTERFACE", "wlan0")
        self.ap_connection = os.getenv("AP_CONNECTION", "percepta-hotspot")
        self.ap_ssid = os.getenv("AP_SSID", "Percepta")
        self.ap_password = os.getenv("AP_PASSWORD", "percepta-camera")
        self.ap_address = os.getenv("AP_ADDRESS", "192.168.50.1")
        self.udp_port = int(os.getenv("UDP_PORT", "5000"))
        self.jpeg_width = int(os.getenv("JPEG_WIDTH", "640"))
        self.jpeg_height = int(os.getenv("JPEG_HEIGHT", "480"))
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", "75"))
        self.frame_rate = float(os.getenv("FRAME_RATE", "10"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1200"))
        self.lease_timeout = float(os.getenv("LEASE_TIMEOUT", "300"))
        self.client_ip_file = Path(
            os.getenv("CLIENT_IP_FILE", "first_client_ip.txt")
        )
