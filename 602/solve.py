#!/usr/bin/env python3
"""Reassemble the aircraft's indexed acknowledgement bytes from its PCAP."""
import re
from pathlib import Path
import dpkt

path = Path(__file__).resolve().parent / "mars_control.pcap"
characters = {}
with path.open("rb") as source:
    for _, raw in dpkt.pcap.Reader(source):
        try:
            ip = dpkt.ethernet.Ethernet(raw).data
            udp = ip.data
        except (AttributeError, dpkt.UnpackError):
            continue
        if not isinstance(udp, dpkt.udp.UDP) or udp.sport != 7099 or udp.dport != 54700:
            continue
        packet = bytes(udp.data)
        if len(packet) != 5 or packet[:2] != b"S\x01" or packet[2:] == b"\0\0\0":
            continue
        index = packet[3] | packet[4] << 8
        value = chr(packet[2])
        assert index not in characters or characters[index] == value
        characters[index] = value

assert sorted(characters) == list(range(240, 275))
message = "".join(characters[index] for index in sorted(characters))
flag = re.fullmatch(r"GAIANSPACE\{[^}]+\}", message).group()
assert flag == "GAIANSPACE{fl1ght_telemetry_str3am}"
print(f"{len(characters)} unique indexed ACKs: {flag}")
