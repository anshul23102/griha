import re

from starlette.testclient import TestClient


class KeyedClient(TestClient):
    """Behaves like the browser: remembers each case's access key from responses and sends it back for that case."""
    keys: dict = {}

    def request(self, method, url, **kw):
        m = re.search(r"/api/cases/([A-Z0-9-]+)", str(url))
        if m and m.group(1) in self.keys:
            kw["headers"] = {"X-Case-Key": self.keys[m.group(1)], **(kw.get("headers") or {})}
        r = super().request(method, url, **kw)
        try:
            j = r.json()
            if isinstance(j, dict) and "access_key" in j:
                self.keys[j["case_id"]] = j["access_key"]
        except Exception:
            pass
        return r
