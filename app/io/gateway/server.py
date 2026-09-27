"""V1 gateway: verified identity -> persistent workspace -> private worker."""
import argparse
import asyncio
import contextlib
import os
import pathlib
import time
import urllib.parse
import weakref

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from identity import AccessIdentity
from runtime import DockerRuntime
from store import Store

GET_PATHS = {'status', 'events', 'files', 'file', 'conversations'}
POST_PATHS = {'login', 'login/callback', 'start', 'input', 'resize', 'interrupt', 'stop', 'logout', 'files', 'conversations/delete'}
LIMIT = 10 * 1024 * 1024


def create_app(store, identity, runtime):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    locks = weakref.WeakValueDictionary()

    def workspace_lock(workspace_id):
        return locks.setdefault(workspace_id, asyncio.Lock())

    @app.middleware('http')
    async def authenticate(request, call_next):
        try:
            request.state.identity = await asyncio.to_thread(identity.verify, request.headers.get('cf-access-jwt-assertion', ''))
        except Exception:
            return JSONResponse({'error': 'Cloudflare Access sign-in required'}, status_code=401)
        # Desktop main-process requests have no Origin. Browser navigations to the landing page
        # are read-only; no browser script is an API client, including generated live apps.
        if request.headers.get('origin') or (request.method != 'GET' and request.headers.get('sec-fetch-site') in ('cross-site', 'same-site')):
            return JSONResponse({'error': 'Browser API requests are not accepted'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        return response

    def owned(request, workspace_id):
        return store.owned(workspace_id, request.state.identity)

    @app.get('/')
    @app.get('/desktop-ready')
    async def landing():
        return HTMLResponse('<!doctype html><title>IO Access</title><h1>Signed in to IO</h1><p>You can return to the IO desktop application.</p>')

    @app.get('/identity')
    async def who(request: Request):
        return {'email': request.state.identity['email'], 'executionMode': 'remote'}

    @app.post('/workspace')
    async def workspace(request: Request):
        record = store.get_or_create(request.state.identity)
        async with workspace_lock(record['id']):
            if not owned(request, record['id']):
                return JSONResponse({'error': 'Workspace was deleted; reconnect'}, status_code=409)
            try:
                await asyncio.to_thread(runtime.ensure, record)
                store.state(record['id'], 'ready')
            except Exception:
                store.state(record['id'], 'unavailable')
                return JSONResponse({'error': 'Workspace could not start; operator diagnostics required'}, status_code=503)
        return {'workspaceId': record['id'], 'state': 'ready', 'executionMode': 'remote', 'persistent': True}

    @app.post('/workspaces/{workspace_id}/end')
    async def delete_workspace(workspace_id: str, request: Request):
        async with workspace_lock(workspace_id):
            record = owned(request, workspace_id)
            if not record:
                return JSONResponse({'error': 'Workspace not found'}, status_code=404)
            store.state(workspace_id, 'deleting')
            try:
                await asyncio.to_thread(runtime.delete, record)
                store.remove(workspace_id)
            except Exception:
                return JSONResponse({'error': 'Workspace deletion incomplete; retry deletion'}, status_code=503)
        return {'ok': True}

    @app.api_route('/workspaces/{workspace_id}/{route:path}', methods=['GET', 'POST'])
    async def proxy(workspace_id: str, route: str, request: Request):
        record = owned(request, workspace_id)
        if not record:
            return JSONResponse({'error': 'Workspace not found'}, status_code=404)
        live = route == 'ports/8080' and request.method == 'GET'
        if not live and route not in (GET_PATHS if request.method == 'GET' else POST_PATHS):
            return JSONResponse({'error': 'Unknown endpoint'}, status_code=404)
        if record['state'] != 'ready':
            return JSONResponse({'error': 'Workspace is not ready; reconnect'}, status_code=409)
        if request.headers.get('transfer-encoding'):
            return JSONResponse({'error': 'Chunked uploads are not supported'}, status_code=400)
        try:
            length = int(request.headers.get('content-length', '0'))
        except ValueError:
            length = -1
        limit = LIMIT if route == 'files' else 65536
        if length < 0 or length > limit:
            return JSONResponse({'error': 'Request too large'}, status_code=413)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return JSONResponse({'error': 'Request too large'}, status_code=413)
        try:
            endpoint = await asyncio.to_thread(runtime.endpoint, record)
        except Exception:
            return JSONResponse({'error': 'Workspace stopped; reopen IO to restart it'}, status_code=503)
        if live:
            address = urllib.parse.urlsplit(endpoint).hostname
            target = 'http://' + address + ':8080/'
            headers = {}  # Never send worker capability or Cloudflare credentials to user apps.
        else:
            target = endpoint + '/' + route
            if request.url.query:
                target += '?' + request.url.query
            headers = {'Authorization': 'Bearer ' + record['token'],
                       'Content-Type': request.headers.get('content-type', 'application/json')}
        client = httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=httpx.Timeout(50, read=30))
        try:
            upstream = await client.send(client.build_request(request.method, target, content=bytes(body), headers=headers), stream=True)
        except Exception:
            await client.aclose()
            return JSONResponse({'error': 'Runtime connection failed'}, status_code=502)
        if route == 'events' and upstream.status_code == 200:
            async def events():
                try:
                    iterator = upstream.aiter_bytes()
                    while True:
                        remaining = request.state.identity['expires'] - time.time()
                        if remaining <= 0 or not owned(request, workspace_id):
                            break
                        try:
                            chunk = await asyncio.wait_for(anext(iterator), timeout=remaining)
                        except (StopAsyncIteration, asyncio.TimeoutError):
                            break
                        yield chunk
                finally:
                    await upstream.aclose()
                    await client.aclose()
            return StreamingResponse(events(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})
        try:
            result = bytearray()
            async for chunk in upstream.aiter_bytes():
                result.extend(chunk)
                if len(result) > LIMIT:
                    return JSONResponse({'error': 'Runtime response too large'}, status_code=502)
            if 300 <= upstream.status_code < 400:
                return JSONResponse({'error': 'Runtime redirects are not followed'}, status_code=502)
            response_headers = {}
            content_type = upstream.headers.get('content-type', 'application/octet-stream')
            if live:
                content_type = 'application/octet-stream'
                response_headers['Content-Disposition'] = 'attachment; filename="workspace-service.html"'
            return Response(bytes(result), status_code=upstream.status_code, media_type=content_type, headers=response_headers)
        except Exception:
            return JSONResponse({'error': 'Runtime response interrupted'}, status_code=502)
        finally:
            await upstream.aclose()
            await client.aclose()

    return app


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--issuer', required=True)
    parser.add_argument('--audience', required=True)
    parser.add_argument('--state', type=pathlib.Path, default=pathlib.Path.home() / '.local/share/io-gateway/gateway.sqlite3')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--image', default='io-remote-codex:v1')
    args = parser.parse_args()
    os.umask(0o077)
    app = create_app(Store(args.state), AccessIdentity(args.issuer, args.audience), DockerRuntime(args.image))
    # Bind only loopback. Cloudflare Tunnel is the public listener; access logs could expose paths.
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, log_level='warning')


if __name__ == '__main__':
    main()
