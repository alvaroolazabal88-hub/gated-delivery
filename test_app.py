import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

from app import Handler


class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_returns_ok(self):
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url) as resp:
            status = resp.status
            body = json.loads(resp.read())

        self.assertEqual(status, 201)
        self.assertEqual(body, {"status": "ok"})

    def test_unknown_route_returns_404(self):
        url = f"http://127.0.0.1:{self.port}/otra"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url)

        ctx.exception.close()
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()