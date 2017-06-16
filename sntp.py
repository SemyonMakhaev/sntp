#!/usr/bin/env python3
"""The lying SNTP-server."""
import sys
import time
import logging

from socket import socket, error, AF_INET, SOCK_DGRAM, timeout
from select import select
from argparse import ArgumentParser

from listener import Listener, NTP_PORT, TIMEOUT


CLOSING_COMMAND = "avada kedavra"


def main():
    """SNTP-requests receiving and responses with shifted time sending."""
    shift = argument_parse()
    maximum_shift_value = 2 ** 32 - int((time.gmtime(0)[0] - 1900) * 31556926 + time.time())

    if shift >= maximum_shift_value or shift <= -maximum_shift_value:
        logging.error("Shift value exceeded")
        sys.exit(0)

    source = get_ip()
    if source is None:
        sys.exit(0)

    sock = socket(AF_INET, SOCK_DGRAM)

    try:
        sock.bind((source, NTP_PORT))
    except error:
        logging.error("Permission denied")
        sock.close()
        sys.exit(0)

    print("Server has bound ({}, {})".format(source, NTP_PORT))
    print('For connection closing use "{}" command'.format(CLOSING_COMMAND))

    try:
        while True:
            rsocks = select([sock, sys.stdin], [], [], 0.01)[0]
            if sock in rsocks:
                data, host_port = sock.recvfrom(512)
                Listener(sock, host_port, data, shift).start()
            if sys.stdin in rsocks and CLOSING_COMMAND.startswith(input()):
                break
    finally:
        print("Connection has been closed")
        sock.close()


def argument_parse():
    """Argument parsing."""
    parser = ArgumentParser(prog="python3 sntp.py", \
        description="The SNTP-server lying on a set seconds number.", \
        epilog="(c) Semyon Makhaev, 2016. All rights reserved.")
    parser.add_argument("shift", type=int, default=0, \
        help="The number of falsification seconds. The value can be negative. \
        Default value is 0", nargs="?")
    return parser.parse_args().shift


def get_ip():
    """
    Request to the external host sending.
    Returns an external IP-address of a current host.
    """
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    try:
        # Any arbitrary existing host and opened
        # for TCP-requests port of this host are suitable.
        sock.connect(("google.com", 4343))
        return sock.getsockname()[0]

    except timeout:
        logging.error("Can't get IP-address")
        return None

    finally:
        sock.close()


if __name__ == "__main__":
    main()
