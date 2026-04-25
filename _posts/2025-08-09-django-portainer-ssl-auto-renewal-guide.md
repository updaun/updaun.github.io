---
layout: post
title: "Django + Nginx + Certbot SSL 자동 갱신 - Portainer 배포 완벽 가이드"
date: 2025-08-09 14:00:00 +0900
categories: [Django, DevOps, Docker]
tags: [Django, Nginx, Certbot, SSL, Portainer, Docker, HTTPS, Let's Encrypt, 자동화, 배포]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-08-09-django-portainer-ssl-auto-renewal-guide.webp"
---

Django 백엔드 서비스를 Portainer로 배포할 때 SSL 인증서 자동 갱신은 필수적인 운영 요소입니다. 이 글에서는 Django + Nginx + Certbot 조합으로 HTTPS를 설정하고 Let's Encrypt SSL 인증서를 자동으로 갱신하는 완전한 배포 프로세스를 다룹니다.

## 🏗️ 아키텍처 개요

### 전체 구조
```
[Client] → [Nginx Reverse Proxy] → [Django Application]
            ↓
        [Certbot SSL 갱신]
```

### 핵심 구성 요소
- **Django**: 백엔드 API 서버
- **Nginx**: 리버스 프록시 & SSL 터미네이션
- **Certbot**: Let's Encrypt SSL 인증서 자동 갱신
- **Portainer**: 컨테이너 오케스트레이션 관리

## 📁 프로젝트 구조

```
django-ssl-deployment/
├── docker-compose.yml
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ssl.conf
├── django/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── myproject/
└── certbot/
    └── certbot-auto-renew.sh
```

## 🐳 Docker 컨테이너 설정

### 1. Django 컨테이너 설정

**django/Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Django 프로젝트 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Gunicorn으로 Django 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
```

**django/requirements.txt**
```
Django==4.2.7
gunicorn==21.2.0
psycopg2-binary==2.9.8
django-cors-headers==4.3.1
python-decouple==3.8
```

### 2. Nginx 컨테이너 설정

**nginx/Dockerfile**
```dockerfile
FROM nginx:alpine

# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/nginx.conf
COPY ssl.conf /etc/nginx/conf.d/ssl.conf

# SSL 디렉토리 생성
RUN mkdir -p /etc/nginx/ssl

# 로그 디렉토리 권한 설정
RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx

EXPOSE 80 443
```

**nginx/nginx.conf**
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 로그 형식 설정
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 기본 설정
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/xml+rss
        application/javascript
        application/json;

    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    # 설정 파일 포함
    include /etc/nginx/conf.d/*.conf;
}
```

**nginx/ssl.conf**
```nginx
# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Let's Encrypt 인증 경로
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 모든 요청을 HTTPS로 리다이렉트
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 서버 설정
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL 인증서 설정
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Django 애플리케이션으로 프록시
    location / {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 정적 파일 서빙
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

## 🔧 Docker Compose 설정

**docker-compose.yml**
```yaml
version: '3.8'

services:
  django:
    build: ./django
    container_name: django-app
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DEBUG=False
      - ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
      - DATABASE_URL=postgresql://user:password@db:5432/myproject
    depends_on:
      - db
    networks:
      - app-network
    restart: unless-stopped

  nginx:
    build: ./nginx
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/var/www/static:ro
      - media_volume:/var/www/media:ro
      - certbot_data:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - django
    networks:
      - app-network
    restart: unless-stopped

  certbot:
    image: certbot/certbot:latest
    container_name: certbot-renewal
    volumes:
      - certbot_data:/etc/letsencrypt
      - certbot_www:/var/www/certbot
      - ./certbot:/scripts
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew --quiet --webroot --webroot-path=/var/www/certbot --post-hook \"nginx -s reload\"; sleep 12h & wait $${!}; done;'"
    networks:
      - app-network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    container_name: postgres-db
    environment:
      - POSTGRES_DB=myproject
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network
    restart: unless-stopped

volumes:
  static_volume:
  media_volume:
  certbot_data:
  certbot_www:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## 🔐 SSL 인증서 초기 설정

### 1. 초기 인증서 발급 스크립트

**certbot/init-letsencrypt.sh**
```bash
#!/bin/bash

domains=(yourdomain.com www.yourdomain.com)
rsa_key_size=4096
data_path="./certbot_data"
email="admin@yourdomain.com" # SSL 인증서 만료 알림 이메일

if [ -d "$data_path" ]; then
  read -p "기존 데이터가 발견되었습니다. 계속하시겠습니까? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi

if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "### Creating dummy certificate for $domains ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker-compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo

echo "### Starting nginx ..."
docker-compose up --force-recreate -d nginx
echo

echo "### Deleting dummy certificate for $domains ..."
docker-compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot
echo

echo "### Requesting Let's Encrypt certificate for $domains ..."
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

docker-compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot
echo

echo "### Reloading nginx ..."
docker-compose exec nginx nginx -s reload
```

### 2. 자동 갱신 설정

**certbot/certbot-auto-renew.sh**
```bash
#!/bin/bash

# SSL 인증서 자동 갱신 스크립트
echo "$(date): Starting SSL certificate renewal check..."

# Certbot으로 인증서 갱신 시도
docker-compose exec certbot certbot renew --quiet --webroot --webroot-path=/var/www/certbot

# 갱신 성공 시 Nginx 리로드
if [ $? -eq 0 ]; then
    echo "$(date): Certificate renewal successful. Reloading Nginx..."
    docker-compose exec nginx nginx -s reload
    echo "$(date): Nginx reloaded successfully."
else
    echo "$(date): Certificate renewal failed or no renewal needed."
fi
```

## 🚀 Portainer에서 배포하기

### 1. Portainer Stack 설정

1. **Portainer 웹 인터페이스 접속**
2. **Stacks** 메뉴로 이동
3. **Add stack** 클릭
4. **Name**: `django-ssl-app`
5. **Build method**: `Repository`
6. **Repository URL**: 프로젝트 Git 저장소 URL
7. **Compose path**: `docker-compose.yml`

### 2. 환경 변수 설정

```yaml
# Portainer Stack 환경 변수
DJANGO_SECRET_KEY=your-super-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@db:5432/myproject
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. 볼륨 매핑 설정

```yaml
# 영구 데이터 보존을 위한 볼륨 설정
volumes:
  - /opt/django-app/static:/app/staticfiles
  - /opt/django-app/media:/app/media
  - /opt/django-app/ssl:/etc/letsencrypt
  - /opt/django-app/logs:/var/log/nginx
```

## 🔄 SSL 자동 갱신 프로세스

### 1. Cron Job 설정

```bash
# 서버에 crontab 설정
crontab -e

# 매일 오전 2시에 SSL 인증서 갱신 확인
0 2 * * * /opt/django-app/certbot/certbot-auto-renew.sh >> /var/log/ssl-renewal.log 2>&1
```

### 2. 갱신 로그 모니터링

**로그 확인 스크립트**
```bash
#!/bin/bash

echo "=== SSL Certificate Status ==="
docker-compose exec certbot certbot certificates

echo "=== Recent Renewal Logs ==="
tail -n 50 /var/log/ssl-renewal.log

echo "=== Certificate Expiry Check ==="
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

## 📊 모니터링 및 알림

### 1. SSL 만료 알림 설정

**ssl-monitor.py**
```python
import ssl
import socket
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def check_ssl_expiry(hostname, port=443):
    """SSL 인증서 만료일 확인"""
    context = ssl.create_default_context()
    
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            expiry_date = datetime.datetime.strptime(
                cert['notAfter'], '%b %d %H:%M:%S %Y %Z'
            )
            
            days_until_expiry = (expiry_date - datetime.datetime.now()).days
            return days_until_expiry, expiry_date

def send_alert_email(days_left, expiry_date, hostname):
    """SSL 만료 알림 이메일 발송"""
    sender_email = "admin@yourdomain.com"
    sender_password = "your-app-password"
    recipient_email = "devops@yourdomain.com"
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = f"SSL Certificate Expiry Alert - {hostname}"
    
    body = f"""
    SSL Certificate for {hostname} will expire in {days_left} days.
    Expiry Date: {expiry_date}
    
    Please check the automatic renewal process.
    """
    
    message.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = message.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print(f"Alert email sent for {hostname}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    hostname = "yourdomain.com"
    
    try:
        days_left, expiry_date = check_ssl_expiry(hostname)
        print(f"SSL certificate for {hostname} expires in {days_left} days")
        
        # 30일 이내 만료 시 알림
        if days_left <= 30:
            send_alert_email(days_left, expiry_date, hostname)
            
    except Exception as e:
        print(f"Error checking SSL certificate: {e}")
```

### 2. 헬스체크 엔드포인트

**Django settings.py**
```python
# SSL 상태 확인을 위한 헬스체크 엔드포인트
# urls.py에 추가
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import ssl
import socket
from datetime import datetime

@csrf_exempt
def ssl_health_check(request):
    """SSL 인증서 상태 확인 API"""
    try:
        hostname = request.get_host().split(':')[0]
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expiry_date = datetime.strptime(
                    cert['notAfter'], '%b %d %H:%M:%S %Y %Z'
                )
                
                days_until_expiry = (expiry_date - datetime.now()).days
                
                return JsonResponse({
                    'status': 'healthy',
                    'ssl_valid': True,
                    'days_until_expiry': days_until_expiry,
                    'expiry_date': expiry_date.isoformat(),
                    'issuer': cert.get('issuer', []),
                    'subject': cert.get('subject', [])
                })
                
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'ssl_valid': False,
            'error': str(e)
        }, status=500)
```

## 🚨 트러블슈팅

### 1. 일반적인 문제와 해결방법

**SSL 인증서 발급 실패**
```bash
# 도메인 소유권 확인
dig yourdomain.com

# Let's Encrypt 레이트 리밋 확인
curl -s "https://letsencrypt.org/docs/rate-limits/"

# Certbot 로그 확인
docker-compose logs certbot
```

**Nginx 설정 오류**
```bash
# Nginx 설정 문법 검사
docker-compose exec nginx nginx -t

# Nginx 로그 확인
docker-compose logs nginx
tail -f ./nginx/logs/error.log
```

**자동 갱신 실패**
```bash
# Certbot 수동 갱신 테스트
docker-compose exec certbot certbot renew --dry-run

# 파일 권한 확인
ls -la /etc/letsencrypt/live/yourdomain.com/
```

### 2. 성능 최적화

**Nginx 캐싱 설정**
```nginx
# nginx/ssl.conf에 추가
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# Gzip 압축 강화
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    gzip_static on;
    expires max;
    add_header Cache-Control public;
}
```

## 📈 모니터링 대시보드

### Prometheus + Grafana 통합

**docker-compose.monitoring.yml**
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    networks:
      - monitoring

  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:latest
    container_name: nginx-exporter
    ports:
      - "9113:9113"
    command:
      - '-nginx.scrape-uri=http://nginx:80/nginx_status'
    depends_on:
      - nginx
    networks:
      - app-network
      - monitoring

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

## 🎯 결론

Django + Nginx + Certbot 조합으로 Portainer에서 SSL 자동 갱신을 구현하는 것은 다음과 같은 장점을 제공합니다:

### ✅ 주요 이점
- **자동화된 SSL 관리**: Let's Encrypt 인증서 자동 갱신
- **제로 다운타임**: 무중단 SSL 인증서 교체
- **보안 강화**: 최신 SSL/TLS 프로토콜 적용
- **모니터링**: 실시간 SSL 상태 추적
- **확장성**: 멀티 도메인 SSL 지원

### 🔧 운영 체크리스트
1. **일일 점검**: SSL 인증서 만료일 확인
2. **주간 점검**: 자동 갱신 로그 검토
3. **월간 점검**: 보안 설정 업데이트
4. **분기별 점검**: 전체 시스템 보안 감사

이제 Django 백엔드 서비스를 안전하고 신뢰할 수 있는 HTTPS 환경에서 운영할 수 있습니다. SSL 인증서 관리에 대한 걱정 없이 개발과 비즈니스 로직에 집중하세요!

---

**참고 자료**
- [Let's Encrypt 공식 문서](https://letsencrypt.org/docs/)
- [Nginx SSL 설정 가이드](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Django 보안 설정](https://docs.djangoproject.com/en/stable/topics/security/)
- [Portainer 공식 문서](https://docs.portainer.io/)
