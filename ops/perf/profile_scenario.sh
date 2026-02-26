#!/usr/bin/env bash
set -euo pipefail

SCENARIO="${1:-browse_catalog}"
SCRIPT_PATH="/loadtests/k6/${SCENARIO}.js"
OUT_DIR="${2:-docs/perf}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${OUT_DIR}/${SCENARIO}_${STAMP}"

mkdir -p "${RUN_DIR}"

if ! docker-compose ps -q backend >/dev/null 2>&1; then
  echo "backend service is not running" >&2
  exit 1
fi

BACKEND_ID="$(docker-compose ps -q backend)"
POSTGRES_ID="$(docker-compose ps -q postgres)"

STATS_CSV="${RUN_DIR}/docker_stats.csv"
K6_LOG="${RUN_DIR}/k6.log"
SUMMARY_TXT="${RUN_DIR}/summary.txt"

echo "timestamp,container,cpu_perc,mem_perc,mem_usage" > "${STATS_CSV}"

collect_stats() {
  while kill -0 "${K6_PID}" >/dev/null 2>&1; do
    TS="$(date -Iseconds)"
    docker stats --no-stream --format '{{.ID}},{{.CPUPerc}},{{.MemPerc}},{{.MemUsage}}' "${BACKEND_ID}" "${POSTGRES_ID}" \
      | awk -F',' -v ts="${TS}" '{
          gsub(/%/, "", $2); gsub(/%/, "", $3);
          print ts "," $1 "," $2 "," $3 "," $4
        }' >> "${STATS_CSV}" || true
    sleep 1
  done
}

docker-compose run --rm --entrypoint sh k6 -lc "k6 run ${SCRIPT_PATH}" > "${K6_LOG}" 2>&1 &
K6_PID=$!

collect_stats &
COLLECT_PID=$!

wait "${K6_PID}" || true
wait "${COLLECT_PID}" || true

awk -F',' '
  NR>1 {
    cpu=$3+0; mem=$4+0;
    if (cpu>max_cpu) max_cpu=cpu;
    if (mem>max_mem) max_mem=mem;
  }
  END {
    printf("max_backend_or_db_cpu_perc=%.2f\nmax_backend_or_db_mem_perc=%.2f\n", max_cpu, max_mem);
  }
' "${STATS_CSV}" > "${SUMMARY_TXT}"

echo "Saved run artifacts to: ${RUN_DIR}"
echo "---"
cat "${SUMMARY_TXT}"
