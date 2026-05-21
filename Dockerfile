FROM python:3.9-slim
WORKDIR /app

# Copy the requirements file and install dependencies first (better for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY app/ .

RUN mkdir -p /app/config && chmod 777 /app/config

EXPOSE 5555
CMD ["python", "-u", "app.py"]
LABEL org.opencontainers.image.source=https://github.com/DmesgNoise/cloudflare-ddns
