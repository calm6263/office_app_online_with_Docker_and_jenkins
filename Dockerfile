# ======================================================
# المرحلة الأولى: بناء التبعيات
# ======================================================
FROM python:3.10-slim-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN sed -i 's/main$/main non-free/' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    libfreetype6-dev \
    pkg-config \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ======================================================
# المرحلة الثانية: صورة الإنتاج
# ======================================================
FROM python:3.10-slim-bullseye AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    FLASK_ENV=production \
    FLASK_DEBUG=0

RUN sed -i 's/main$/main non-free/' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libfreetype6 \
    libpng16-16 \
    libjpeg62-turbo \
    fonts-freefont-ttf \
    fonts-dejavu \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مستخدم غير root للأمان
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# نسخ الحزم المثبتة من مرحلة البناء
COPY --from=builder /install /usr/local

# نسخ الكود
COPY --chown=appuser:appgroup . .

# إنشاء المجلدات الضرورية بأذونات صحيحة
RUN mkdir -p \
    static/transaction_files \
    static/reports \
    static/fonts \
    database_backups \
    && chown -R appuser:appgroup \
    static/transaction_files \
    static/reports \
    static/fonts \
    database_backups \
    && chmod -R 750 static/transaction_files static/reports database_backups

# التبديل إلى المستخدم غير root
USER appuser

EXPOSE 5000

# نقطة دخول Gunicorn
ENTRYPOINT ["gunicorn"]
CMD ["--config", "gunicorn.conf.py", "wsgi:application"]
