FROM python:3.12-slim

WORKDIR /app
COPY scripts/experiments/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY scripts /app/scripts
COPY services /app/services
COPY tests /app/tests
COPY infra/azure/experiment-settings.json /app/infra/azure/experiment-settings.json

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m"]
