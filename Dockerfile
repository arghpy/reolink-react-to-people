# If there wouldn't be any detection
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# If there wouldn't be any detection
COPY requirements.txt .
RUN pip install -r requirements.txt
