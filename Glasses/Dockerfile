FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 network-manager \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY streamer.py receiver.py ./

CMD ["python", "streamer.py"]
