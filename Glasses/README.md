# Glasses

The streamer is split into small modules:

- `hotspot.py` manages NetworkManager and discovers the host.
- `camera.py` captures and JPEG-encodes frames with Picamera2.
- `udp_stream.py` fragments and sends frames without inter-packet sleeps.
- `config.py` reads runtime settings from environment variables.

Work in progress.

Run the streamer on the Raspberry Pi with:

```bash
sudo python3 main.py
```

The default transport is 10 FPS at 640x480, with JPEG quality 75. Set
`FRAME_RATE`, `JPEG_WIDTH`, `JPEG_HEIGHT`, and `JPEG_QUALITY` to tune capture.
The sender paces complete frames only; it does not delay individual UDP
fragments, which keeps transport latency low.
