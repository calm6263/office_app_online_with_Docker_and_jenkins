FROM jenkins/jenkins:lts-jdk11

# تثبيت التبعيات المطلوبة
USER root
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# إضافة مفتاح Docker الرسمي
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# إضافة مستودع Docker
RUN echo \
    "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# تثبيت Docker CLI (ليس المحرك)
RUN apt-get update && apt-get install -y docker-ce-cli

# تثبيت Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose

# إصلاح مشكلة المجموعة
RUN groupadd docker || true
RUN usermod -aG docker jenkins

# تثبيت خطوط DejaVu للدعم متعدد اللغات
RUN apt-get install -y fonts-dejavu

# العودة إلى المستخدم jenkins لتجنب المشاكل الأمنية
USER jenkins