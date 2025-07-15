# Dockerfile
FROM python:3.10-slim-bullseye

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive
RUN sed -i 's/main/main non-free/' /etc/apt/sources.list

# تثبيت حزم النظام المطلوبة
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    libfreetype6-dev \
    pkg-config \
    libpng-dev \
    libjpeg-dev \
    fonts-freefont-ttf \
    fonts-dejavu \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد التطبيق
WORKDIR /app

# نسخ متطلبات التطبيق
COPY requirements.txt .

# تثبيت الاعتمادات البايثونية
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ ملفات التطبيق
COPY . .

# إنشاء المجلدات الضرورية
RUN mkdir -p \
    static/transaction_files \
    static/reports \
    static/fonts \
    database_backups

# تعيين أذونات للمجلدات
RUN chmod -R 755 static database_backups

# فتح المنفذ
EXPOSE 5000

# أمر التشغيل
CMD ["python", "app.py"]