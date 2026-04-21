import ipaddress
import socket

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.poolmanager import PoolManager
import urllib3.util.connection as urllib3_cn


def create_safe_connection(
    address,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address=None,
    socket_options=None,
):
    host, port = address

    addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    valid_ip = None

    for item in addr_info:
        ip_str = item[4][0]
        # Handle IPv6 zone indices
        if "%" in ip_str:
            ip_str = ip_str.split("%")[0]

        ip = ipaddress.ip_address(ip_str)

        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        ):
            raise requests.exceptions.ConnectionError(
                f"Security Error: Blocked unsafe IP {ip_str} for host {host}"
            )

        valid_ip = ip_str
        break

    if not valid_ip:
        raise requests.exceptions.RequestException(f"Could not resolve {host}")

    return urllib3_cn.create_connection(
        (valid_ip, port), timeout, source_address, socket_options
    )


class SafeHTTPConnection(HTTPConnection):
    def _new_conn(self):
        extra_kw = {}
        if self.source_address:
            extra_kw["source_address"] = self.source_address
        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        host = getattr(self, "_dns_host", self.host)
        return create_safe_connection((host, self.port), self.timeout, **extra_kw)


class SafeHTTPSConnection(HTTPSConnection):
    def _new_conn(self):
        extra_kw = {}
        if self.source_address:
            extra_kw["source_address"] = self.source_address
        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        host = getattr(self, "_dns_host", self.host)
        return create_safe_connection((host, self.port), self.timeout, **extra_kw)


class SafeHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = SafeHTTPConnection


class SafeHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = SafeHTTPSConnection


class SafePoolManager(PoolManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool_classes_by_scheme = {
            "http": SafeHTTPConnectionPool,
            "https": SafeHTTPSConnectionPool,
        }


class SafeAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = SafePoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )
