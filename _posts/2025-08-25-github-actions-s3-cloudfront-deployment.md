---
layout: post
title: "GitHub Actions로 AWS S3 + CloudFront 자동 배포 파이프라인 구축하기"
categories: [aws-saa, devops, ci-cd]
tags: [aws, s3, cloudfront, github-actions, automation, deployment, invalidation]
date: 2025-08-25
---

## 📋 개요

정적 웹사이트의 배포 과정을 자동화하는 것은 개발 생산성을 크게 향상시킵니다. 이번 포스트에서는 GitHub Actions를 활용하여 AWS S3와 CloudFront를 통한 완전 자동화된 배포 파이프라인을 구축하는 방법을 상세히 알아보겠습니다.

### 🎯 목표

- GitHub에 코드 푸시 시 자동으로 S3에 배포
- CloudFront 캐시 무효화 자동 실행
- 배포 상태 및 결과 알림
- 환경별 배포 전략 구현
- 롤백 기능 구현

## 🏗️ 전체 아키텍처

```
[GitHub Repository] → [GitHub Actions] → [AWS S3] → [CloudFront] → [사용자]
                           ↓
[Slack/Discord 알림] ← [배포 상태 모니터링]
```

### 배포 플로우

1. **코드 푸시**: main 브랜치에 코드 푸시
2. **빌드**: 정적 파일 빌드 및 최적화
3. **테스트**: 링크 검증 및 성능 테스트
4. **배포**: S3에 파일 동기화
5. **무효화**: CloudFront 캐시 무효화
6. **알림**: 배포 결과 알림

## 🚀 GitHub Actions 워크플로우 구축

### 1단계: 기본 워크플로우 생성

**.github/workflows/deploy-production.yml**
```yaml
name: Deploy to Production

# 트리거 조건 설정
on:
  push:
    branches: [ main ]
    paths-ignore:
      - 'README.md'
      - 'docs/**'
      - '.gitignore'
  
  # 수동 실행도 가능하도록 설정
  workflow_dispatch:
    inputs:
      invalidate_cache:
        description: 'Invalidate CloudFront cache'
        required: false
        default: 'true'
        type: choice
        options:
          - 'true'
          - 'false'

# 환경변수 설정
env:
  AWS_REGION: ap-northeast-2
  S3_BUCKET: my-static-website-prod
  CLOUDFRONT_DISTRIBUTION_ID: E1234567890ABC

jobs:
  # 린터 및 테스트 작업
  lint-and-test:
    runs-on: ubuntu-latest
    name: 🔍 Lint and Test
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 🔧 Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          
      - name: 📦 Install dependencies
        run: |
          npm ci
          
      - name: 🧹 Run ESLint
        run: |
          npm run lint
          
      - name: 🧪 Run tests
        run: |
          npm run test
          
      - name: 🔗 Check for broken links
        run: |
          npm run link-check

  # 빌드 작업
  build:
    runs-on: ubuntu-latest
    name: 🏗️ Build
    needs: lint-and-test
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 🔧 Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          
      - name: 📦 Install dependencies
        run: npm ci
        
      - name: 🏗️ Build project
        run: |
          npm run build
          
      - name: 🗜️ Optimize images
        run: |
          npm run optimize-images
          
      - name: 📤 Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-files
          path: dist/
          retention-days: 1

  # 배포 작업
  deploy:
    runs-on: ubuntu-latest
    name: 🚀 Deploy to S3 and CloudFront
    needs: build
    environment: production
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 📥 Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-files
          path: dist/
          
      - name: 🔑 Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: 📊 Check S3 bucket status
        run: |
          echo "🔍 Checking S3 bucket status..."
          aws s3 ls s3://${{ env.S3_BUCKET }} --summarize --human-readable
          
      - name: 🔄 Sync files to S3
        run: |
          echo "🚀 Syncing files to S3..."
          aws s3 sync dist/ s3://${{ env.S3_BUCKET }} \
            --delete \
            --exact-timestamps \
            --exclude "*.DS_Store" \
            --exclude "*.git*" \
            --cache-control "public,max-age=31536000,immutable" \
            --metadata-directive REPLACE
            
      - name: 🎯 Set cache headers for HTML files
        run: |
          echo "🎯 Setting cache headers for HTML files..."
          aws s3 cp s3://${{ env.S3_BUCKET }}/ s3://${{ env.S3_BUCKET }}/ \
            --recursive \
            --exclude "*" \
            --include "*.html" \
            --metadata-directive REPLACE \
            --cache-control "public,max-age=3600,must-revalidate" \
            --content-type "text/html; charset=utf-8"
            
      - name: 🗑️ Invalidate CloudFront cache
        if: ${{ github.event.inputs.invalidate_cache != 'false' }}
        run: |
          echo "🗑️ Creating CloudFront invalidation..."
          INVALIDATION_ID=$(aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*" \
            --query 'Invalidation.Id' \
            --output text)
          
          echo "⏳ Waiting for invalidation to complete..."
          echo "Invalidation ID: $INVALIDATION_ID"
          
          # 무효화 완료까지 대기
          aws cloudfront wait invalidation-completed \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --id $INVALIDATION_ID
          
          echo "✅ CloudFront invalidation completed!"
          
      - name: 🌐 Get CloudFront URL
        id: get-url
        run: |
          CLOUDFRONT_URL=$(aws cloudfront get-distribution \
            --id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --query 'Distribution.DomainName' \
            --output text)
          echo "url=https://$CLOUDFRONT_URL" >> $GITHUB_OUTPUT
          echo "🌐 Website URL: https://$CLOUDFRONT_URL"
          
      - name: 📊 Deployment summary
        run: |
          echo "## 🚀 Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "- **S3 Bucket**: ${{ env.S3_BUCKET }}" >> $GITHUB_STEP_SUMMARY
          echo "- **CloudFront Distribution**: ${{ env.CLOUDFRONT_DISTRIBUTION_ID }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Website URL**: ${{ steps.get-url.outputs.url }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Commit**: ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Branch**: ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Deployed at**: $(date -u)" >> $GITHUB_STEP_SUMMARY
          
  # 배포 후 검증
  verify-deployment:
    runs-on: ubuntu-latest
    name: ✅ Verify Deployment
    needs: deploy
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 🔍 Health check
        run: |
          echo "🔍 Performing health check..."
          
          # CloudFront URL에서 상태 확인
          CLOUDFRONT_URL=$(aws cloudfront get-distribution \
            --id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --query 'Distribution.DomainName' \
            --output text)
          
          # HTTP 상태 코드 확인
          STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$CLOUDFRONT_URL")
          
          if [ $STATUS_CODE -eq 200 ]; then
            echo "✅ Health check passed! Status code: $STATUS_CODE"
          else
            echo "❌ Health check failed! Status code: $STATUS_CODE"
            exit 1
          fi
          
      - name: 🚦 Performance test
        run: |
          echo "🚦 Running performance test..."
          
          # Lighthouse CI를 사용한 성능 테스트
          npm install -g @lhci/cli
          
          # 간단한 성능 체크
          curl -s "https://pagespeed-insights.googleapis.com/pagespeed/v5/runPagespeed?url=https://$CLOUDFRONT_URL&strategy=desktop" \
            | jq '.lighthouseResult.categories.performance.score * 100' \
            | xargs -I {} echo "Performance Score: {}%"

  # Slack 알림
  notify:
    runs-on: ubuntu-latest
    name: 📢 Send Notification
    needs: [deploy, verify-deployment]
    if: always()
    
    steps:
      - name: 📢 Slack notification
        if: ${{ secrets.SLACK_WEBHOOK_URL }}
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          channel: '#deployments'
          webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
          fields: repo,message,commit,author,action,eventName,ref,workflow
```

### 2단계: 스테이징 환경용 워크플로우

**.github/workflows/deploy-staging.yml**
```yaml
name: Deploy to Staging

on:
  push:
    branches: [ develop ]
  pull_request:
    branches: [ main ]

env:
  AWS_REGION: ap-northeast-2
  S3_BUCKET: my-static-website-staging
  CLOUDFRONT_DISTRIBUTION_ID: E0987654321XYZ

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    name: 🧪 Deploy to Staging
    environment: staging
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 🔧 Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          
      - name: 📦 Install and build
        run: |
          npm ci
          npm run build:staging
          
      - name: 🔑 Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_STAGING }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_STAGING }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: 🚀 Deploy to staging
        run: |
          aws s3 sync dist/ s3://${{ env.S3_BUCKET }} --delete
          
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
            
      - name: 📝 Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🚀 **Staging deployment completed!**
              
              Preview URL: https://staging.example.com
              Commit: ${context.sha.substring(0, 7)}
              
              Please test the changes before merging.`
            })
```

### 3단계: 롤백 워크플로우

**.github/workflows/rollback.yml**
```yaml
name: Rollback Deployment

on:
  workflow_dispatch:
    inputs:
      target_commit:
        description: 'Target commit SHA to rollback to'
        required: true
        type: string
      reason:
        description: 'Reason for rollback'
        required: true
        type: string

env:
  AWS_REGION: ap-northeast-2
  S3_BUCKET: my-static-website-prod
  CLOUDFRONT_DISTRIBUTION_ID: E1234567890ABC

jobs:
  rollback:
    runs-on: ubuntu-latest
    name: ⏪ Rollback Deployment
    environment: production
    
    steps:
      - name: 📂 Checkout target commit
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.inputs.target_commit }}
          
      - name: 🔧 Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          
      - name: 📦 Install and build
        run: |
          npm ci
          npm run build
          
      - name: 🔑 Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: ⏪ Rollback to previous version
        run: |
          echo "🔄 Rolling back to commit: ${{ github.event.inputs.target_commit }}"
          echo "📝 Reason: ${{ github.event.inputs.reason }}"
          
          # S3에 이전 버전 배포
          aws s3 sync dist/ s3://${{ env.S3_BUCKET }} --delete
          
          # CloudFront 무효화
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
            
      - name: 📢 Create rollback issue
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `🚨 Rollback executed - ${new Date().toISOString()}`,
              body: `**Rollback Details:**
              - Target Commit: ${{ github.event.inputs.target_commit }}
              - Reason: ${{ github.event.inputs.reason }}
              - Executed by: @${{ github.actor }}
              - Timestamp: ${new Date().toISOString()}
              
              **Next Steps:**
              1. Verify the rollback was successful
              2. Investigate the root cause
              3. Plan the fix and redeployment`,
              labels: ['rollback', 'urgent']
            })
```

### 4단계: 고급 배포 전략

**.github/workflows/blue-green-deploy.yml**
```yaml
name: Blue-Green Deployment

on:
  push:
    branches: [ main ]
    paths: [ 'src/**', 'public/**' ]

env:
  AWS_REGION: ap-northeast-2

jobs:
  blue-green-deploy:
    runs-on: ubuntu-latest
    name: 🔵🟢 Blue-Green Deployment
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        
      - name: 🔍 Determine current environment
        id: current-env
        run: |
          # Route 53에서 현재 활성 환경 확인
          CURRENT_ALIAS=$(aws route53 list-resource-record-sets \
            --hosted-zone-id ${{ secrets.HOSTED_ZONE_ID }} \
            --query "ResourceRecordSets[?Name=='www.example.com.'].AliasTarget.DNSName" \
            --output text)
            
          if [[ $CURRENT_ALIAS == *"blue"* ]]; then
            echo "current=blue" >> $GITHUB_OUTPUT
            echo "target=green" >> $GITHUB_OUTPUT
            echo "target_bucket=my-website-green" >> $GITHUB_OUTPUT
            echo "target_distribution=${{ secrets.GREEN_DISTRIBUTION_ID }}" >> $GITHUB_OUTPUT
          else
            echo "current=green" >> $GITHUB_OUTPUT
            echo "target=blue" >> $GITHUB_OUTPUT
            echo "target_bucket=my-website-blue" >> $GITHUB_OUTPUT
            echo "target_distribution=${{ secrets.BLUE_DISTRIBUTION_ID }}" >> $GITHUB_OUTPUT
          fi
          
      - name: 🔧 Setup and build
        run: |
          npm ci
          npm run build
          
      - name: 🔑 Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: 🚀 Deploy to target environment
        run: |
          echo "🎯 Deploying to ${{ steps.current-env.outputs.target }} environment"
          
          # 타겟 환경에 배포
          aws s3 sync dist/ s3://${{ steps.current-env.outputs.target_bucket }} --delete
          
          # CloudFront 무효화
          aws cloudfront create-invalidation \
            --distribution-id ${{ steps.current-env.outputs.target_distribution }} \
            --paths "/*"
            
      - name: 🧪 Run smoke tests
        run: |
          # 타겟 환경에서 스모크 테스트 실행
          DISTRIBUTION_DOMAIN=$(aws cloudfront get-distribution \
            --id ${{ steps.current-env.outputs.target_distribution }} \
            --query 'Distribution.DomainName' \
            --output text)
            
          echo "🔍 Testing https://$DISTRIBUTION_DOMAIN"
          
          # 헬스체크
          curl -f "https://$DISTRIBUTION_DOMAIN" || exit 1
          
          # 주요 페이지 테스트
          curl -f "https://$DISTRIBUTION_DOMAIN/about" || exit 1
          curl -f "https://$DISTRIBUTION_DOMAIN/contact" || exit 1
          
      - name: 🔄 Switch traffic to new environment
        run: |
          echo "🔄 Switching traffic to ${{ steps.current-env.outputs.target }}"
          
          # Route 53에서 DNS 레코드 업데이트
          TARGET_DOMAIN=$(aws cloudfront get-distribution \
            --id ${{ steps.current-env.outputs.target_distribution }} \
            --query 'Distribution.DomainName' \
            --output text)
            
          # DNS 레코드 변경
          aws route53 change-resource-record-sets \
            --hosted-zone-id ${{ secrets.HOSTED_ZONE_ID }} \
            --change-batch '{
              "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                  "Name": "www.example.com",
                  "Type": "A",
                  "AliasTarget": {
                    "DNSName": "'$TARGET_DOMAIN'",
                    "EvaluateTargetHealth": false,
                    "HostedZoneId": "Z2FDTNDATAQYW2"
                  }
                }
              }]
            }'
            
      - name: ✅ Deployment completed
        run: |
          echo "✅ Blue-Green deployment completed successfully!"
          echo "Current active environment: ${{ steps.current-env.outputs.target }}"
          echo "Previous environment: ${{ steps.current-env.outputs.current }} (kept for rollback)"
```

## 🔧 필수 설정 작업

### 1. GitHub Secrets 설정

Repository Settings > Secrets and variables > Actions에서 다음 시크릿들을 설정하세요:

```bash
# AWS 인증 정보
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# 스테이징 환경 (선택사항)
AWS_ACCESS_KEY_ID_STAGING=AKIA...
AWS_SECRET_ACCESS_KEY_STAGING=...

# CloudFront 배포 ID
CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC
GREEN_DISTRIBUTION_ID=E0987654321XYZ
BLUE_DISTRIBUTION_ID=EABCDEF123456789

# Route 53 (Blue-Green 배포용)
HOSTED_ZONE_ID=Z1234567890ABC

# Slack 알림 (선택사항)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### 2. AWS IAM 정책 생성

**GitHub Actions용 IAM 정책**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::my-static-website-*",
                "arn:aws:s3:::my-static-website-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation",
                "cloudfront:GetDistribution",
                "cloudfront:GetInvalidation"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "route53:ChangeResourceRecordSets",
                "route53:GetChange",
                "route53:ListResourceRecordSets"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Package.json 스크립트 설정

**package.json**
```json
{
  "name": "static-website",
  "version": "1.0.0",
  "scripts": {
    "build": "npm run build:prod",
    "build:prod": "NODE_ENV=production webpack --mode=production",
    "build:staging": "NODE_ENV=staging webpack --mode=development",
    "lint": "eslint src/ --ext .js,.jsx,.ts,.tsx",
    "test": "jest",
    "link-check": "markdown-link-check README.md",
    "optimize-images": "imagemin src/assets/images/* --out-dir=dist/images"
  },
  "devDependencies": {
    "webpack": "^5.88.0",
    "eslint": "^8.45.0",
    "jest": "^29.6.0",
    "markdown-link-check": "^3.11.0",
    "imagemin": "^8.0.1"
  }
}
```

## 📊 모니터링 및 알림

### 1. 배포 상태 모니터링

**.github/workflows/monitor-deployment.yml**
```yaml
name: Monitor Deployment

on:
  schedule:
    - cron: '*/5 * * * *'  # 5분마다 실행
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    name: 📊 Monitor Website Health
    
    steps:
      - name: 🔍 Health Check
        run: |
          # 웹사이트 상태 확인
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://www.example.com)
          
          if [ $STATUS -ne 200 ]; then
            echo "❌ Website is down! Status: $STATUS"
            
            # Slack 알림
            curl -X POST -H 'Content-type: application/json' \
              --data '{"text":"🚨 Website is down! Status: '$STATUS'"}' \
              ${{ secrets.SLACK_WEBHOOK_URL }}
              
            exit 1
          else
            echo "✅ Website is healthy! Status: $STATUS"
          fi
          
      - name: 📈 Performance Check
        run: |
          # 페이지 로드 시간 측정
          LOAD_TIME=$(curl -s -w "%{time_total}" -o /dev/null https://www.example.com)
          
          # 5초 이상이면 경고
          if (( $(echo "$LOAD_TIME > 5.0" | bc -l) )); then
            echo "⚠️ Slow page load time: ${LOAD_TIME}s"
            
            curl -X POST -H 'Content-type: application/json' \
              --data '{"text":"⚠️ Slow page load time: '$LOAD_TIME's"}' \
              ${{ secrets.SLACK_WEBHOOK_URL }}
          fi
```

### 2. 배포 실패 시 자동 복구

**.github/workflows/auto-recovery.yml**
```yaml
name: Auto Recovery

on:
  workflow_run:
    workflows: ["Deploy to Production"]
    types:
      - completed

jobs:
  auto-recovery:
    runs-on: ubuntu-latest
    name: 🛠️ Auto Recovery
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    
    steps:
      - name: 📂 Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 2  # 이전 커밋까지 가져오기
          
      - name: ⏪ Auto rollback
        run: |
          # 이전 커밋으로 자동 롤백
          PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
          
          echo "🔄 Auto-rolling back to: $PREVIOUS_COMMIT"
          
          # 워크플로우 트리거
          gh workflow run rollback.yml \
            -f target_commit=$PREVIOUS_COMMIT \
            -f reason="Auto-rollback due to deployment failure"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 🔍 배포 성능 최적화

### 1. 캐시 효율성 개선

```yaml
# 파일 타입별 캐시 설정
- name: 📦 Set optimal cache headers
  run: |
    # CSS, JS 파일 - 1년 캐시
    aws s3 cp s3://${{ env.S3_BUCKET }}/ s3://${{ env.S3_BUCKET }}/ \
      --recursive --exclude "*" --include "*.css" --include "*.js" \
      --metadata-directive REPLACE \
      --cache-control "public,max-age=31536000,immutable"
    
    # 이미지 파일 - 6개월 캐시
    aws s3 cp s3://${{ env.S3_BUCKET }}/ s3://${{ env.S3_BUCKET }}/ \
      --recursive --exclude "*" --include "*.jpg" --include "*.png" --include "*.webp" \
      --metadata-directive REPLACE \
      --cache-control "public,max-age=15552000"
    
    # HTML 파일 - 1시간 캐시
    aws s3 cp s3://${{ env.S3_BUCKET }}/ s3://${{ env.S3_BUCKET }}/ \
      --recursive --exclude "*" --include "*.html" \
      --metadata-directive REPLACE \
      --cache-control "public,max-age=3600,must-revalidate"
```

### 2. 압축 최적화

```yaml
- name: 🗜️ Enable compression
  run: |
    # Gzip 압축 적용
    find dist/ -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec gzip -9 {} \;
    
    # 압축된 파일들을 원본 이름으로 업로드
    for file in $(find dist/ -name "*.gz"); do
      original_file=${file%.gz}
      aws s3 cp "$file" "s3://${{ env.S3_BUCKET }}/${original_file#dist/}" \
        --content-encoding gzip \
        --content-type "$(file -b --mime-type "$original_file")"
    done
```

### 3. 점진적 배포 (Canary Deployment)

```yaml
- name: 🐦 Canary deployment
  run: |
    # 트래픽의 10%만 새 버전으로 라우팅
    aws cloudfront update-distribution \
      --id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
      --distribution-config '{
        "CallerReference": "'$(date +%s)'",
        "DefaultCacheBehavior": {
          "TargetOriginId": "primary",
          "ViewerProtocolPolicy": "redirect-to-https",
          "Origins": {
            "Quantity": 2,
            "Items": [
              {
                "Id": "primary",
                "DomainName": "old-version.s3.amazonaws.com",
                "Weight": 90
              },
              {
                "Id": "canary",
                "DomainName": "new-version.s3.amazonaws.com", 
                "Weight": 10
              }
            ]
          }
        }
      }'
```

## 📈 메트릭 및 분석

### 배포 메트릭 수집

```yaml
- name: 📊 Collect deployment metrics
  run: |
    # 배포 시간 측정
    DEPLOY_START=$(date -d "${{ github.event.head_commit.timestamp }}" +%s)
    DEPLOY_END=$(date +%s)
    DEPLOY_DURATION=$((DEPLOY_END - DEPLOY_START))
    
    # CloudWatch 커스텀 메트릭 전송
    aws cloudwatch put-metric-data \
      --namespace "GitHub/Deployment" \
      --metric-data \
        MetricName=DeploymentDuration,Value=$DEPLOY_DURATION,Unit=Seconds \
        MetricName=DeploymentSuccess,Value=1,Unit=Count
        
    echo "📊 Deployment took: ${DEPLOY_DURATION} seconds"
```

## 🎯 고급 기능

### 1. 다중 환경 관리

```yaml
strategy:
  matrix:
    environment: [staging, production]
    include:
      - environment: staging
        s3_bucket: my-website-staging
        cloudfront_id: E1234567890ABC
      - environment: production  
        s3_bucket: my-website-prod
        cloudfront_id: E0987654321XYZ
```

### 2. 조건부 배포

```yaml
- name: 🎯 Conditional deployment
  if: |
    contains(github.event.head_commit.message, '[deploy]') ||
    github.ref == 'refs/heads/main'
```

### 3. 배포 승인 워크플로우

```yaml
environment:
  name: production
  url: https://www.example.com
  protection_rules:
    - type: required_reviewers
      reviewers: ['admin-team']
    - type: wait_timer
      minutes: 5
```

## 🔒 보안 고려사항

### 1. 최소 권한 원칙

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::specific-bucket/*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/Environment": "production"
        }
      }
    }
  ]
}
```

### 2. 시크릿 로테이션

```yaml
- name: 🔑 Rotate access keys
  if: github.event.schedule
  run: |
    # 90일마다 액세스 키 로테이션 알림
    LAST_ROTATION=$(aws iam get-access-key-last-used \
      --access-key-id ${{ secrets.AWS_ACCESS_KEY_ID }} \
      --query 'AccessKeyLastUsed.LastUsedDate')
      
    # 알림 로직...
```

## 📚 결론

GitHub Actions를 활용한 AWS S3 + CloudFront 자동 배포 파이프라인을 통해 다음과 같은 이점을 얻을 수 있습니다:

### ✅ 핵심 장점

1. **완전 자동화**: 코드 푸시부터 배포까지 자동화
2. **신뢰성**: 테스트, 검증, 롤백 기능으로 안정적 배포
3. **가시성**: 배포 상태 모니터링 및 알림
4. **확장성**: 다양한 환경과 배포 전략 지원
5. **비용 효율성**: 무료 GitHub Actions 사용량 활용

### 🚀 추천 다음 단계

1. **Infrastructure as Code**: CloudFormation/Terraform으로 인프라 관리
2. **고급 테스트**: E2E 테스트, 보안 스캔 추가
3. **성능 모니터링**: Real User Monitoring 구현
4. **A/B 테스트**: 기능별 점진적 릴리스

이제 여러분도 프로급 자동 배포 파이프라인을 구축할 수 있습니다! 🎉
