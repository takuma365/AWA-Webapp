# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Pythonパスにカレントディレクトリを追加
ENV PYTHONPATH="${PYTHONPATH}:/app"

CMD ["python", "app/manage.py", "runserver", "0.0.0.0:8000"]