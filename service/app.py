#!/usr/bin/env python3
"""Kestrel Array mission console (fictional, offline).

The import desk loads catalog fragments referenced by a JSON "$ref" and
inlines their contents into the imported document. Refs are resolved
relative to the catalog directory; a cleaner strips path-traversal before
the join so imports cannot wander off the catalog drawer."""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.environ.get("CATALOG_DIR", os.path.join(os.path.dirname(__file__), "data"))
PORT = int(os.environ.get("PORT", "8000"))


def clean_ref(ref):
    # keep imports inside the catalog drawer: drop absolute paths and
    # strip the obvious traversal token before joining.
    if ref.startswith("/") or ref.startswith("\\"):
        return None
    return ref.replace("../", "").replace("..\\", "")


def resolve(obj):
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            safe = clean_ref(obj["$ref"])
            if safe is None:
                return {"$ref": obj["$ref"], "error": "absolute refs are not allowed"}
            path = os.path.join(BASE, safe)
            with open(path, "r", errors="replace") as f:
                return {"$ref": obj["$ref"], "resolved": f.read()}
        return {k: resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve(v) for v in obj]
    return obj

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, indent=2).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/health"):
            return self._send(200, {"status": "ok", "console": "Kestrel Array"})
        if self.path.startswith("/api/catalog"):
            try:
                cat = json.load(open(os.path.join(BASE, "catalog.json")))
            except Exception as e:
                return self._send(500, {"error": str(e)})
            return self._send(200, cat)
        self._send(404, {"error": "not found", "hint": "POST /api/catalog/import"})
    def do_POST(self):
        if not self.path.startswith("/api/catalog/import"):
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send(400, {"error": "bad json: %s" % e})
        try:
            return self._send(200, {"imported": resolve(body)})
        except FileNotFoundError:
            return self._send(404, {"error": "ref target not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})

if __name__ == "__main__":
    print("console on :%d (catalog dir %s)" % (PORT, BASE))
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
