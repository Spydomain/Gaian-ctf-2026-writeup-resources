#!/bin/sh
set -e
mkdir -p /opt/console/secret
# the operator schedule is provisioned at boot, outside the catalog web-root.
# the restricted page is sealed; the console unseals it into the secret room on start.
SCHED_BLOB="06e0aa0dc30dbb8dfb5de3b44e8ec2fa71f5ecea0ce9f171c7edadf97b8e28f31ee6b11cd51dbbe89a27e3b044fa7233a681e6fe60b1c555e4d6e3c21aaa12bd29ca8e79a17ccd9d8a2281c32d9e1020c5f5c8df309bc24afcdef9c055b35bbd24c2912dfd31fdc0db66df8172c0411486b083cf27d7df46e39ff9c651b815e96de2b810d006a4fdfb4cf48e65cb462595e1d7d216cfc211fedaffda5bb106d9"
SCHED_BLOB="$SCHED_BLOB" python3 - <<'PY'
import os, hashlib
blob = bytes.fromhex(os.environ["SCHED_BLOB"])
key = hashlib.sha256(os.environ.get("STATION_ID", "KESTREL-ARRAY").encode()).digest()
data = bytes(c ^ key[i % len(key)] for i, c in enumerate(blob))
with open("/opt/console/secret/pass_schedule.txt", "wb") as f:
    f.write(data)
PY
exec python3 /opt/console/app.py
