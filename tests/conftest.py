import functools
import socket
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def fixture_server():
    """Serve tests/fixtures on 127.0.0.1 with a random free port."""
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d/" % server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def closed_port_url():
    """A URL on a local port that nothing listens on."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d/" % port


@pytest.fixture(scope="session")
def fixture_report(fixture_server):
    """One browser run over all fixture pages, shared by the browser tests."""
    from a11y_audit.engine import Options, audit_urls

    urls = [fixture_server + name for name in ("good.html", "bad.html", "trap.html", "stuck.html")]
    report = audit_urls(urls, Options(delay_s=0, fail_on="serious"))
    return {p["url"].rsplit("/", 1)[-1]: p for p in report["pages"]}, report
