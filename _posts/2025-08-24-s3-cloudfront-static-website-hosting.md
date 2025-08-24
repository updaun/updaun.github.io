---
layout: post
title: "AWS S3와 CloudFront를 활용한 정적 웹사이트 호스팅 완전 가이드"
categories: [aws-saa, web-development]
tags: [aws, s3, cloudfront, static-hosting, cdn, web-performance]
date: 2025-08-24
---

## 📋 개요

정적 웹사이트 호스팅은 현대 웹 개발에서 매우 중요한 배포 방식입니다. 이번 포스트에서는 AWS S3와 CloudFront를 활용하여 고성능, 고가용성의 정적 웹사이트를 구축하는 방법을 단계별로 알아보겠습니다.

### 왜 정적 웹사이트인가?

정적 웹사이트의 장점:
- **빠른 로딩 속도**: 서버 사이드 처리가 없어 응답 속도가 빠름
- **높은 보안성**: 서버 사이드 취약점이 없음
- **저렴한 비용**: 서버 인프라 비용 절약
- **높은 확장성**: CDN을 통한 글로벌 배포
- **간단한 배포**: 파일 업로드만으로 배포 완료

## 🏗️ 아키텍처 설계

### 전체 구성도

```
[사용자] → [Route 53] → [CloudFront CDN] → [S3 Static Website]
                             ↓
[WAF] ← [Lambda@Edge] ← [Origin Access Control]
```

### 주요 구성 요소

1. **Amazon S3**: 정적 파일 저장소 및 웹 호스팅
2. **Amazon CloudFront**: 글로벌 CDN 서비스
3. **Route 53**: DNS 관리 (선택사항)
4. **AWS WAF**: 웹 애플리케이션 방화벽 (선택사항)
5. **Lambda@Edge**: 엣지 컴퓨팅 (선택사항)

## 🚀 실습 가이드

### 1단계: S3 버킷 생성 및 설정

#### A. S3 버킷 생성

```bash
# AWS CLI를 사용한 버킷 생성
aws s3 mb s3://my-static-website-bucket-unique-name --region ap-northeast-2
```

#### B. 정적 웹사이트 호스팅 활성화

```bash
# 정적 웹사이트 설정
aws s3 website s3://my-static-website-bucket-unique-name \
    --index-document index.html \
    --error-document error.html
```

#### C. 버킷 정책 설정

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-static-website-bucket-unique-name/*"
        }
    ]
}
```

### 2단계: 샘플 정적 웹사이트 생성

#### A. HTML 파일 생성

**index.html**
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS S3 + CloudFront 정적 웹사이트</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <nav class="navbar">
            <div class="nav-container">
                <h1 class="nav-logo">My Website</h1>
                <ul class="nav-menu">
                    <li class="nav-item">
                        <a href="#home" class="nav-link">홈</a>
                    </li>
                    <li class="nav-item">
                        <a href="#about" class="nav-link">소개</a>
                    </li>
                    <li class="nav-item">
                        <a href="#services" class="nav-link">서비스</a>
                    </li>
                    <li class="nav-item">
                        <a href="#contact" class="nav-link">연락처</a>
                    </li>
                </ul>
            </div>
        </nav>
    </header>

    <main>
        <section id="home" class="hero">
            <div class="hero-content">
                <h1>AWS S3 + CloudFront로 구축된 정적 웹사이트</h1>
                <p>고성능, 고가용성, 저비용의 웹 호스팅 솔루션</p>
                <button class="cta-button" onclick="showInfo()">자세히 알아보기</button>
            </div>
        </section>

        <section id="about" class="about">
            <div class="container">
                <h2>프로젝트 소개</h2>
                <div class="feature-grid">
                    <div class="feature-card">
                        <h3>⚡ 빠른 속도</h3>
                        <p>CloudFront CDN을 통한 전 세계 빠른 콘텐츠 배포</p>
                    </div>
                    <div class="feature-card">
                        <h3>🔒 높은 보안</h3>
                        <p>AWS의 엔터프라이즈급 보안 인프라</p>
                    </div>
                    <div class="feature-card">
                        <h3>💰 경제적</h3>
                        <p>사용한 만큼만 지불하는 합리적인 비용</p>
                    </div>
                    <div class="feature-card">
                        <h3>📈 확장성</h3>
                        <p>트래픽 증가에도 자동으로 확장</p>
                    </div>
                </div>
            </div>
        </section>

        <section id="services" class="services">
            <div class="container">
                <h2>사용된 AWS 서비스</h2>
                <ul class="service-list">
                    <li><strong>Amazon S3</strong>: 정적 파일 저장 및 웹 호스팅</li>
                    <li><strong>Amazon CloudFront</strong>: 글로벌 CDN 서비스</li>
                    <li><strong>Route 53</strong>: 도메인 관리 (선택사항)</li>
                    <li><strong>AWS WAF</strong>: 웹 보안 (선택사항)</li>
                </ul>
            </div>
        </section>

        <section id="contact" class="contact">
            <div class="container">
                <h2>연락처</h2>
                <p>이 프로젝트에 대한 문의사항이 있으시면 언제든 연락해주세요.</p>
                <div class="contact-info">
                    <p>📧 Email: contact@example.com</p>
                    <p>🐙 GitHub: github.com/yourname</p>
                </div>
            </div>
        </section>
    </main>

    <footer>
        <p>&copy; 2025 AWS S3 + CloudFront 정적 웹사이트. All rights reserved.</p>
    </footer>

    <script src="script.js"></script>
</body>
</html>
```

#### B. CSS 파일 생성

**styles.css**
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Navigation */
.navbar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem 0;
    position: fixed;
    width: 100%;
    top: 0;
    z-index: 1000;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav-logo {
    color: white;
    font-size: 1.5rem;
    font-weight: bold;
}

.nav-menu {
    display: flex;
    list-style: none;
    gap: 2rem;
}

.nav-link {
    color: white;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.3s ease;
}

.nav-link:hover {
    color: #ffd700;
}

/* Hero Section */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-align: center;
    padding: 120px 0 80px;
    margin-top: 60px;
}

.hero-content h1 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    animation: fadeInUp 1s ease;
}

.hero-content p {
    font-size: 1.2rem;
    margin-bottom: 2rem;
    animation: fadeInUp 1s ease 0.2s both;
}

.cta-button {
    background: #ffd700;
    color: #333;
    padding: 12px 30px;
    font-size: 1.1rem;
    font-weight: bold;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    transition: transform 0.3s ease;
    animation: fadeInUp 1s ease 0.4s both;
}

.cta-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(255, 215, 0, 0.3);
}

/* About Section */
.about {
    padding: 80px 0;
    background: #f8f9fa;
}

.about h2 {
    text-align: center;
    font-size: 2rem;
    margin-bottom: 3rem;
    color: #333;
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
}

.feature-card {
    background: white;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
}

.feature-card:hover {
    transform: translateY(-5px);
}

.feature-card h3 {
    font-size: 1.3rem;
    margin-bottom: 1rem;
    color: #667eea;
}

/* Services Section */
.services {
    padding: 80px 0;
    background: white;
}

.services h2 {
    text-align: center;
    font-size: 2rem;
    margin-bottom: 3rem;
    color: #333;
}

.service-list {
    max-width: 600px;
    margin: 0 auto;
    list-style: none;
}

.service-list li {
    padding: 1rem;
    margin-bottom: 1rem;
    background: #f8f9fa;
    border-left: 4px solid #667eea;
    border-radius: 5px;
}

/* Contact Section */
.contact {
    padding: 80px 0;
    background: #f8f9fa;
    text-align: center;
}

.contact h2 {
    font-size: 2rem;
    margin-bottom: 2rem;
    color: #333;
}

.contact-info {
    margin-top: 2rem;
}

.contact-info p {
    margin: 0.5rem 0;
    font-size: 1.1rem;
}

/* Footer */
footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 2rem 0;
}

/* Animations */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Responsive Design */
@media (max-width: 768px) {
    .nav-menu {
        flex-direction: column;
        gap: 1rem;
    }
    
    .hero-content h1 {
        font-size: 2rem;
    }
    
    .feature-grid {
        grid-template-columns: 1fr;
    }
}
```

#### C. JavaScript 파일 생성

**script.js**
```javascript
// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    console.log('AWS S3 + CloudFront 정적 웹사이트 로드 완료!');
    
    // 네비게이션 스크롤 효과
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.backgroundColor = 'rgba(102, 126, 234, 0.95)';
        } else {
            navbar.style.backgroundColor = 'rgba(102, 126, 234, 1)';
        }
    });
    
    // 부드러운 스크롤 효과
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 페이지 로드 시 성능 메트릭 측정
    measurePerformance();
});

// CTA 버튼 클릭 이벤트
function showInfo() {
    alert(`🎉 이 웹사이트는 다음과 같은 AWS 서비스로 구축되었습니다:

📦 Amazon S3: 정적 파일 호스팅
🌐 Amazon CloudFront: 글로벌 CDN
⚡ 로딩 속도: ${measureLoadTime()}ms
🚀 배포 방식: 완전 자동화

비용 효율적이고 확장 가능한 웹 호스팅 솔루션입니다!`);
}

// 성능 측정 함수
function measurePerformance() {
    if ('performance' in window) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const navigation = performance.getEntriesByType('navigation')[0];
                const loadTime = navigation.loadEventEnd - navigation.fetchStart;
                
                console.log(`📊 성능 메트릭:
- 페이지 로드 시간: ${loadTime.toFixed(2)}ms
- DNS 조회: ${navigation.domainLookupEnd - navigation.domainLookupStart}ms
- TCP 연결: ${navigation.connectEnd - navigation.connectStart}ms
- 서버 응답: ${navigation.responseStart - navigation.requestStart}ms
- DOM 처리: ${navigation.domComplete - navigation.domLoading}ms`);
                
                // 성능 정보를 페이지에 표시 (개발용)
                if (loadTime < 1000) {
                    console.log('🚀 우수한 성능! CloudFront CDN 효과를 확인할 수 있습니다.');
                }
            }, 0);
        });
    }
}

// 로드 시간 측정 함수
function measureLoadTime() {
    if ('performance' in window) {
        const navigation = performance.getEntriesByType('navigation')[0];
        return Math.round(navigation.loadEventEnd - navigation.fetchStart);
    }
    return 'N/A';
}

// 간단한 방문자 통계 (LocalStorage 활용)
function trackVisit() {
    const visits = localStorage.getItem('siteVisits') || 0;
    const newVisits = parseInt(visits) + 1;
    localStorage.setItem('siteVisits', newVisits);
    
    console.log(`방문 횟수: ${newVisits}회`);
}

// 페이지 방문 추적
trackVisit();

// CloudFront 캐시 상태 확인 함수
function checkCacheStatus() {
    // CloudFront는 응답 헤더에 X-Cache 정보를 포함합니다
    fetch(window.location.href)
        .then(response => {
            const cacheStatus = response.headers.get('X-Cache');
            if (cacheStatus) {
                console.log(`CloudFront 캐시 상태: ${cacheStatus}`);
            }
        })
        .catch(error => {
            console.log('캐시 상태 확인 중 오류:', error);
        });
}

// 캐시 상태 확인
checkCacheStatus();
```

#### D. 에러 페이지 생성

**error.html**
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - 페이지를 찾을 수 없습니다</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        .error-container {
            max-width: 500px;
        }
        h1 {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }
        .back-button {
            background: #ffd700;
            color: #333;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: transform 0.3s ease;
        }
        .back-button:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>404</h1>
        <h2>페이지를 찾을 수 없습니다</h2>
        <p>요청하신 페이지가 존재하지 않거나 이동되었습니다.</p>
        <a href="/" class="back-button">홈으로 돌아가기</a>
    </div>
</body>
</html>
```

### 3단계: S3에 파일 업로드

```bash
# 파일들을 S3 버킷에 업로드
aws s3 sync ./website s3://my-static-website-bucket-unique-name

# 또는 개별 파일 업로드
aws s3 cp index.html s3://my-static-website-bucket-unique-name/
aws s3 cp styles.css s3://my-static-website-bucket-unique-name/
aws s3 cp script.js s3://my-static-website-bucket-unique-name/
aws s3 cp error.html s3://my-static-website-bucket-unique-name/
```

### 4단계: CloudFront 배포 생성

#### A. CloudFront 배포 설정

```json
{
    "CallerReference": "static-website-2025-08-24",
    "DefaultRootObject": "index.html",
    "Comment": "Static website hosting with S3 and CloudFront",
    "Enabled": true,
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-my-static-website-bucket",
                "DomainName": "my-static-website-bucket-unique-name.s3.ap-northeast-2.amazonaws.com",
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only"
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-my-static-website-bucket",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {
                "Forward": "none"
            }
        },
        "MinTTL": 0,
        "DefaultTTL": 86400,
        "MaxTTL": 31536000
    },
    "CustomErrorResponses": {
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/error.html",
                "ResponseCode": "404",
                "ErrorCachingMinTTL": 300
            }
        ]
    },
    "PriceClass": "PriceClass_All"
}
```

#### B. AWS CLI를 통한 CloudFront 배포

```bash
# CloudFront 배포 생성
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

### 5단계: 도메인 연결 (선택사항)

#### A. Route 53 호스팅 영역 생성

```bash
# 호스팅 영역 생성
aws route53 create-hosted-zone \
    --name example.com \
    --caller-reference $(date +%s)
```

#### B. A 레코드 생성

```json
{
    "Comment": "Creating A record for CloudFront distribution",
    "Changes": [
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "example.com",
                "Type": "A",
                "AliasTarget": {
                    "DNSName": "d123456789.cloudfront.net",
                    "EvaluateTargetHealth": false,
                    "HostedZoneId": "Z2FDTNDATAQYW2"
                }
            }
        }
    ]
}
```

## 🔧 성능 최적화

### 1. 캐싱 최적화

#### A. 파일 타입별 캐시 설정

```json
{
    "CacheBehaviors": {
        "Quantity": 3,
        "Items": [
            {
                "PathPattern": "*.css",
                "TargetOriginId": "S3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "DefaultTTL": 2592000,
                "MaxTTL": 31536000
            },
            {
                "PathPattern": "*.js",
                "TargetOriginId": "S3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "DefaultTTL": 2592000,
                "MaxTTL": 31536000
            },
            {
                "PathPattern": "*.html",
                "TargetOriginId": "S3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "DefaultTTL": 3600,
                "MaxTTL": 86400
            }
        ]
    }
}
```

### 2. 압축 최적화

```bash
# Gzip 압축 활성화를 위한 S3 메타데이터 설정
aws s3 cp styles.css s3://my-static-website-bucket-unique-name/ \
    --content-encoding gzip \
    --content-type "text/css"

aws s3 cp script.js s3://my-static-website-bucket-unique-name/ \
    --content-encoding gzip \
    --content-type "application/javascript"
```

### 3. 이미지 최적화

```html
<!-- WebP 형식 사용 예시 -->
<picture>
    <source srcset="hero-image.webp" type="image/webp">
    <source srcset="hero-image.jpg" type="image/jpeg">
    <img src="hero-image.jpg" alt="Hero Image">
</picture>
```

## 🔒 보안 강화

### 1. Origin Access Control (OAC) 설정

```json
{
    "OriginAccessControlConfig": {
        "Name": "S3-OAC-static-website",
        "Description": "OAC for static website",
        "SigningProtocol": "sigv4",
        "SigningBehavior": "always",
        "OriginAccessControlOriginType": "s3"
    }
}
```

### 2. S3 버킷 정책 업데이트 (OAC 사용 시)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-static-website-bucket-unique-name/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"
                }
            }
        }
    ]
}
```

### 3. AWS WAF 연결

```json
{
    "Name": "StaticWebsiteWAF",
    "Scope": "CLOUDFRONT",
    "DefaultAction": {
        "Allow": {}
    },
    "Rules": [
        {
            "Name": "AWSManagedRulesCommonRuleSet",
            "Priority": 1,
            "OverrideAction": {
                "None": {}
            },
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesCommonRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "CommonRuleSetMetric"
            }
        }
    ]
}
```

## 📊 모니터링 및 로깅

### 1. CloudWatch 메트릭 설정

주요 모니터링 지표:
- **요청 수 (Requests)**: 총 요청 수
- **바이트 다운로드 (BytesDownloaded)**: 전송된 데이터량  
- **오류율 (4xxErrorRate, 5xxErrorRate)**: 오류 발생률
- **캐시 히트율 (CacheHitRate)**: 캐시 효율성

### 2. 로그 분석

```bash
# CloudFront 액세스 로그 분석
aws logs start-query \
    --log-group-name /aws/cloudfront/distribution \
    --start-time $(date -d '1 hour ago' +%s) \
    --end-time $(date +%s) \
    --query-string 'fields @timestamp, @message | filter @message like /ERROR/'
```

## 💰 비용 최적화

### 1. S3 스토리지 클래스 최적화

```bash
# Intelligent-Tiering 활성화
aws s3api put-bucket-intelligent-tiering-configuration \
    --bucket my-static-website-bucket-unique-name \
    --id static-website-tiering \
    --intelligent-tiering-configuration \
    Id=static-website-tiering,Status=Enabled,Prefix=/
```

### 2. CloudFront 비용 클래스 설정

```json
{
    "PriceClass": "PriceClass_100",  // 가장 저렴한 옵션
    "Comment": "Cost-optimized distribution for static website"
}
```

### 3. 비용 모니터링

```bash
# 월별 비용 확인
aws ce get-cost-and-usage \
    --time-period Start=2025-08-01,End=2025-08-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

## 🚀 CI/CD 파이프라인 구축

### GitHub Actions를 활용한 자동 배포

**.github/workflows/deploy.yml**
```yaml
name: Deploy Static Website

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-2
    
    - name: Sync files to S3
      run: |
        aws s3 sync . s3://my-static-website-bucket-unique-name \
          --exclude ".git/*" \
          --exclude ".github/*" \
          --exclude "README.md" \
          --delete
    
    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
          --paths "/*"
```

## 🎯 성능 측정 결과

예상 성능 지표:
- **First Contentful Paint**: < 1.5초
- **Largest Contentful Paint**: < 2.5초  
- **Cumulative Layout Shift**: < 0.1
- **Time to Interactive**: < 3초

## 📈 확장 가능한 아키텍처

### Lambda@Edge를 활용한 고급 기능

```javascript
// A/B 테스트를 위한 Lambda@Edge 함수
exports.handler = (event, context, callback) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    // A/B 테스트 로직
    const testGroup = Math.random() < 0.5 ? 'A' : 'B';
    
    if (testGroup === 'B') {
        request.uri = '/v2' + request.uri;
    }
    
    // 사용자 그룹 헤더 추가
    headers['x-test-group'] = [{
        key: 'X-Test-Group',
        value: testGroup
    }];
    
    callback(null, request);
};
```

## 🔍 문제 해결 가이드

### 자주 발생하는 문제들

1. **403 Forbidden 오류**
   - S3 버킷 정책 확인
   - CloudFront OAC 설정 확인

2. **캐시가 업데이트되지 않음**
   - CloudFront 무효화(Invalidation) 실행
   - 캐시 헤더 설정 확인

3. **느린 로딩 속도**  
   - CloudFront 배포 상태 확인
   - 압축 설정 확인
   - 이미지 최적화 수행

## 📚 결론

AWS S3와 CloudFront를 활용한 정적 웹사이트 호스팅은 다음과 같은 이점을 제공합니다:

### ✅ 핵심 장점

1. **높은 성능**: 글로벌 CDN을 통한 빠른 콘텐츠 배포
2. **저렴한 비용**: 사용량 기반 과금으로 비용 효율적
3. **높은 가용성**: AWS의 글로벌 인프라 활용
4. **간편한 배포**: 파일 업로드만으로 즉시 배포 가능
5. **확장성**: 트래픽 증가에 자동 대응

### 🎯 추천 사용 사례

- 회사 소개 홈페이지
- 포트폴리오 웹사이트  
- 브로슈어 웹사이트
- SPA(Single Page Application)
- 정적 문서 사이트

### 🚀 다음 단계

1. **고급 기능 추가**
   - Lambda@Edge를 통한 동적 기능
   - AWS WAF를 통한 보안 강화
   - CloudWatch를 통한 상세 모니터링

2. **성능 최적화**
   - 이미지 최적화 및 WebP 형식 사용
   - Critical CSS 인라인화
   - 지연 로딩(Lazy Loading) 구현

3. **자동화 개선**
   - Infrastructure as Code (CloudFormation/CDK)
   - 멀티 환경 배포 파이프라인
   - 자동화된 성능 테스트

이제 여러분도 AWS의 강력한 서비스들을 활용해 전문적인 정적 웹사이트를 구축할 수 있습니다! 🎉
