import json
import urllib.parse


class FakeServer:
    """Callable opener for GBPClient: routes (method, path) to scripted responses and records calls."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __call__(self, req):
        u = urllib.parse.urlparse(req.full_url)
        q = dict(urllib.parse.parse_qsl(u.query))
        body = json.loads(req.data.decode()) if req.data else None
        self.calls.append((req.get_method(), u.path, q, body, req.get_header("Authorization")))
        status, headers, payload = self.handler(req.get_method(), u.path, q, body, len(self.calls))
        return status, headers, json.dumps(payload).encode() if payload is not None else b""
