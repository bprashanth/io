#!/bin/sh
# all scripts, three modes, then the renderer fault (a chart that loses its second panel) for the two new modes
cd "$(dirname "$0")"
for m in idli-9b-careful idli-9b-auto idli-9b; do
  ./run.sh $m yerawada debt state falsepush nodata panels > logs/$m.log 2>&1
done
for m in idli-9b-careful idli-9b-auto; do
  IDLI_FAULT=drop_series ./run.sh $m panels --fault > logs/$m-fault.log 2>&1
done
echo done
