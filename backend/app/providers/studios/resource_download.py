"""Bounded HTTPS download with pinned public DNS and a configured host allowlist."""

import http.client
import ipaddress
import socket
import ssl
from pathlib import Path
from urllib.parse import urljoin, urlsplit


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("resource_private_address")
        # Connect to one of the checked numeric addresses, retaining TLS hostname
        # verification. Prefer IPv4 on Windows hosts where an advertised IPv6
        # route may be unavailable, then fall back across every resolved public
        # address instead of treating the first DNS record as authoritative.
        addresses = sorted(addresses, key=lambda item: item[0] != socket.AF_INET)
        last_error = None
        for family, socktype, proto, _, address in addresses:
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(self.timeout)
            try:
                sock.connect(address)
                self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
                return
            except (OSError, ssl.SSLError) as error:
                last_error = error
                sock.close()
        if last_error:
            raise last_error
        raise OSError("resource_connection_unavailable")


def download_resource(url: str, destination: Path, hosts: list[str], *, max_bytes=100 * 1024 * 1024):
    for _ in range(4):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or not parsed.hostname
            or parsed.hostname.lower() not in {h.lower() for h in hosts}
        ):
            raise ValueError("resource_host_not_registered")
        connection = PublicHTTPSConnection(parsed.hostname, timeout=30, context=ssl.create_default_context())
        try:
            path = parsed.path or "/"
            connection.request(
                "GET",
                path + ("?" + parsed.query if parsed.query else ""),
                headers={"User-Agent": "res-editing-resources/1", "Accept-Encoding": "identity"},
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                url = urljoin(url, response.getheader("Location", ""))
                continue
            if response.status != 200:
                raise ValueError("resource_download_failed")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("resource_encoding_unsupported")
            size = 0
            with destination.open("wb") as output:
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("resource_too_large")
                    output.write(chunk)
            if not size:
                raise ValueError("resource_empty")
            return url
        finally:
            connection.close()
    raise ValueError("resource_redirect_limit")
