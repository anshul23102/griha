from fastapi import FastAPI
from fastapi.testclient import TestClient

from griha import web


def _site(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "index.html").write_text("<!doctype html><html><head><script>var t=1</script></head><body>home</body></html>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("do not serve")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    return app, web.mount(app, tmp_path)


def test_spa_routes_assets_and_api_coexist(tmp_path):
    app, headers = _site(tmp_path)
    c = TestClient(app)
    assert c.get("/api/ping").json() == {"ok": True}
    assert c.get("/case/A-1/letter").text.endswith("home</body></html>")          # client-side route falls back to index
    assert c.get("/assets/app.js").status_code == 200 and c.get("/favicon.svg").text == "<svg/>"
    assert c.get("/api/unknown").status_code == 404 and c.get("/api/unknown").headers["content-type"].startswith("application/json")
    assert c.get("/assets/missing.js").status_code == 404
    assert c.head("/").status_code == 200 and c.head("/case/A-1").status_code == 200       # uptime monitors use HEAD


def test_no_path_traversal(tmp_path):
    app, _ = _site(tmp_path)
    c = TestClient(app)
    for p in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "//etc/passwd"):
        assert "do not serve" not in c.get(p).text


def test_csp_pins_the_inline_script_only(tmp_path):
    _, headers = _site(tmp_path)
    csp = headers["Content-Security-Policy"]
    assert "script-src 'self' 'sha256-" in csp and "'unsafe-inline'" not in csp.split("style-src")[0] and "unsafe-eval" not in csp


def test_unknown_pages_are_404_with_the_shell_and_missing_files_are_plain_404(tmp_path):
    app, _ = _site(tmp_path)
    c = TestClient(app)
    r = c.get("/no-such-page")
    assert r.status_code == 404 and "home</body>" in r.text                      # the router can draw its own not-found page, crawlers see a 404
    assert c.get("/robots.txt").status_code == 404 and c.get("/sitemap.xml").status_code == 404   # not the app shell dressed as a file
    assert c.get("/apply").status_code == 200 and c.get("/desk").status_code == 200 and c.get("/").status_code == 200
