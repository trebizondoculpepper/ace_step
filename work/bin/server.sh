#!/usr/bin/env bash
# Start / stop / check the local ACE-Step API server used by work/ projects.
#   work/bin/server.sh start   # background start, waits until models are loaded, prints load time
#   work/bin/server.sh status
#   work/bin/server.sh stop
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$REPO/work"
LOG="$WORK/logs/server.log"
PIDFILE="$WORK/logs/server.pid"
TIMINGS="$WORK/logs/timings.csv"
URL="http://127.0.0.1:8001"
LM_MODEL="${LM_MODEL:-acestep-5Hz-lm-1.7B}"   # installed locally; 4B is NOT (multi-GB download)

health() { curl -sf "$URL/health" 2>/dev/null || true; }

case "${1:-status}" in
  start)
    if [ -n "$(health)" ]; then echo "Already running: $(health)"; exit 0; fi
    mkdir -p "$WORK/logs"
    [ -f "$TIMINGS" ] || echo "timestamp,project,label,task,duration_s,batch,elapsed_s" > "$TIMINGS"
    cd "$REPO"
    export ACESTEP_LM_BACKEND=mlx TOKENIZERS_PARALLELISM=false ACESTEP_INIT_LLM=true
    export ACESTEP_NO_INIT=false        # load models at startup so readiness == ready to generate
    export HF_HUB_OFFLINE=1             # never silently download models
    start=$(date +%s)
    nohup uv run --offline acestep-api --host 127.0.0.1 --port 8001 \
      --lm-model-path "$LM_MODEL" > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Starting server (LM=$LM_MODEL), log: $LOG"
    while :; do
      h=$(health)
      if echo "$h" | grep -q '"models_initialized":true'; then break; fi
      if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Server died during startup. Last log lines:"; tail -20 "$LOG"; exit 1
      fi
      sleep 5; printf "  ...loading models, %ss elapsed\n" $(( $(date +%s) - start ))
    done
    elapsed=$(( $(date +%s) - start ))
    echo "$(date -u +%FT%TZ),-,server-start,load,0,0,$elapsed" >> "$TIMINGS"
    echo "Ready in ${elapsed}s: $(health)"
    ;;
  status)
    h=$(health); [ -n "$h" ] && echo "$h" || echo "Not running";;
  stop)
    pkill -f "acestep-api --host 127.0.0.1 --port 8001" && echo "Stopped" || echo "Not running"
    rm -f "$PIDFILE";;
  *) echo "usage: $0 start|status|stop"; exit 2;;
esac
