"""Credential-free callback completion fixture, not successful OpenAI OAuth."""
import http.server
import pathlib
import sys
import threading
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'remote'))
from oauth_callback import deliver


class CallbackTests(unittest.TestCase):
    def test_completion_and_redirect_boundaries(self):
        paths = []
        location = 'http://localhost:1455/success?secret=must-not-be-forwarded'
        status = 302
        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args): pass
            def do_GET(self):
                paths.append(self.path)
                self.send_response(200 if self.path == '/success' else status)
                self.send_header('Content-Length', '0')
                self.send_header('Location', location)
                self.end_headers()
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            deliver('/auth/callback?code=synthetic&state=synthetic', port=server.server_port)
            self.assertEqual(paths, ['/auth/callback?code=synthetic&state=synthetic','/success'])
            for location in ['https://evil.invalid/success', 'http://localhost:1455/cancel',
                             'http://localhost:1455@evil.invalid/success', '/success',
                             'http://localhost:1455/success#fragment']:
                paths.clear()
                with self.assertRaises(ValueError): deliver('/auth/callback',port=server.server_port)
                self.assertEqual(paths, ['/auth/callback'])
            status = 400
            with self.assertRaises(ValueError): deliver('/auth/callback',port=server.server_port)
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__ == '__main__': unittest.main()
