FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python3 -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL ducklake')"

COPY . .

ENV DATABASE_URL=postgresql://postgres:password@worthy-continually-diaphragm:5432/butik

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
