FROM python:3.11-slim

WORKDIR /app

# Шаардлагатай сангуудыг суулгах
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SQLite өгөгдлийн сан байрлах хавтасыг бэлдэж эрх өгөх
RUN mkdir -p /app/sqlite_db && chmod 777 /app/sqlite_db

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn gotopa_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 90 --max-requests 300 --max-requests-jitter 30"]