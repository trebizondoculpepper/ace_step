#!/usr/bin/env bash
# Run one ACE-Step cover (remix) job for a work/ project, with ETA + elapsed-time feedback.
#
#   work/bin/remix.sh <project> <label> <cover_strength> <batch> "<caption>" [source.wav]
#
# - source defaults to work/projects/<project>/source/trimmed.wav
# - duration is taken from the source file (ffprobe)
# - outputs land in work/projects/<project>/renders/<label>_<n>.wav (+ <label>.json metadata)
# - every run appends to work/logs/timings.csv, which feeds the next run's estimate
set -euo pipefail

[ $# -ge 5 ] || { sed -n 2,9p "$0"; exit 2; }
PROJECT=$1 LABEL=$2 STRENGTH=$3 BATCH=$4 CAPTION=$5
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$REPO/work"; PDIR="$WORK/projects/$PROJECT"
SRC_REL="${6:-work/projects/$PROJECT/source/trimmed.wav}"   # API only accepts repo-relative paths
TIMINGS="$WORK/logs/timings.csv"
SKILL="$REPO/.claude/skills/acestep/scripts/acestep.sh"
RUNLOG="$PDIR/logs/$LABEL.log"

cd "$REPO"
[ -f "$SRC_REL" ] || { echo "Source not found: $SRC_REL"; exit 1; }
curl -sf http://127.0.0.1:8001/health | grep -q '"models_initialized":true' \
  || { echo "Server not ready. Run: work/bin/server.sh start"; exit 1; }
mkdir -p "$PDIR/renders" "$PDIR/logs"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC_REL" | cut -d. -f1)
WORKLOAD=$(( DUR * BATCH ))   # audio-seconds generated

# Estimate: average seconds per generated audio-second over past cover runs.
EST=$(awk -F, -v w="$WORKLOAD" 'NR>1 && $4=="cover" && $5*$6>0 {r+=$7/($5*$6); n++}
  END { if (n) printf "%d %d", r/n*w, n }' "$TIMINGS" 2>/dev/null || true)
if [ -n "$EST" ]; then
  set -- $EST
  printf "Estimate: ~%dm%02ds for %ss x %s takes (based on %s past runs)\n" $(($1/60)) $(($1%60)) "$DUR" "$BATCH" "$2"
else
  echo "Estimate: no timing history yet; this run will calibrate future estimates."
fi

start=$(date +%s)
( while sleep 30; do printf "  ...%ss elapsed\n" $(( $(date +%s) - start )); done ) &
TICKER=$!; trap 'kill $TICKER 2>/dev/null' EXIT

set +e
bash "$SKILL" cover "$SRC_REL" -c "$CAPTION" -l "[Instrumental]" \
  --cover-strength "$STRENGTH" --duration "$DUR" --batch "$BATCH" > "$RUNLOG" 2>&1
rc=$?
set -e
elapsed=$(( $(date +%s) - start ))

JOB=$(grep -o 'Job created: [0-9a-f-]*' "$RUNLOG" | awk '{print $3}' || true)
if [ $rc -ne 0 ] || [ -z "$JOB" ]; then
  echo "FAILED after ${elapsed}s (rc=$rc). Log: $RUNLOG"; tr '\r' '\n' < "$RUNLOG" | tail -5; exit 1
fi
n=0
for f in "$REPO"/acestep_output/"$JOB"_*.*; do
  [ -e "$f" ] || continue; n=$((n+1)); mv "$f" "$PDIR/renders/${LABEL}_$n.${f##*.}"
done
[ -f "$REPO/acestep_output/$JOB.json" ] && mv "$REPO/acestep_output/$JOB.json" "$PDIR/renders/$LABEL.json"

echo "$(date -u +%FT%TZ),$PROJECT,$LABEL,cover,$DUR,$BATCH,$elapsed" >> "$TIMINGS"
printf "Done in %dm%02ds: %s files -> %s/renders/%s_*\n" $((elapsed/60)) $((elapsed%60)) "$n" "$PDIR" "$LABEL"
