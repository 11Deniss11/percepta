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

The default transport is 5 FPS at 640x480, with JPEG quality 75. `FRAME_RATE`
can lower the rate, but the sender will never exceed 5 FPS. Set
`JPEG_WIDTH`, `JPEG_HEIGHT`, `JPEG_QUALITY`, and `CHUNK_DELAY` to tune capture
and packet smoothing. The small default chunk delay reduces Wi-Fi packet loss
without adding a noticeable frame delay.
The sender paces complete frames only; it does not delay individual UDP
fragments, which keeps transport latency low.
