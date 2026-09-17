# Готопа бясалгалын төв - Django Application
FROM python:3.13-slim

# Системийн орчин тохируулах
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=gotopa_project.settings

WORKDIR /app

# Системийн хамаарлууд суулгах (Pillow-д хэрэгтэй)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python хамаарлууд суулгах
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir django-ckeditor gunicorn

# Апп-ын кодыг хуулах
COPY . .

# entrypoint скрипт ажиллах эрх олгох
RUN chmod +x /app/entrypoint.sh

# Media болон staticfiles директор үүсгэх
RUN mkdir -p /app/media /app/staticfiles

# Static файлуудыг цуглуулах
RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
