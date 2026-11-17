"""The router's trusted tools catalog routes (narrative/PAGES_AND_TOOLS.md, "a catalog of trusted tools").

Runs the router's handler on a free local port against a temporary catalog folder. Nothing reaches Muse.
Usage: python3 -I test_catalog_routes.py -v
"""
import http.client
import http.server
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load_router():
    argv = sys.argv
    sys.argv = ["muse_prefix_proxy.py", "0", "127.0.0.1:9"]
    try:
        spec = importlib.util.spec_from_file_location("muse_prefix_proxy", os.path.join(HERE, "muse_prefix_proxy.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.argv = argv


R = load_router()


class CatalogRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="idli-catalog-test-")
        cls.root = os.path.join(cls.tmp, "idli-catalog")
        os.makedirs(os.path.join(cls.root, "files", "models", "x"))
        with open(os.path.join(cls.root, "catalog.json"), "w") as f:
            json.dump({"version": 1, "tools": [{"id": "t"}]}, f)
        cls.big = os.urandom(3 * (1 << 20) + 17)  # more than one 1 MB chunk
        with open(os.path.join(cls.root, "files", "models", "x", "big.bin"), "wb") as f:
            f.write(cls.big)
        with open(os.path.join(cls.root, "files", "a b.py"), "w") as f:
            f.write("print('hi')\n")
        with open(os.path.join(cls.tmp, "secret.txt"), "w") as f:
            f.write("outside")
        try:
            os.symlink(os.path.join(cls.tmp, "secret.txt"), os.path.join(cls.root, "files", "leak.txt"))
            os.symlink(os.path.join(cls.root, "files", "a b.py"), os.path.join(cls.root, "files", "inside.py"))
            cls.symlinks = True
        except OSError:
            cls.symlinks = False
        R.CATALOG_DIR = cls.root
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), R.H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r, data

    def test_catalog_json(self):
        r, data = self.req("GET", "/idli/catalog/catalog.json")
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(data)["tools"][0]["id"], "t")
        self.assertEqual(r.getheader("Content-Type"), "application/json")

    def test_big_file_streams_with_length(self):
        r, data = self.req("GET", "/idli/catalog/files/models/x/big.bin")
        self.assertEqual(r.status, 200)
        self.assertEqual(int(r.getheader("Content-Length")), len(self.big))
        self.assertEqual(data, self.big)

    def test_head(self):
        r, data = self.req("HEAD", "/idli/catalog/files/models/x/big.bin")
        self.assertEqual(r.status, 200)
        self.assertEqual(int(r.getheader("Content-Length")), len(self.big))
        self.assertEqual(data, b"")

    def test_quoted_name(self):
        r, data = self.req("GET", "/idli/catalog/files/a%20b.py")
        self.assertEqual((r.status, data), (200, b"print('hi')\n"))

    def test_rejects_escapes_and_listing(self):
        for p in ["/idli/catalog/files/../catalog.json", "/idli/catalog/files/%2e%2e/catalog.json",
                  "/idli/catalog/files/models/../../catalog.json", "/idli/catalog/files/%2Fetc%2Fpasswd",
                  "/idli/catalog/files//etc/passwd", "/idli/catalog/files/models", "/idli/catalog/files/models/",
                  "/idli/catalog/files/", "/idli/catalog/files/models/x/..%2F..%2F..%2Fsecret.txt",
                  "/idli/catalog/files/models%5C..%5C..%5Ccatalog.json", "/idli/catalog/files/C:/x",
                  "/idli/catalog/files/a%00b", "/idli/catalog/requests.jsonl", "/idli/catalog/",
                  "/idli/catalog/files/./a%20b.py"]:
            r, data = self.req("GET", p)
            self.assertEqual(r.status, 404, p)
            self.assertNotIn(b"outside", data)

    def test_symlinks(self):
        if not self.symlinks:
            self.skipTest("no symlinks on this filesystem")
        r, data = self.req("GET", "/idli/catalog/files/leak.txt")
        self.assertEqual(r.status, 404)
        r, data = self.req("GET", "/idli/catalog/files/inside.py")
        self.assertEqual(r.status, 200)

    def test_read_only(self):
        for m in ("PUT", "DELETE", "POST"):
            r, _ = self.req(m, "/idli/catalog/catalog.json", body=b"{}")
            self.assertEqual(r.status, 405, m)
        r, _ = self.req("POST", "/idli/catalog/files/models/x/big.bin", body=b"x")
        self.assertEqual(r.status, 405)

    def test_request_roundtrip(self):
        body = {"need": "Read Odia text from photos", "why": "Forms come in Odia", "platform": "win-64",
                "team": "survey", "tools_considered": ["ocr-tesseract"]}
        r, data = self.req("POST", "/idli/catalog/requests", body=json.dumps(body).encode(),
                           headers={"Content-Type": "application/json"})
        self.assertEqual(r.status, 200, data)
        j = json.loads(data)
        self.assertTrue(j["ok"])
        r, data = self.req("GET", "/idli/catalog/requests")
        reqs = json.loads(data)["requests"]
        mine = [x for x in reqs if x["id"] == j["id"]]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["need"], body["need"])
        self.assertEqual(mine[0]["tools_considered"], ["ocr-tesseract"])
        self.assertTrue(mine[0]["received"].endswith("Z"))
        with open(os.path.join(self.root, "requests.jsonl")) as f:
            self.assertTrue(all(json.loads(ln) for ln in f))

    def test_request_rejects(self):
        cases = [b"not json", b"[1]", json.dumps({"why": "no need"}).encode(),
                 json.dumps({"need": "x", "team": "../../etc"}).encode(),
                 json.dumps({"need": "x", "secret": "y"}).encode(),
                 json.dumps({"need": 5}).encode(),
                 json.dumps({"need": "x", "tools_considered": [1, 2]}).encode()]
        for b in cases:
            r, _ = self.req("POST", "/idli/catalog/requests", body=b)
            self.assertEqual(r.status, 400, b)
        r, _ = self.req("POST", "/idli/catalog/requests", body=json.dumps({"need": "x" * 17000}).encode())
        self.assertEqual(r.status, 413)
        r, _ = self.req("DELETE", "/idli/catalog/requests")
        self.assertEqual(r.status, 405)

    def test_head_elsewhere_is_refused(self):
        r, _ = self.req("HEAD", "/v1/models")
        self.assertEqual(r.status, 405)


if __name__ == "__main__":
    unittest.main()
