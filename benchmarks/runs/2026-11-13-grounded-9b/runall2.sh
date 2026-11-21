#!/bin/sh
# round 2 (after the fixes): the two new modes on every script, then the renderer fault
cd "$(dirname "$0")"
for m in idli-9b-careful idli-9b-auto; do
  ./run.sh $m yerawada debt state falsepush nodata panels > logs/$m.log 2>&1
  IDLI_FAULT=drop_series ./run.sh $m panels --fault > logs/$m-fault.log 2>&1
done
echo done
