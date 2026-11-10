"""Optional single-origin hosting: serve the built frontend from the API process (used by the container image).
One origin means no CORS and no dev server; the page CSP is derived from the built index.html so the theme bootstrap
script stays hash-pinned and nothing else inline is allowed."""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def mount(app: FastAPI, dist: Path) -> dict[str, str]:
    """Registers the SPA routes on `app` (call after all API routes) and returns the headers to send with page responses."""
    dist = dist.resolve()
    index = (dist / "index.html").read_text()
    inline = re.findall(r"<script>(.*?)</script>", index, re.S)
    hashes = " ".join("'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'" for s in inline)
    csp = (f"default-src 'self'; script-src 'self' {hashes}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
           "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "not found")
        f = (dist / path).resolve()
        if path and f.is_file() and dist in f.parents:           # favicon and other root files; never outside dist
            return FileResponse(f)
        return HTMLResponse(index)

    return {"Content-Security-Policy": csp}
