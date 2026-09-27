"""Validate Cloudflare Access app tokens, never unsigned forwarding headers."""
import re
import time
import threading
import httpx
import jwt


class AccessKeys:
    def __init__(self, issuer):
        self.url = issuer + '/cdn-cgi/access/certs'
        self.keys = {}
        self.fetched = 0
        self.lock = threading.Lock()

    def __call__(self, token):
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
            raise ValueError('Invalid signature header')
        kid = header['kid']
        with self.lock:
            now = time.monotonic()
            if now - self.fetched > 300 or (kid not in self.keys and now - self.fetched > 30):
                # Explicit direct HTTPS, no ambient proxy and no redirects to another issuer.
                with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
                    response = client.get(self.url)
                    response.raise_for_status()
                    if len(response.content) > 1024 * 1024:
                        raise ValueError('JWKS too large')
                    keys = response.json().get('keys', [])
                self.keys = {key['kid']: jwt.PyJWK.from_dict(key).key for key in keys
                             if key.get('kty') == 'RSA' and key.get('use', 'sig') == 'sig'}
                self.fetched = now
            if kid not in self.keys:
                raise ValueError('Unknown signing key')
            return self.keys[kid]


class AccessIdentity:
    def __init__(self, issuer, audience, keys=None):
        if not re.fullmatch(r'https://[a-zA-Z0-9-]+\.cloudflareaccess\.com', issuer):
            raise ValueError('Expected HTTPS Cloudflare team issuer')
        if not audience:
            raise ValueError('Access application audience is required')
        self.issuer, self.audience = issuer, audience
        # A keys callback is dependency injection for tests, never a command-line bypass.
        self.keys = keys or AccessKeys(issuer)

    def verify(self, token):
        if not isinstance(token, str) or len(token) > 16384:
            raise ValueError('Invalid token')
        key = self.keys(token)
        claims = jwt.decode(token, getattr(key, 'key', key), algorithms=['RS256'],
                            audience=self.audience, issuer=self.issuer,
                            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'email']})
        if (claims.get('type') != 'app' or not isinstance(claims['sub'], str) or
                not claims['sub'] or len(claims['sub']) > 256 or
                not isinstance(claims['email'], str) or '@' not in claims['email'] or
                len(claims['email']) > 320):
            raise ValueError('Human application identity required')
        return dict(subject=claims['sub'], issuer=claims['iss'],
                    email=claims['email'].strip().lower(), expires=claims['exp'])
