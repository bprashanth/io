#!/bin/sh
# held-out run: code frozen; Muse 30B (today's product) vs Careful vs Auto, dev scripts and held-out scripts
cd "$(dirname "$0")"
mkdir -p logs/holdout
DEV="yerawada debt state falsepush nodata panels"
HOLD="h_struggle h_modify h_share h_causal f_money f_time"
for m in muse-glimmer-30b idli-9b-careful idli-9b-auto; do
  ./run.sh $m $HOLD > logs/holdout/$m-holdout.log 2>&1
done
./run.sh muse-glimmer-30b $DEV > logs/holdout/muse-glimmer-30b-dev.log 2>&1
echo done
