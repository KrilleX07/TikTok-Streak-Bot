FROM python:3.12-slim

# Install system deps required by Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Add Google's official apt repo and install Chrome stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
    http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Directory for log output (mounted as a volume in compose)
RUN mkdir -p /app/data

CMD ["python", "-u", "main.py"]
