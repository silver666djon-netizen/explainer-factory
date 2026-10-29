#!/usr/bin/env bash
# The whole regression list (docs/REGRESSION_CHECKS.md) before every release. Any failure -> exit 1 (release blocked).
#   tools/qc/run_regression.sh episodes/<slug> <dir with timings.json, qc_checks.json and the rendered .mp4 files>
set -u
EP_DIR="$1"; REL="$2"; TJ="$REL/timings.json"
export EP="$EP_DIR" OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-audit-offline}"
cd "$(dirname "$0")/../.."
fail=0; res=()
run() { local name="$1"; shift; if "$@" > "$REL/qc_$name.log" 2>&1; then res+=("| $name | PASS |"); else res+=("| $name | FAIL (see qc_$name.log) |"); fail=1; fi; }
run mark_audit python3 tools/qc/mark_audit.py "$EP_DIR" "$TJ" --shorts
run handcheck_long python3 tools/qc/handcheck.py "$TJ" long --no-frames
run handcheck_shorts python3 tools/qc/handcheck.py "$TJ" shorts --no-frames
run release_checks python3 tools/qc/release_checks.py "$EP_DIR" "$TJ" --out "$REL/qc_release_local.md" --skip voice_cut_check
if [ -s "$REL/qc_checks.json" ]; then  # the CI build's checks on the real narration (voice_cut_check lives there)
  run ci_checks python3 -c "import json,sys; r=json.load(open('$REL/qc_checks.json')); sys.exit(any(c['fails'] for v in r.values() for c in v.values()))"
else res+=("| ci_checks | FAIL (no qc_checks.json in the release) |"); fail=1; fi
if python3 -c "import json,sys; sys.exit(1 if json.load(open('$TJ')).get('max_still_warnings') else 0)"; then res+=("| max_still | PASS |"); else res+=("| max_still | FAIL |"); fail=1; fi
for f in "$REL"/*.mp4; do
  b=$(basename "$f" .mp4)
  run "static_$b" python3 tools/qc/static_scan.py "$f" "$TJ"
  run "decode_$b" bash -c "ffmpeg -v error -i '$f' -f null - 2>&1 | (! grep -q .)"
done
run audio_gate python3 tools/qc/audio_gate.py "$REL"/*.mp4
printf '| check | result |\n|---|---|\n'; printf '%s\n' "${res[@]}"
exit $fail
