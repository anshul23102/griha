#!/usr/bin/env bash
# Starts the whole Griha stack: Temporal, Prometheus, Grafana, API (with the Temporal worker) and the web app.
# Everything is local and free. Stop with ops/stop.sh.
set -u
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
D="$PWD/.data"
mkdir -p "$D/logs" "$D/pids" "$D/prometheus" "$D/grafana"
run() { name=$1; shift; if [ -f "$D/pids/$name" ] && kill -0 "$(cat "$D/pids/$name")" 2>/dev/null; then echo "$name already running"; return; fi
  nohup "$@" > "$D/logs/$name.log" 2>&1 & echo $! > "$D/pids/$name"; echo "started $name"; }
run temporal temporal server start-dev --ip 127.0.0.1 --db-filename "$PWD/.data/temporal.db"
run prometheus prometheus --config.file="$PWD/prometheus.yml" --storage.tsdb.path="$PWD/.data/prometheus" --web.listen-address=127.0.0.1:9090
mkdir -p "$D/provisioning/datasources" "$D/provisioning/dashboards" "$D/logs/grafana"
cp "$PWD/grafana/provisioning/datasources/"*.yml "$D/provisioning/datasources/"
printf "apiVersion: 1\nproviders:\n  - name: griha\n    type: file\n    options:\n      path: %s/grafana/dashboards\n" "$PWD" > "$D/provisioning/dashboards/griha.yml"
export GF_PATHS_DATA="$D/grafana" GF_PATHS_LOGS="$D/logs/grafana" GF_PATHS_PLUGINS="$D/grafana/plugins" GF_PATHS_PROVISIONING="$D/provisioning" GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH="$PWD/grafana/dashboards/griha.json"
run grafana grafana server --homepath /opt/homebrew/opt/grafana/share/grafana --config "$PWD/grafana.ini"
sleep 4
( cd "$ROOT/backend" && run api env GRIHA_RETENTION_HOLD=${GRIHA_RETENTION_HOLD:-0} uv run uvicorn griha.api:app --port 8000 ) 
( cd "$ROOT/frontend" && run web pnpm exec vite --host 127.0.0.1 )
sleep 8
echo; echo "Web app       http://127.0.0.1:5173"; echo "Temporal UI   http://localhost:8233"; echo "Grafana       http://localhost:3000  (anonymous viewer; admin / griha-demo)"; echo "Prometheus    http://localhost:9090"
