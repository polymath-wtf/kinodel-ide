"""Resolve installation storage and explicitly selected native ComfyUI settings."""

from dataclasses import dataclass, field
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import ssl
import sys
from typing import Literal
from urllib.parse import quote, unquote, urlsplit, urlunsplit


class ComfyUIConfigError(ValueError):
    """Safe diagnostics; never include the rejected setting in the message."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code


@dataclass(frozen=True)
class ComfyUIConnection:
    connection: Literal["local", "server"]
    endpoint: str = field(repr=False)
    endpoint_digest: str
    auth_token: str | None = field(default=None, repr=False)
    verify: bool | ssl.SSLContext = field(default=True, repr=False)


def _comfyui_endpoint(raw: str) -> str:
    try:
        if not raw or len(raw.encode("utf-8")) > 8192 \
                or any(char.isspace() or ord(char) < 32 or 127 <= ord(char) <= 159 for char in raw) \
                or any(char in raw for char in "\\?#"):
            raise ValueError
        url = urlsplit(raw)
        if url.scheme not in ("http", "https") or not url.hostname or "@" in url.netloc \
                or url.netloc.endswith(":") or (url.port is not None and not 1 <= url.port <= 65535):
            raise ValueError
        host = url.hostname
        try:
            ip = ipaddress.ip_address(host)
            host = f"[{ip.compressed}]" if ip.version == 6 else ip.compressed
        except ValueError:
            host = host.encode("idna").decode("ascii").lower()
            if len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                          for label in host.rstrip(".").split(".")):
                raise ValueError
        path = url.path
        decoded = unquote(path)
        if any(char == "\\" or ord(char) < 32 or 127 <= ord(char) <= 159 for char in decoded) \
                or any(part in (".", "..") for part in decoded.split("/")) \
                or re.search(r"%(?![0-9a-fA-F]{2})", path):
            raise ValueError
        authority = host + (f":{url.port}" if url.port is not None else "")
        path = quote(path.rstrip("/"), safe="/%:@!$&'()*+,;=-._~") + "/"
        return urlunsplit((url.scheme, authority, path, "", ""))
    except (ValueError, UnicodeError):
        raise ComfyUIConfigError("invalid_endpoint", "Selected ComfyUI endpoint must be a valid HTTP(S) URL without credentials, query or fragment.") from None


def resolve_comfyui_connection(selection: Literal["local", "server"] | None = None) -> ComfyUIConnection:
    """Resolve only the selected endpoint; credentials and private CA remain separate."""
    connection = selection if selection is not None else os.environ.get("COMFYUI_CONNECTION", "local")
    if connection not in ("local", "server"):
        raise ComfyUIConfigError("invalid_connection", "ComfyUI connection must be local or server.")
    raw = os.environ.get("COMFYUI_LOCAL_ENDPOINT", "http://127.0.0.1:8188") if connection == "local" \
        else os.environ.get("COMFYUI_SERVER_ENDPOINT", "")
    endpoint = _comfyui_endpoint(raw)
    token = os.environ.get("COMFYUI_AUTH_TOKEN") or None
    if token and any(not 33 <= ord(char) <= 126 for char in token):
        raise ComfyUIConfigError("invalid_auth_token", "ComfyUI bearer token must contain only visible ASCII characters without spaces.")
    verify: bool | ssl.SSLContext = True
    ca_file = os.environ.get("COMFYUI_CA_FILE")
    if ca_file:
        try:
            if not Path(ca_file).is_absolute():
                raise ValueError
            verify = ssl.create_default_context(cafile=ca_file)
        except (OSError, ValueError):
            raise ComfyUIConfigError("invalid_ca_file", "ComfyUI CA file must be an absolute path to a readable trusted certificate bundle.") from None
    return ComfyUIConnection(connection, endpoint, hashlib.sha256(endpoint.encode()).hexdigest(), token, verify)


def resolve_data_root() -> Path:
    """Default to installation/stuff; keep other source paths and the venv protected."""
    installation = Path(__file__).resolve().parents[1]
    override = os.environ.get("KINODEL_DATA_ROOT")
    raw = override if override is not None else str(installation / "stuff")

    # Normalize the extended local-drive spelling before containment checks.
    if os.name == "nt" and raw.startswith("\\\\?\\") and len(raw) >= 7 and raw[5:7] == ":\\":
        raw = raw[4:]
    if raw.startswith(("\\\\", "//")):
        raise ValueError("Network and device data roots are unsupported")
    if not raw or not Path(raw).is_absolute():
        raise ValueError("Data root must be an absolute local path")
    root = Path(raw).resolve()
    if str(root).startswith(("\\\\", "//")):
        raise ValueError("Network data roots are unsupported")
    if root.is_relative_to(installation) and not root.is_relative_to(installation / "stuff"):
        raise ValueError("Data root must be outside installation source paths")
    if root.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("Data root must be outside the venv")
    if root.exists() and not root.is_dir():
        raise ValueError("Data root must be a directory")
    return root
