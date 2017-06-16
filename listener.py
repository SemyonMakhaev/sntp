#!/usr/bin/env python3
"""The listener of SNTP-server representation."""
import time

from socket import socket, AF_INET, SOCK_DGRAM, timeout, error
from struct import pack, unpack
from threading import Thread
from logging import warning, info


NTP_SERVER = "pool.ntp.org"
NTP_PORT = 123
TIMEOUT = 10

PATTERN = "!BBBbiIIQQQQ"


class Listener(Thread):
    """The class for a new thread representation."""
    def __init__(self, sock, host_port, client_fields, shift):
        """Initialization."""
        super(Listener, self).__init__()

        # The socket to comunicate with a client.
        self.sock = sock
        self.host_port = host_port
        self.shift = shift

        self.li_version_mode = client_fields[0]
        self.transmit_timestamp = unpack(PATTERN, client_fields)[10]


    def run(self):
        """A current time getting and a response with shifted time sending."""

        # Making a package for NTP-server with firts byte from a client request.
        # So, server answer will include a client version.
        server_reply = self.request_to_server()

        if server_reply is not None:
            response = self.shift_time(server_reply)
        else:
            # A case of failure of NTP-server request.
            # Getting time from a current machine.
            response = self.get_response()

        self.sock.sendto(response, self.host_port)

        info("Served %s", self.host_port[0])


    def request_to_server(self):
        """
        A request to NTP-server sending using a given first byte.
        This first byte has client fields values (li, version and mode),
        so a server reply will include a client version.
        Returns unpacked received data or None in case of socket timeout exceeding.
        """
        buff = pack(PATTERN, self.li_version_mode, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        sock = socket(AF_INET, SOCK_DGRAM)
        sock.settimeout(TIMEOUT)

        try:
            sock.sendto(buff, (NTP_SERVER, NTP_PORT))
            buff = sock.recv(512)
            return unpack(PATTERN, buff)

        # A case of a server request failure.
        except timeout:
            warning("Server request failed")
            return None

        except error:
            warning("Server request failed")
            return None

        finally:
            sock.close()


    def shift_time(self, server_reply):
        """Shifting a time in NTP-server reply."""
        head = pack(PATTERN[:9], *server_reply[:8])
        originate = pack("!"+PATTERN[9], self.transmit_timestamp)
        shifted_time = server_reply[9] + self.shift
        shifted_time = pack("!"+PATTERN[10], shifted_time)
        tail = pack("!"+PATTERN[11:], *server_reply[10:])

        # This reply includes a version sent by client.
        return head + originate + shifted_time + tail


    def get_response(self):
        """
        A response to the listener assembling using time from a current host.
        A package format described in RFC 4330.
        """
        now = time.gmtime()

        # Leap Indicator setting.
        if now[2] == 30 and now[1] == 6 or now[2] == 31 and now[1] == 12:
            self.li_version_mode += 1 << 6

        shifted_time = self.current_time()

        # Mode setting.
        # In client request it was set to 3 and in server responce it should be 4.
        self.li_version_mode = (self.li_version_mode - 3) | 4
        stratum = 2# Secondary reference.

        return pack(PATTERN, self.li_version_mode, stratum, 0, 0, 0, 0, 0, 0, \
                self.transmit_timestamp, shifted_time, self.current_time())


    def current_time(self):
        """Returns a current time from the machine."""
        return int((time.gmtime(0)[0] - 1900) * 31556926 + time.time()) + self.shift
