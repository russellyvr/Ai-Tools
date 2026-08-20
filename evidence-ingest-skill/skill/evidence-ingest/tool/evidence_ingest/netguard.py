"""Network guard: default-deny socket layer for the closed-corpus pipeline.

Installed at import time in ``__main__.py`` BEFORE anything else. The
allowlist is empty by default; only ``ocr --allow-loopback-ocr --endpoint``
adds exactly one (loopback-ip, port) pair. Hostnames are never resolvable —
``getaddrinfo`` rejects anything that is not a literal loopback IP, so DNS
exfiltration is impossible. Every permitted connection is reported to a
custody callback. Any violation raises :class:`NetworkBlockedError`, which
the CLI maps to exit code 4.
"""
from __future__ import annotations

import ipaddress
import socket as _socket

_LOOPBACK_IPS = {"127.0.0.1", "::1"}


class NetworkBlockedError(Exception):
    """Raised on any attempt to reach a network destination not allowlisted."""


# (ip, port) pairs. Empty by default — closed corpus.
_ALLOWLIST: set[tuple[str, int]] = set()

# Exact hostnames permitted through _guarded_getaddrinfo. Populated ONLY by
# allow_cloud_host() — the audited cloud-OCR exception. Empty by default.
_ALLOWED_HOSTNAMES: set[str] = set()

# Optional callback invoked as fn(ip, port) on every ALLOWED connection so
# custody can log it. Set by the ocr stage.
_on_allowed_connection = None

_installed = False
_OrigSocket = _socket.socket
_orig_getaddrinfo = _socket.getaddrinfo


def allow_loopback(ip: str, port: int) -> None:
    """Add exactly one loopback (ip, port) to the allowlist.

    Refuses non-loopback IPs outright — there is no code path that can
    allowlist a routable address.
    """
    if ip not in _LOOPBACK_IPS:
        raise NetworkBlockedError(
            f"refusing to allowlist non-loopback address {ip!r} "
            "(only 127.0.0.1 / ::1 permitted)"
        )
    if not (0 < int(port) < 65536):
        raise NetworkBlockedError(f"invalid port {port!r}")
    _ALLOWLIST.add((ip, int(port)))


def allow_cloud_host(hostname: str, port: int) -> list[str]:
    """AUDITED EXCEPTION: pin one cloud hostname into the allowlist.

    This is the ONLY path that ever admits a non-loopback destination, and
    the only permitted caller is the ``ocr`` CLI stage when the operator has
    passed BOTH ``--google-docai`` and ``--allow-cloud-ocr``. It:

      * resolves ``hostname`` exactly once via the ORIGINAL (pre-guard)
        ``getaddrinfo``,
      * pins every resolved IP + ``port`` into the allowlist (DNS is not
        consulted again, so later resolution cannot be poisoned mid-run),
      * remembers the exact hostname so the guarded ``getaddrinfo`` permits
        that literal string and nothing else, and
      * returns the resolved IP list so the caller can custody-log them.

    Everything else remains default-deny.
    """
    hostname = hostname.strip().lower().rstrip(".")
    if not hostname or _normalize_ip(hostname) is not None:
        raise NetworkBlockedError(
            f"allow_cloud_host requires a DNS hostname, got {hostname!r}")
    if not (0 < int(port) < 65536):
        raise NetworkBlockedError(f"invalid port {port!r}")
    try:
        infos = _orig_getaddrinfo(hostname, port, type=_socket.SOCK_STREAM)
    except OSError as e:
        raise NetworkBlockedError(
            f"could not resolve cloud host {hostname!r}: {e}") from e
    ips = sorted({_normalize_ip(str(info[4][0])) for info in infos
                  if _normalize_ip(str(info[4][0]))})
    if not ips:
        raise NetworkBlockedError(f"no usable addresses for {hostname!r}")
    for ip in ips:
        _ALLOWLIST.add((ip, int(port)))
    _ALLOWED_HOSTNAMES.add(hostname)
    return ips


def set_connection_logger(fn) -> None:
    global _on_allowed_connection
    _on_allowed_connection = fn


def allowlist_snapshot() -> list[tuple[str, int]]:
    return sorted(_ALLOWLIST)


def allowed_hostnames_snapshot() -> list[str]:
    return sorted(_ALLOWED_HOSTNAMES)


def _normalize_ip(host: str) -> str | None:
    """Return canonical IP string if ``host`` is a literal IP, else None."""
    try:
        return str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        return None


def _check_address(address, log: bool = True) -> None:
    """Validate a connect() target tuple against the allowlist.

    Permits literal loopback IPs with an allowlisted (ip, port), pinned IPs
    admitted by allow_cloud_host(), or the exact pinned hostname itself.
    Raises NetworkBlockedError for everything else.
    """
    if not isinstance(address, tuple) or len(address) < 2:
        raise NetworkBlockedError(f"blocked connection to non-inet address {address!r}")
    host, port = address[0], address[1]
    name = str(host).strip().lower().rstrip(".")
    if name in _ALLOWED_HOSTNAMES:
        if log and _on_allowed_connection is not None:
            _on_allowed_connection(name, int(port))
        return
    ip = _normalize_ip(str(host))
    if ip is None:
        raise NetworkBlockedError(
            f"blocked connection to hostname {host!r} (not an admitted host)"
        )
    if (ip, int(port)) not in _ALLOWLIST:
        raise NetworkBlockedError(
            f"blocked connection to {ip}:{port} (not in allowlist {allowlist_snapshot()})"
        )
    if _on_allowed_connection is not None:
        _on_allowed_connection(ip, int(port))


class GuardedSocket(_OrigSocket):
    """socket.socket subclass enforcing the closed-corpus allowlist."""

    def connect(self, address):  # noqa: D102
        _check_address(address)
        return super().connect(address)

    def connect_ex(self, address):  # noqa: D102
        _check_address(address)
        return super().connect_ex(address)

    def sendto(self, *args, **kwargs):  # noqa: D102
        raise NetworkBlockedError("sendto() is blocked (closed-corpus policy)")


def _guarded_create_connection(address, *args, **kwargs):
    # Validate first without logging: for pinned hostnames the concrete
    # pinned-IP connect below produces the custody event, so the dialed IP
    # (not just the name) is what enters the chain.
    _check_address(address, log=False)
    host, port = address[0], address[1]
    name = str(host).strip().lower().rstrip(".")
    if name in _ALLOWED_HOSTNAMES:
        # Connect ONLY to the IPs pinned at allow_cloud_host() time — the
        # hostname is never re-resolved, defeating mid-run DNS repinning.
        pinned = [ip for (ip, p) in sorted(_ALLOWLIST)
                  if p == int(port) and ip not in _LOOPBACK_IPS]
        if not pinned:
            raise NetworkBlockedError(
                f"no pinned addresses for {name!r}:{port}")
        err: OSError | None = None
        for ip in pinned:
            family = _socket.AF_INET6 if ":" in ip else _socket.AF_INET
            sock = GuardedSocket(family, _socket.SOCK_STREAM)
            try:
                timeout = args[0] if args else kwargs.get("timeout")
                if timeout is not None and timeout is not getattr(
                        _socket, "_GLOBAL_DEFAULT_TIMEOUT", None):
                    sock.settimeout(timeout)
                sock.connect((ip, int(port)))
                return sock
            except OSError as e:
                err = e
                sock.close()
        raise err if err else OSError(f"could not reach any pinned IP for {name}")
    ip = _normalize_ip(str(host))
    family = _socket.AF_INET6 if ":" in ip else _socket.AF_INET
    sock = GuardedSocket(family, _socket.SOCK_STREAM)
    try:
        timeout = args[0] if args else kwargs.get("timeout")
        if timeout is not None and timeout is not getattr(
                _socket, "_GLOBAL_DEFAULT_TIMEOUT", None):
            sock.settimeout(timeout)
        sock.connect((ip, int(port)))
        return sock
    except OSError:
        sock.close()
        raise


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    """Resolve literal loopback IPs, plus the exact hostnames admitted by the
    audited allow_cloud_host() exception; every other lookup is refused."""
    if host is not None:
        name = str(host).strip().lower().rstrip(".")
        if name in _ALLOWED_HOSTNAMES:
            return _orig_getaddrinfo(host, port, *args, **kwargs)
    ip = _normalize_ip(str(host)) if host is not None else None
    if ip is None or ip not in _LOOPBACK_IPS:
        raise NetworkBlockedError(
            f"blocked name resolution for {host!r} (literal loopback IPs only)"
        )
    return _orig_getaddrinfo(ip, port, *args, **kwargs)


def install() -> None:
    """Monkey-patch the socket module with the guarded implementations."""
    global _installed
    if _installed:
        return
    _socket.socket = GuardedSocket
    _socket.create_connection = _guarded_create_connection
    _socket.getaddrinfo = _guarded_getaddrinfo
    _installed = True


def is_installed() -> bool:
    return _installed
