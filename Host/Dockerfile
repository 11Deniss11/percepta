FROM osrf/ros:jazzy-desktop

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-opencv \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into the system interpreter. Keep Debian's
# pip package; upgrading it attempts to uninstall a package without a RECORD.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "numpy<2" "setuptools<81" ultralytics \
    "clip @ git+https://github.com/ultralytics/CLIP.git" \
    colcon-common-extensions \
    SpeechRecognition \
    soundfile \
    openai-whisper \
    ollama

# THIS SECTION BELOW IS FOR INSTALLING THE QWEN MODEL AND RELATED DEPENDANCIES

# Install dependencies required by the Ollama installer
RUN apt-get update && apt-get install -y curl zstd && rm -rf /var/lib/apt/lists/*

# Install the Ollama daemon
RUN curl -fsSL https://ollama.com/install.sh | sh

# TTS stuff
RUN pip install piper-tts

# Start the server temporarily in the background to pull the model into the image layers
# Increased sleep to 10 seconds to ensure daemon is fully listening before pulling
RUN nohup bash -c "ollama serve &" && sleep 10 && ollama pull qwen3.5:2b

# END OF QWEN-RELATED SECTION

WORKDIR /workspace

# The devcontainer publishes this UDP port to the laptop's network interfaces.
EXPOSE 5000/udp
EXPOSE 5005/udp
EXPOSE 11434/tcp

# Automatically source ROS2 and start Ollama in the background when a terminal opens
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
    echo 'if ! curl -s http://localhost:11434/ > /dev/null; then ollama serve > /dev/null 2>&1 & sleep 2; fi' >> ~/.bashrc

CMD ["bash"]