#!/bin/sh
# DGX side: the Paseo CLI, pointed at the LAPTOP's daemon through the tunnel.
# The DGX host has no Node; the CLI comes from the io-oss-paseo image (same 0.15.2 as the laptop app).
# Always pass --workspace or --cwd with laptop paths: the container's own cwd means nothing to the laptop.
#   paseo-remote.sh ls
#   paseo-remote.sh run --provider t4gc-cowork --workspace <wks_id> --mode bypassPermissions "question"
exec docker run --rm -i --network host --entrypoint paseo io-oss-paseo:0.15.2 \
  --host "${PASEO_REMOTE:-127.0.0.1:46767}" "$@"
