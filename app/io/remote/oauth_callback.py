"""Fixed-target OAuth callback delivery, independent of browser redirects/content."""
import http.client
import urllib.parse


def deliver(callback, port=1455):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
    try:
        conn.request('GET', callback, headers={'Host': 'localhost:1455'})
        response = conn.getresponse()
        code = response.status
        location = response.getheader('Location', '')
        response.read(65536)
        if code in (302, 303):
            target = urllib.parse.urlsplit(location)
            if (target.scheme != 'http' or target.netloc != 'localhost:1455' or
                    target.path != '/success' or target.fragment):
                raise ValueError('Unsupported sign-in completion redirect')
            # Codex has saved credentials but awaits /success to terminate login.
            # Discard redirect query parameters, which can contain account claims.
            conn.request('GET', '/success', headers={'Host': 'localhost:1455'})
            response = conn.getresponse()
            code = response.status
            response.read(65536)
        if code != 200:
            raise ValueError('Sign-in callback was rejected')
    finally:
        conn.close()
