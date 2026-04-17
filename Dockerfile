FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Förinstallera ducklake-tillägget så containern inte behöver nätverket vid start
RUN python3 -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL ducklake')"

COPY . .

ENV CATALOG_PATH=/app/data/katalog.duckdb
ENV DATA_PATH=/app/data/lake/

RUN mkdir -p /app/data/lake && python seed.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
