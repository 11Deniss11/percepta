import ipaddress
import subprocess
import time
from pathlib import Path

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
    # Remove an old connection first so repeated runs start cleanly.
    stop(config)
    run("ip", "neigh", "flush", "dev", config.ap_interface)
    run(
        "nmcli", "device", "wifi", "hotspot",
        "ifname", config.ap_interface,
        "con-name", config.ap_connection,
        "ssid", config.ap_ssid,
        "password", config.ap_password,
    )
    run(
        "nmcli", "connection", "modify", config.ap_connection,
        "802-11-wireless.band", "bg",
        "802-11-wireless.mode", "ap",
        "802-11-wireless.channel", "6",                # FIX 1: Force a safe channel (1-11) for ESP32
        "wifi-sec.key-mgmt", "wpa-psk",
        "wifi-sec.psk", config.ap_password,
        "wifi-sec.auth-alg", "open",
        "wifi-sec.proto", "rsn",
        "wifi-sec.pairwise", "ccmp",
        "wifi-sec.group", "ccmp",
        "wifi-sec.pmf", "0",                           # FIX 2: Disable PMF (802.11w) to prevent ESP32 auth failure
        "ipv4.method", "shared",
        "ipv4.addresses", f"{config.ap_address}/24",
        "ipv6.method", "disabled",
    )
    run("nmcli", "connection", "up", config.ap_connection)
    print(
        f"Hotspot {config.ap_ssid!r} is active on "
        f"{config.ap_interface} ({config.ap_address})"
    )


def stop(config):
    try:
        run("nmcli", "connection", "down", config.ap_connection)
    except RuntimeError as exc:
        if not any(
            message in str(exc).lower()
            for message in ("unknown connection", "not active", "no active connection")
        ):
            raise
    try:
        run("nmcli", "connection", "delete", config.ap_connection)
    except RuntimeError as exc:
        if "unknown connection" not in str(exc).lower():
            raise


def _lease_files():
    files = []
    for directory in (
        Path("/var/lib/NetworkManager"),
        Path("/var/lib/misc"),
        Path("/run/NetworkManager"),
    ):
        if directory.is_dir():
            for path in directory.glob("*lease*"):
                if path.is_file():
                    files.append(path)
    return files


def _first_client_ip(config, seen_ips):
    # The neighbor table is preferred because old lease files can be stale.
    try:
        neighbors = run("ip", "-4", "neigh", "show", "dev", config.ap_interface)
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
            if ip != config.ap_address and ip not in seen_ips:
                seen_ips.add(ip)
                return ip
        return None

    for path in _lease_files():
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
            if ip != config.ap_address and ip not in seen_ips:
                seen_ips.add(ip)
                return ip
    return None


def wait_for_client(config):
    seen_ips = set()
    deadline = (
        time.monotonic() + config.lease_timeout
        if config.lease_timeout > 0 else None
    )
    try:
        config.client_ip_file.unlink()
    except FileNotFoundError:
        pass

    print("Waiting for the first device to join the hotspot...")
    while deadline is None or time.monotonic() < deadline:
        ip = _first_client_ip(config, seen_ips)
        if ip:
            config.client_ip_file.write_text(f"{ip}\n", encoding="utf-8")
            print(f"Using first client at {ip}:{config.udp_port}")
            return ip
        time.sleep(1)
    raise TimeoutError("No client joined the hotspot before LEASE_TIMEOUT expired")
