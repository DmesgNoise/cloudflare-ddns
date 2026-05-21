FROM python:3.9-slim
WORKDIR /app

# Copy dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory content into /app/
COPY app/ .

# Create the config directory and set open permissions for volume mounting
RUN mkdir -p /app/config && chmod -R 777 /app/config

EXPOSE 5555

# -u flag ensures python logs are sent straight to terminal (Docker logs)
CMD ["python", "-u", "app.py"]

LABEL org.opencontainers.image.source="https://github.com/DmesgNoise/cloudflare-ddns"
