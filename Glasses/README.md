# Raspberry Pi JPEG hotspot streamer

`streamer.py` creates a NetworkManager Wi-Fi hotspot, waits for the first DHCP
client, remembers that client's IP address, and sends JPEG frames to UDP port
`5000`. Frames are split into packets of 1200 bytes to avoid normal Wi-Fi MTU
fragmentation. UDP is intentionally lossy; the receiver drops incomplete
frames.

## Raspberry Pi setup

On Raspberry Pi OS, install the camera stack and NetworkManager on the host:

```sh
sudo apt install network-manager python3-picamera2
```

Enable the camera if required by the OS, then run the script as root because
creating an AP and reading DHCP leases require host networking privileges:

```sh
sudo -E AP_SSID=MyCamera AP_PASSWORD='use-a-password' python3 streamer.py
```

The default interface is `wlan0`. Override it with `AP_INTERFACE` if needed.
The first device whose DHCP lease is observed is the destination. Its address
is printed and saved to `first_client_ip.txt` before streaming starts. Set
`CLIENT_IP_FILE` to change that path.

## Docker/devcontainer

The container must share the host network and access the host's NetworkManager
DBus socket and camera device. A normal bridged container cannot create a
hotspot on the Pi's Wi-Fi adapter. For a development container, use equivalent
settings to:

```sh
docker run --rm -it --network host --privileged \
  -v /run/dbus:/run/dbus \
  --device /dev/video0 \
  -e AP_SSID=MyCamera -e AP_PASSWORD='use-a-password' \
  percepta-glasses
```

If Picamera2 is not available in the image, install the platform-specific
Raspberry Pi package on the host or install `opencv-python-headless` and use a
USB/V4L2 camera. The `Dockerfile` includes NetworkManager and `iproute2`, but
camera access and DBus still come from the host.

Useful settings:

| Variable | Default | Purpose |
|---|---:|---|
| `AP_INTERFACE` | `wlan0` | Wi-Fi adapter used for the hotspot |
| `AP_SSID` | `Percepta` | Hotspot name |
| `AP_PASSWORD` | `percepta-camera` | WPA password |
| `AP_ADDRESS` | `192.168.50.1` | Hotspot gateway address |
| `CLIENT_IP_FILE` | `first_client_ip.txt` | File where the first client IP is recorded |
| `FRAME_RATE` | `10` | Frames per second |
| `JPEG_WIDTH` / `JPEG_HEIGHT` | `640` / `480` | Camera resolution |
| `JPEG_QUALITY` | `75` | JPEG quality |
| `CHUNK_SIZE` | `1200` | JPEG bytes per UDP packet |
| `LEASE_TIMEOUT` | `300` | Seconds to wait for the first client; `0` means forever |

## Test receiver

Run this on the device that joins the hotspot:

```sh
python3 receiver.py --output frames
```

It reassembles complete frames and writes them as numbered `.jpg` files.
