# If there wouldn't be any detection
FROM python:3.11-slim

# If there wouldn't be any detection
COPY requirements.txt .
RUN pip install -r requirements.txt
