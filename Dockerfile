FROM python:3.11-slim

WORKDIR /app

# Шаардлагатай сангуудыг суулгах
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SQLite өгөгдлийн сан байрлах хавтасыг бэлдэж эрх өгөх
RUN mkdir -p /app/sqlite_db && chmod 777 /app/sqlite_db

COPY . .

EXPOSE 8000

CMD ["gunicorn", "gotopa_project.wsgi:application", "--bind", "0.0.0.0:8000"]