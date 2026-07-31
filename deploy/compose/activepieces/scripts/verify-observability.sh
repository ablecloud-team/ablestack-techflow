#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"
set -a
source .env
set +a

python3 -m unittest -v observability/test_observer.py
python3 observability/observer.py collect --strict
python3 observability/observer.py status
test "$(stat -c '%a' /var/lib/ablestack-techflow/observability/status.json)" = "640"
test "$(stat -c '%a' /var/lib/ablestack-techflow/observability/metrics.prom)" = "640"
test "$(stat -c '%a' /var/lib/ablestack-techflow/observability/current-alerts.json)" = "640"
grep -q '^techflow_observer_up 1$' /var/lib/ablestack-techflow/observability/metrics.prom
grep -q '^techflow_service_healthy{service="app"} 1$' /var/lib/ablestack-techflow/observability/metrics.prom
systemctl is-enabled techflow-observer.timer
systemctl is-active techflow-observer.timer
docker compose --env-file .env config >/dev/null
scripts/healthcheck.sh --wait 120

scan_target=$(mktemp -d)
trap 'rm -rf -- "${scan_target}"' EXIT
cp -a /var/lib/ablestack-techflow/observability "${scan_target}/state"
if [[ -d /var/log/ablestack-techflow/observability ]]; then
  cp -a /var/log/ablestack-techflow/observability "${scan_target}/log"
fi
python3 scripts/secret_scan.py --env-file .env --scan-root "${scan_target}"

echo "observability=verified timer=active collector=ready alerts=0 secret_scan=passed"
