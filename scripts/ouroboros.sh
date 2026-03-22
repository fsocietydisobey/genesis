#!/usr/bin/env bash
# Chayah (Ouroboros) — outer daemon for the evolution loop.
# Restarts the agent on exit code 42 (self-modification detected).

set -e

echo "Chayah: starting evolution loop..."

while true; do
    uv run ai-orchestrator-graph "$@"
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Chayah: clean shutdown."
        break
    fi

    if [ $EXIT_CODE -eq 42 ]; then
        echo "Chayah: self-modification detected. Restarting with new code..."
        sleep 1
        continue
    fi

    echo "Chayah: unexpected exit ($EXIT_CODE). Stopping."
    break
done
