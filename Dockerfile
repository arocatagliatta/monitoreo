FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    mbpoll \
    && apt-get clean

WORKDIR /app

COPY modbus_export.py /app/modbus_export.py

CMD ["sh", "-c", "while true; do python3 /app/modbus_export.py; sleep 15; done"]
