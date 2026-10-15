#!/usr/bin/env python3
"""Carve the phishing mail from memory and read its PDF attachment."""
from pathlib import Path
from email import policy
from email.parser import BytesParser
import re

ROOT = Path(__file__).resolve().parent
memory = (ROOT / 'mem.dmp').read_bytes()
start = memory.index(b'Return-Path: <contracts@')
terminator = b'--=_gaian_7f2a_boundary--'
end = memory.index(terminator, start) + len(terminator)
message = BytesParser(policy=policy.default).parsebytes(memory[start:end])
attachments = [part for part in message.walk() if part.get_content_type() == 'application/pdf']
assert len(attachments) == 1
pdf = attachments[0].get_payload(decode=True)
assert pdf == (ROOT / 'Invoice_FoundationOne.pdf').read_bytes()
match = re.search(rb'\((GAIANSPACE\{[^}]+\})\) Tj', pdf)
assert match
print('Sender:', message['From'])
print('Attachment:', attachments[0].get_filename())
print(match[1].decode())
