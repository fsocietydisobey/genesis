#!/usr/bin/env bash
# Ein Sof (MUTHER) — outer daemon for the meta-orchestrator.
# Restarts on exit code 42 (self-modification). Stops on clean exit or error.

set -e

echo "Ein Sof: awakening..."

while true; do
    uv run ai-orchestrator-graph "$@"
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Ein Sof: entering cryosleep. All is well."
        break
    fi

    if [ $EXIT_CODE -eq 42 ]; then
        echo "Ein Sof: self-modification detected. Rebirth in progress..."
        sleep 1
        continue
    fi

    echo "Ein Sof: unexpected exit ($EXIT_CODE). Stopping."
    break
done
