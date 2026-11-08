import socket
import subprocess


def _connect_bluetooth(config):
    if not config.audio_bluetooth_mac:
        raise ValueError("AUDIO_BLUETOOTH_MAC must be set")

    subprocess.run(
        ["bluetoothctl", "--timeout", "15", "connect",
         config.audio_bluetooth_mac],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _alsa_device(config):
    if config.audio_alsa_device:
        return config.audio_alsa_device
    return (
        f"bluealsa:DEV={config.audio_bluetooth_mac},"
        "PROFILE=a2dp"
    )


def _start_recorder(config):
    return subprocess.Popen(
        [
            "arecord",
            "-D", _alsa_device(config),
            "-f", "S16_LE",
            "-r", str(config.audio_sample_rate),
            "-c", str(config.audio_channels),
            "-t", "raw",
            "-q",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def stream_audio(config, destination_ip, stop_event):
    """Connect the DJI Mic audio source and forward raw PCM to the host."""
    while not stop_event.is_set():
        recorder = None
        connection = None
        try:
            _connect_bluetooth(config)
            recorder = _start_recorder(config)
            connection = socket.create_connection(
                (destination_ip, config.audio_port), timeout=10
            )
            connection.settimeout(10)
            print(
                f"Audio connected to {destination_ip}:{config.audio_port}",
                flush=True,
            )

            while not stop_event.is_set():
                audio = recorder.stdout.read(config.audio_chunk_size)
                if not audio:
                    raise RuntimeError("arecord stopped producing audio")
                connection.sendall(audio)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            if not stop_event.is_set():
                print(f"Audio stream unavailable: {exc}", flush=True)
        finally:
            if connection is not None:
                connection.close()
            if recorder is not None:
                recorder.terminate()
                try:
                    recorder.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    recorder.kill()
                    recorder.wait()

        stop_event.wait(config.audio_reconnect_delay)
