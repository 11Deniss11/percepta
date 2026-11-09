import ipaddress
import subprocess
import time

def run(*args):
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


def start(config):
    print(
        f"Using the existing Wi-Fi connection on {config.wifi_interface}; "
        "the laptop provides the hotspot."
    )


def stop(config):
    # The Wi-Fi connection belongs to the laptop and must remain up.
    return None


def _default_gateway(config):
    routes = run(
        "ip", "-4", "route", "show", "default", "dev", config.wifi_interface
    )
    for line in routes.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0] == "default" and fields[1] == "via":
            try:
                ipaddress.ip_address(fields[2])
            except ValueError:
                continue
            return fields[2]
    return None


def wait_for_client(config):
    deadline = (
        time.monotonic() + config.lease_timeout
        if config.lease_timeout > 0 else None
    )

    print("Waiting for the laptop hotspot connection...")
    while deadline is None or time.monotonic() < deadline:
        ip = config.host_ip or _default_gateway(config)
        if ip:
            config.client_ip_file.write_text(f"{ip}\n", encoding="utf-8")
            print(f"Using laptop at {ip}:{config.udp_port}")
            return ip
        time.sleep(1)
    raise TimeoutError("No laptop hotspot connection before LEASE_TIMEOUT expired")
