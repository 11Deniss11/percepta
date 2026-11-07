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
    colcon-common-extensions

WORKDIR /workspace

# The devcontainer publishes this UDP port to the laptop's network interfaces.
EXPOSE 5000/udp

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

CMD ["bash"]