FROM python:3.9-slim
WORKDIR /app
COPY app/ . 
RUN mkdir -p /app/config && chmod 777 /app/config
RUN pip install --no-cache-dir flask requests
EXPOSE 5555
CMD ["python", "-u", "app.py"]
LABEL org.opencontainers.image.source=https://github.com/DmesgNoise/cloudflare-ddns
