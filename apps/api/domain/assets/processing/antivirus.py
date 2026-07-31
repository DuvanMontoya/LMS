from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from pathlib import Path

from domain.assets.exceptions import AssetProcessingError

CHUNK_SIZE = 64 * 1024
MAX_RESPONSE_BYTES = 4 * 1024


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    signature: str


class ClamAVClient:
    def __init__(
        self, *, host: str, port: int, timeout_seconds: int, maximum_size: int
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.maximum_size = maximum_size

    def scan_path(self, path: Path) -> ScanResult:
        if path.stat().st_size > self.maximum_size:
            raise AssetProcessingError("File exceeds antivirus scan limit.")
        response = bytearray()
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=self.timeout_seconds
            ) as connection:
                connection.settimeout(self.timeout_seconds)
                connection.sendall(b"zINSTREAM\0")
                with path.open("rb") as source:
                    total = 0
                    while chunk := source.read(CHUNK_SIZE):
                        total += len(chunk)
                        if total > self.maximum_size:
                            raise AssetProcessingError(
                                "File exceeds antivirus scan limit."
                            )
                        connection.sendall(struct.pack("!I", len(chunk)))
                        connection.sendall(chunk)
                connection.sendall(struct.pack("!I", 0))
                while len(response) <= MAX_RESPONSE_BYTES:
                    chunk = connection.recv(512)
                    if not chunk:
                        break
                    response.extend(chunk)
                    if b"\0" in chunk or b"\n" in chunk:
                        break
        except AssetProcessingError:
            raise
        except (OSError, TimeoutError) as error:
            raise AssetProcessingError("Antivirus service unavailable.") from error
        if len(response) > MAX_RESPONSE_BYTES:
            raise AssetProcessingError("Antivirus returned an invalid response.")
        text = bytes(response).rstrip(b"\0\r\n")
        try:
            decoded = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AssetProcessingError(
                "Antivirus returned an invalid response."
            ) from error
        if decoded == "stream: OK":
            return ScanResult(clean=True, signature="")
        if decoded.startswith("stream: ") and decoded.endswith(" FOUND"):
            signature = decoded[len("stream: ") : -len(" FOUND")].strip()
            if not signature or len(signature) > 255:
                raise AssetProcessingError("Antivirus returned an invalid response.")
            return ScanResult(clean=False, signature=signature)
        raise AssetProcessingError("Antivirus returned an error.")
