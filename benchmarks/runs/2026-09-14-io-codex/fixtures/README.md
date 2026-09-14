# fixtures

`auth-fixture.json` is a *fake* Codex credential: a JWT-shaped id_token signed by nobody,
placeholder access/refresh tokens. It exists so the io UI's "signed in" path can be driven
on a machine where the real ChatGPT OAuth cannot be completed (no display, no account B).
Any real server rejects it with 401 (see spike1-out). It is never a substitute for the
user's own login and never touches ~/.codex.
