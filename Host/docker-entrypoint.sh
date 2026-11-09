#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

workspace=/workspace
cd "$workspace"
if [ ! -f "$workspace/install/setup.bash" ] ||
   [ ! -f "$workspace/install/percepta_host/share/percepta_host/launch/host_nodes.launch.py" ]; then
    colcon build --base-paths "$workspace/src"
fi

source "$workspace/install/setup.bash"

ollama_url=http://127.0.0.1:11434/
ollama_log=/tmp/ollama.log
ollama_startup_timeout=${OLLAMA_STARTUP_TIMEOUT:-120}

if ! curl -fsS "$ollama_url" >/dev/null 2>&1; then
    : > "$ollama_log"
    ollama serve >"$ollama_log" 2>&1 &
    ollama_pid=$!

    for ((elapsed=0; elapsed<ollama_startup_timeout; elapsed++)); do
        if curl -fsS "$ollama_url" >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "$ollama_pid" 2>/dev/null; then
            echo "Ollama exited before becoming ready. Log:" >&2
            cat "$ollama_log" >&2
            exit 1
        fi
        sleep 1
    done
fi

if ! curl -fsS "$ollama_url" >/dev/null 2>&1; then
    echo "Ollama did not become ready after ${ollama_startup_timeout}s. Log:" >&2
    cat "$ollama_log" >&2
    exit 1
fi

exec ros2 launch percepta_host host_nodes.launch.py
