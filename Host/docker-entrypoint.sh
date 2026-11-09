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

if ! curl -fsS http://localhost:11434/ >/dev/null 2>&1; then
    ollama serve >/tmp/ollama.log 2>&1 &
    for _ in {1..30}; do
        if curl -fsS http://localhost:11434/ >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

if ! curl -fsS http://localhost:11434/ >/dev/null 2>&1; then
    echo "Ollama did not become ready" >&2
    exit 1
fi

exec ros2 launch percepta_host host_nodes.launch.py
