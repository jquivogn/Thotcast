#!/usr/bin/env bash
# Thotcast daily trigger — call from cron to generate a new episode automatically.
#
# Install (generates an episode every day at 07:00):
#   crontab -e
#   0 7 * * * /home/user/Thotcast/cron_trigger.sh >> /home/user/Thotcast/cron.log 2>&1

set -euo pipefail

THOTCAST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${THOTCAST_API_URL:-http://localhost:8000}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Triggering Thotcast generation..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_URL}/generate" \
    -H "Content-Type: application/json")

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Generation started (HTTP $HTTP_CODE)"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: API returned HTTP $HTTP_CODE" >&2
    exit 1
fi
