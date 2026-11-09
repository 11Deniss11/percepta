import ipaddress
import subprocess
import time

def run(*args, redact=()):
    command = " ".join(args)
    try:
        result = subprocess.run(
            args, check=True, text=True, capture_output=True
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command is not installed: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout).strip()
        for secret in redact:
            if secret:
                command = command.replace(secret, "<redacted>")
                detail = detail.replace(secret, "<redacted>")
        raise RuntimeError(f"{command} failed: {detail}") from exc
    return result.stdout


def start(config):
    run("nmcli", "radio", "wifi", "on")
    try:
        run(
            "nmcli", "connection", "up", "id", config.wifi_connection,
            "ifname", config.wifi_interface,
        )
    except RuntimeError as exc:
        if "unknown connection" not in str(exc).lower():
            raise
        run(
            "nmcli", "device", "wifi", "connect", config.wifi_ssid,
            "password", config.wifi_password,
            "ifname", config.wifi_interface,
            "name", config.wifi_connection,
            redact=(config.wifi_password,),
        )
    run(
        "nmcli", "connection", "modify", config.wifi_connection,
        "connection.autoconnect", "yes",
        "connection.interface-name", config.wifi_interface,
    )
    print(
        f"Connected to Wi-Fi {config.wifi_ssid!r} on "
        f"{config.wifi_interface}; the laptop provides the hotspot."
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
