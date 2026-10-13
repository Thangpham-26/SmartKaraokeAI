"""Restore one phone's ADB reverse mapping after USB reconnects; stdlib only."""
import argparse
import socket
import time
from datetime import datetime


def receive_exact(connection, size):
    result = b""
    while len(result) < size:
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise RuntimeError("ADB connection closed")
        result += chunk
    return result


def request(connection, command):
    data = command.encode("utf-8")
    connection.sendall(f"{len(data):04x}".encode("ascii") + data)
    status = receive_exact(connection, 4)
    if status != b"OKAY":
        message = receive_exact(connection, int(receive_exact(connection, 4), 16))
        raise RuntimeError(message.decode("utf-8", errors="replace"))


def devices():
    with socket.create_connection(("127.0.0.1", 5037), timeout=5) as connection:
        request(connection, "host:devices")
        size = int(receive_exact(connection, 4), 16)
        lines = receive_exact(connection, size).decode().splitlines()
    return dict(line.split("\t", 1) for line in lines if "\t" in line)


def device_service(serial, service):
    with socket.create_connection(("127.0.0.1", 5037), timeout=5) as connection:
        request(connection, "host:transport:" + serial)
        request(connection, service)
        result = b""
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            result += chunk
        return result.decode("utf-8", errors="replace")


def ensure_reverse(serial, port):
    if devices().get(serial) != "device":
        return "waiting for authorized USB device"
    endpoint = f"tcp:{port}"
    raw = device_service(serial, "reverse:list-forward")
    rows = raw[4:].splitlines()  # Four ASCII hex digits prefix the list payload.
    if any(row.split()[-2:] == [endpoint, endpoint] for row in rows):
        return "ready"
    result = device_service(serial, f"reverse:forward:{endpoint};{endpoint}")
    if not result.startswith("OKAY"):
        raise RuntimeError("ADB could not establish reverse forwarding: " + result)
    return "restored USB reverse mapping"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="Only this authorized phone is configured")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be 1–65535")
    previous = None
    while True:
        try:
            state = ensure_reverse(args.serial, args.port)
        except (OSError, ValueError, RuntimeError) as exc:
            if not args.watch:
                raise
            state = "waiting for ADB: " + str(exc)
        if state != previous:
            print(f"{datetime.now().isoformat(timespec='seconds')} {state}", flush=True)
            previous = state
        if not args.watch:
            return
        time.sleep(3)


if __name__ == "__main__":
    main()
