"""Use a11y-audit as a library: audit a local folder of HTML files.

    python examples/audit_from_python.py path/to/site
"""

import functools
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from a11y_audit import Options, audit_urls
from a11y_audit.report import to_markdown


def main(folder):
    folder = Path(folder).resolve()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(folder))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)  # random free port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    urls = [base + p.relative_to(folder).as_posix() for p in sorted(folder.rglob("*.html"))]
    try:
        report = audit_urls(urls, Options(delay_s=0, fail_on="serious"))
    finally:
        server.shutdown()
    print(to_markdown(report))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
