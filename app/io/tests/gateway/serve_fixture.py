"""Local-only integration harness, never a production gateway configuration."""
import json
import os
import pathlib
import sys
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'gateway'))
import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from identity import AccessIdentity
from runtime import DockerRuntime
from server import create_app
from store import Store

if __name__ == '__main__':
    os.umask(0o077)
    state = pathlib.Path(sys.argv[1]); state.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer, audience = 'https://io-test.cloudflareaccess.com', 'io-synthetic-audience'
    for subject in ('alice', 'bob'):
        token = jwt.encode(dict(iss=issuer, aud=[audience], sub=subject, email=subject+'@example.invalid', type='app',
                                iat=int(time.time()), exp=int(time.time())+7200), key, algorithm='RS256')
        (state / (subject+'.jwt')).write_text(token)
    app = create_app(Store(state/'gateway.sqlite3'), AccessIdentity(issuer, audience, keys=lambda _:key.public_key()), DockerRuntime())
    uvicorn.run(app, host='127.0.0.1', port=8788, access_log=False, log_level='warning')
