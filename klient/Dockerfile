FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY klient.py .

ENV DATALAKE_URL=https://misty-abnormally-educated.app.cloud.cbh.kth.se

EXPOSE 8001

CMD ["uvicorn", "klient:app", "--host", "0.0.0.0", "--port", "8001"]
