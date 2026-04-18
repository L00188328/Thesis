FROM python:3.12-slim

ARG SERVICE_DIR

WORKDIR /app
COPY services /app/services
COPY ${SERVICE_DIR}/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "services.api.main"]
