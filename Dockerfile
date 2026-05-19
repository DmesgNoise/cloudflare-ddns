FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

ENV CF_API_TOKEN=""
ENV CF_ZONE_ID=""
ENV RECORD_NAME=""
ENV CF_PROXIED="true"

EXPOSE 5555

CMD ["python", "app.py"]
