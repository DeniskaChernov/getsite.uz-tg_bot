FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway монтирует volume в /app/data от root, поэтому процесс должен идти от root,
# иначе sqlite3.OperationalError: unable to open database file
RUN mkdir -p /app/data

CMD ["python", "main.py"]
