FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp ./webapp

EXPOSE 8000

# $PORT is provided by most hosts (Render, Railway, Cloud Run); default to 8000.
CMD ["sh", "-c", "uvicorn webapp.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
