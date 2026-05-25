FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION .
COPY app/ .

RUN mkdir -p /app/config && chmod -R 777 /app/config

EXPOSE 5555

CMD ["python", "-u", "app.py"]

LABEL org.opencontainers.image.source="https://github.com/DmesgNoise/cloudflare-ddns"
