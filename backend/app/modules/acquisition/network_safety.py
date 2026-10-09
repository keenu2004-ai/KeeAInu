"""Network safety and SSRF prevention layer for external dataset discovery and controlled acquisition."""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional, Dict
import httpx


BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),        # Unique local IPv6
    ipaddress.ip_network("fe80::/10"),       # Link-local IPv6
]


def validate_url_safe(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a given URL is safe to fetch, preventing SSRF, intranet access,
    and protocol abuses.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Unsupported URL scheme: {parsed.scheme}. Only HTTP/HTTPS permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname in URL."

        # Reject literal localhost or known local hostnames
        if hostname.lower() in ("localhost", "localhost.localdomain", "127.0.0.1", "::1", "metadata.google.internal"):
            return False, f"Access to private/local host '{hostname}' is strictly prohibited."

        # Resolve IP addresses for the hostname
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            # Cannot resolve domain
            return False, f"Could not resolve hostname: {hostname}"

        for item in addr_info:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            # Check against blocked networks
            for blocked_net in BLOCKED_NETWORKS:
                if ip_obj in blocked_net:
                    return False, f"Target resolved to blocked IP '{ip_str}' in range '{blocked_net}'."

            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
                return False, f"Target resolved to prohibited non-public IP '{ip_str}'."

        return True, None

    except Exception as e:
        return False, f"Invalid or malformed URL: {str(e)}"


async def safe_fetch_metadata(
    url: str,
    timeout_sec: float = 5.0,
    max_bytes: int = 5 * 1024 * 1024  # 5 MB limit for metadata
) -> Tuple[int, bytes, Dict[str, str]]:
    """
    Safely fetch JSON/metadata payload from a public URL with SSRF checks,
    bounded timeouts, and byte limits.
    """
    is_safe, err = validate_url_safe(url)
    if not is_safe:
        raise ValueError(f"SSRF Security Violation: {err}")

    async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=False) as client:
        response = await client.get(url, headers={"User-Agent": "KeeAInu-Discovery-Agent/1.0"})
        
        # Check for redirects and re-validate destination
        if response.is_redirect and "location" in response.headers:
            redirect_url = response.headers["location"]
            is_redirect_safe, r_err = validate_url_safe(redirect_url)
            if not is_redirect_safe:
                raise ValueError(f"SSRF Security Violation in redirect: {r_err}")

        content = response.content
        if len(content) > max_bytes:
            raise ValueError(f"Response size ({len(content)} bytes) exceeds max limit of {max_bytes} bytes.")

        headers_dict = dict(response.headers)
        return response.status_code, content, headers_dict
