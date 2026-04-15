---
layout: post
title: "AGENTS.md 작성 전략: AI 하네스 엔지니어링으로 LLM 성능 극대화하기"
date: 2026-04-15 10:00:00 +0900
categories: [AI, Engineering, LLM]
tags: [AI, LLM, AGENTS.md, Harness Engineering, Instructions, Copilot, Agent, Lint, Pre-commit, DevOps]
render_with_liquid: false
image: "/assets/img/posts/2026-04-15-agents-md-strategy-for-ai-harness-engineering.webp"
---

AI 에이전트가 프로덕션 환경에서 효과적으로 작동하려면 단순히 좋은 프롬프트를 작성하는 것만으로는 부족합니다. **AGENTS.md**와 같은 커스터마이제이션 파일을 전략적으로 구성하고, 코드 품질 도구로 AI의 출력을 제한하는 것이 핵심입니다. 이는 하네스 엔지니어링의 연장선이자 실전 전략입니다.

## 🎯 왜 AGENTS.md 전략이 중요한가?

AI 에이전트는 프로젝트의 컨텍스트를 이해하지 못하면 비효율적이거나 잘못된 코드를 생성합니다. AGENTS.md를 포함한 커스터마이제이션 파일은 **에이전트의 행동을 설계하고 제약하는 청사진**입니다.

### 전통적 접근의 문제점

```markdown
<!-- ❌ 비효율적인 AGENTS.md -->
# Project Instructions

- Write good code
- Follow best practices
- Be helpful and accurate
- Use TypeScript
```

**문제점:**
- 너무 일반적이고 애매모호
- 구체적인 프로젝트 컨텍스트 부족
- 우선순위와 제약사항 불명확
- 파일 크기가 커질수록 관리 불가능

### 전략적 접근

```markdown
<!-- ✅ 효과적인 AGENTS.md 구조 -->
# Project: E-commerce Platform

## Quick Start
읽기: [개발 워크플로우](.github/instructions/workflow.instructions.md)
도구: [테스트 가이드](.github/skills/testing/SKILL.md)

## Core Principles
1. API-first 아키텍처 (OpenAPI 3.0 스펙 준수)
2. 타입 안정성 최우선 (TypeScript strict mode)
3. 모든 비즈니스 로직은 테스트 커버리지 80% 이상

## File Organization Strategy
상세 내용은 하위 파일 참조:
- API 개발: `.github/instructions/api.instructions.md`
- 프론트엔드: `.github/instructions/frontend.instructions.md`
- 데이터베이스: `.github/instructions/database.instructions.md`
```

## 📂 파일 분리 전략: 모듈화된 인스트럭션

### 1. 계층적 구조 설계

하나의 거대한 AGENTS.md보다 **역할별로 분리된 파일 시스템**이 훨씬 효과적입니다.

```
.github/
├── AGENTS.md                          # 프로젝트 전체 오버뷰 (짧게!)
├── copilot-instructions.md            # 글로벌 코딩 스타일
├── instructions/                      # 파일 타입별 세부 지침
│   ├── api.instructions.md           # API 엔드포인트 개발
│   ├── frontend.instructions.md      # React 컴포넌트 작성
│   ├── database.instructions.md      # Prisma 스키마 관리
│   ├── testing.instructions.md       # 테스트 작성 가이드
│   └── deployment.instructions.md    # CI/CD 관련 작업
├── skills/                            # 반복 워크플로우
│   ├── api-endpoint/                 # API 엔드포인트 생성 스킬
│   │   ├── SKILL.md
│   │   └── template.ts
│   ├── component-generator/          # React 컴포넌트 생성
│   │   ├── SKILL.md
│   │   └── template.tsx
│   └── migration/                    # DB 마이그레이션
│       ├── SKILL.md
│       └── template.sql
└── hooks/                            # 강제 실행 규칙
    ├── pre-commit.json               # 코드 제출 전 검증
    └── post-tool-use.json            # AI 도구 사용 후 검증
```

### 2. applyTo 패턴 활용

각 instruction 파일은 **특정 파일 패턴에만 적용**되도록 설정합니다.

```markdown
<!-- api.instructions.md -->
---
description: "API 엔드포인트 개발 시 적용. RESTful 설계, OpenAPI 스펙 준수"
applyTo:
  - "src/api/**/*.ts"
  - "src/routes/**/*.ts"
---

# API Development Guidelines

## Endpoint Structure
- 모든 엔드포인트는 `src/api/v1/` 하위에 위치
- 파일명: `{resource}.controller.ts`, `{resource}.service.ts`
- OpenAPI 데코레이터 필수

## Request Validation
```typescript
// Zod 스키마로 입력 검증 (Yup은 사용하지 않음)
import { z } from 'zod';

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(50),
  age: z.number().int().positive().optional()
});

export const createUser = async (req: Request, res: Response) => {
  const validated = CreateUserSchema.parse(req.body);
  // ...
};
```

## Error Handling
- 모든 에러는 `src/utils/errors.ts`의 커스텀 에러 클래스 사용
- 민감 정보 노출 금지 (stacktrace는 로그에만)
```

### 3. 우선순위 명시

인스트럭션 간의 충돌을 방지하기 위해 우선순위를 명확히 합니다.

```markdown
<!-- copilot-instructions.md -->
# Global Coding Standards (우선순위: LOW)

모든 파일에 적용되는 기본 규칙:
- Prettier로 포맷팅 (설정: `.prettierrc`)
- ESLint 규칙 준수
- 주석은 한국어 사용 가능

---

<!-- api.instructions.md -->
# API Development (우선순위: HIGH)

이 가이드는 `copilot-instructions.md`를 **오버라이드**합니다.

- API 파일의 주석은 **영어로만** 작성 (OpenAPI 생성 때문)
- JSDoc 형식 필수
```

## 🔒 하네스 엔지니어링: 강제 제약으로 품질 보장

AI가 아무리 똑똑해도 실수할 수 있습니다. **린트, 테스트, pre-commit 훅**으로 AI 출력을 강제로 검증하는 것이 하네스 엔지니어링의 핵심입니다.

### 1. Pre-commit Hooks: AI 코드의 게이트키퍼

AI가 생성한 코드가 커밋되기 전에 자동으로 검증합니다.

```json
// .github/hooks/pre-commit.json
{
  "name": "pre-commit-quality-gate",
  "events": ["PreToolUse"],
  "filters": {
    "tools": ["replace_string_in_file", "create_file", "multi_replace_string_in_file"]
  },
  "command": "bash .github/hooks/pre-commit.sh",
  "requireApproval": true,
  "failOnError": true
}
```

```bash
#!/bin/bash
# .github/hooks/pre-commit.sh

echo "🔍 AI 생성 코드 검증 시작..."

# 1. TypeScript 타입 체크
echo "📘 TypeScript 컴파일 체크..."
npm run type-check
if [ $? -ne 0 ]; then
  echo "❌ 타입 에러 발견! AI가 생성한 코드를 수정하세요."
  exit 1
fi

# 2. ESLint 검사
echo "🔎 ESLint 검사..."
npm run lint -- --max-warnings 0
if [ $? -ne 0 ]; then
  echo "❌ Lint 에러 발견!"
  exit 1
fi

# 3. 단위 테스트 실행
echo "🧪 단위 테스트 실행..."
npm run test:unit
if [ $? -ne 0 ]; then
  echo "❌ 테스트 실패! AI가 기존 기능을 망가뜨렸습니다."
  exit 1
fi

# 4. 커버리지 체크
echo "📊 테스트 커버리지 확인..."
COVERAGE=$(npm run test:coverage -- --silent | grep "All files" | awk '{print $10}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
  echo "❌ 테스트 커버리지 부족: ${COVERAGE}% (최소 80% 필요)"
  exit 1
fi

# 5. 보안 스캔
echo "🔐 보안 취약점 스캔..."
npm audit --audit-level=high
if [ $? -ne 0 ]; then
  echo "⚠️  보안 취약점 발견! 검토 필요"
  exit 1
fi

echo "✅ 모든 검증 통과!"
exit 0
```

### 2. Post-generation Validation: 생성 후 즉시 검증

AI가 파일을 생성하거나 수정한 직후 자동 검증을 실행합니다.

```json
// .github/hooks/post-tool-use.json
{
  "name": "post-generation-validator",
  "events": ["PostToolUse"],
  "filters": {
    "tools": ["create_file"],
    "patterns": ["src/**/*.ts", "src/**/*.tsx"]
  },
  "command": "node .github/scripts/validate-generated-file.js ${FILES}",
  "failOnError": true
}
```

```javascript
// .github/scripts/validate-generated-file.js
const fs = require('fs');
const path = require('path');
const { ESLint } = require('eslint');

async function validateFile(filePath) {
  console.log(`🔍 검증 중: ${filePath}`);

  // 1. 파일 존재 확인
  if (!fs.existsSync(filePath)) {
    throw new Error(`파일이 존재하지 않습니다: ${filePath}`);
  }

  // 2. 파일 크기 체크 (너무 크면 AI가 실수한 것)
  const stats = fs.statSync(filePath);
  const maxSizeKB = 100;
  if (stats.size / 1024 > maxSizeKB) {
    throw new Error(`파일이 너무 큽니다: ${stats.size / 1024}KB (최대 ${maxSizeKB}KB)`);
  }

  // 3. 금지된 패턴 체크
  const content = fs.readFileSync(filePath, 'utf-8');
  const forbiddenPatterns = [
    { pattern: /console\.log/g, message: 'console.log 사용 금지 (logger 사용)' },
    { pattern: /any\s*\)/g, message: 'TypeScript any 타입 사용 금지' },
    { pattern: /TODO|FIXME/g, message: 'TODO/FIXME 코멘트 발견' },
    { pattern: /@ts-ignore/g, message: '@ts-ignore 사용 금지' },
  ];

  for (const { pattern, message } of forbiddenPatterns) {
    if (pattern.test(content)) {
      throw new Error(`${message} in ${filePath}`);
    }
  }

  // 4. ESLint 검증
  const eslint = new ESLint();
  const results = await eslint.lintFiles([filePath]);
  const hasErrors = results.some(result => result.errorCount > 0);

  if (hasErrors) {
    const formatter = await eslint.loadFormatter('stylish');
    const resultText = formatter.format(results);
    throw new Error(`ESLint 에러:\n${resultText}`);
  }

  // 5. 필수 주석 체크 (파일 헤더)
  const requiredHeader = [
    '/**',
    ' * @file',
    ' * @description',
    ' * @author',
    ' */'
  ];

  const hasHeader = requiredHeader.every(line => 
    content.includes(line)
  );

  if (!hasHeader) {
    console.warn(`⚠️  파일 헤더 주석이 없습니다: ${filePath}`);
  }

  console.log(`✅ ${filePath} 검증 완료`);
}

// 커맨드 라인 인자로 받은 파일들 검증
const files = process.argv.slice(2);
Promise.all(files.map(validateFile))
  .then(() => {
    console.log('✅ 모든 파일 검증 완료');
    process.exit(0);
  })
  .catch(error => {
    console.error('❌ 검증 실패:', error.message);
    process.exit(1);
  });
```

### 3. Lint 규칙: AI에게 명확한 경계 설정

ESLint, Prettier, TypeScript를 조합해 AI가 벗어날 수 없는 경계를 만듭니다.

```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
  ],
  rules: {
    // AI가 자주 실수하는 부분 강제
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'error',
    '@typescript-eslint/no-unused-vars': ['error', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_' 
    }],
    
    // 코드 품질 강제
    'complexity': ['error', 10],  // 순환 복잡도 10 이하
    'max-lines-per-function': ['error', 50],  // 함수 최대 50줄
    'max-depth': ['error', 3],  // 중첩 최대 3단계
    
    // 보안 관련
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    
    // AI가 놓치기 쉬운 부분
    'require-await': 'error',
    'no-return-await': 'error',
    'prefer-const': 'error',
    
    // 주석 강제
    'require-jsdoc': ['error', {
      require: {
        FunctionDeclaration: true,
        MethodDefinition: true,
        ClassDeclaration: true,
      }
    }],
  },
};
```

```json
// tsconfig.json - 엄격한 타입 체크
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true
  }
}
```

### 4. 자동화된 테스트: AI 출력의 최종 방어선

AI가 생성한 코드는 반드시 테스트를 통과해야 합니다.

```typescript
// jest.config.js
module.exports = {
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.tsx',
    '!src/**/__tests__/**'
  ]
};
```

```yaml
# .github/workflows/ai-code-validation.yml
name: AI Generated Code Validation

on:
  pull_request:
    branches: [main, develop]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check if PR is from AI
        id: check-ai
        run: |
          if [[ "${{ github.event.pull_request.user.login }}" == "github-actions[bot]" ]]; then
            echo "is_ai=true" >> $GITHUB_OUTPUT
          fi
      
      - name: Enhanced validation for AI code
        if: steps.check-ai.outputs.is_ai == 'true'
        run: |
          echo "🤖 AI가 생성한 PR 감지 - 강화된 검증 시작"
          
          # 1. 타입 체크
          npm run type-check
          
          # 2. Lint (warnings도 에러로 처리)
          npm run lint -- --max-warnings 0
          
          # 3. 테스트 (커버리지 90% 요구)
          npm run test:coverage -- --coverageThreshold='{"global":{"branches":90,"functions":90,"lines":90,"statements":90}}'
          
          # 4. 보안 스캔
          npm audit --production --audit-level=moderate
          
          # 5. 번들 사이즈 체크
          npm run build
          if [ $(du -k dist/ | cut -f1) -gt 5000 ]; then
            echo "❌ 번들 크기 초과 (최대 5MB)"
            exit 1
          fi
          
          # 6. 성능 테스트
          npm run test:performance
          
          echo "✅ 모든 검증 통과"
      
      - name: Code Quality Report
        if: steps.check-ai.outputs.is_ai == 'true'
        run: |
          npm run analyze:complexity
          npm run analyze:dependencies
```

## 📋 AGENTS.md 작성 베스트 프랙티스

### 1. 짧고 명확한 오버뷰

AGENTS.md는 프로젝트의 "목차"여야 하지 "백과사전"이 아닙니다.

```markdown
<!-- ✅ 좋은 AGENTS.md -->
# E-commerce Platform API

## 프로젝트 개요
Node.js + TypeScript + PostgreSQL 기반 REST API

## 핵심 원칙
1. 타입 안정성 (TypeScript strict mode)
2. API-first (OpenAPI 3.0 스펙 준수)
3. 테스트 주도 (최소 80% 커버리지)

## 시작하기
새로운 작업 시작 전 읽기:
- [개발 워크플로우](.github/instructions/workflow.instructions.md)
- [코딩 스타일](.github/copilot-instructions.md)

## 파일별 가이드
AI가 다음 패턴의 파일을 수정할 때 자동 적용:
- API 엔드포인트: `.github/instructions/api.instructions.md`
- 데이터베이스 스키마: `.github/instructions/database.instructions.md`
- 테스트 작성: `.github/instructions/testing.instructions.md`

## 자동화 워크플로우
반복 작업은 스킬 사용:
- `/api-endpoint` - 새 API 엔드포인트 생성
- `/crud-generator` - CRUD 보일러플레이트 생성
- `/test-suite` - 테스트 파일 생성

## 품질 게이트
모든 코드는 다음을 통과해야 함:
- Pre-commit hooks (타입 체크, Lint, 테스트)
- CI/CD 파이프라인 (보안 스캔, 성능 테스트)
```

### 2. 구체적인 예시 포함

추상적인 지침보다 실제 코드 예시가 훨씬 효과적입니다.

```markdown
<!-- api.instructions.md -->
## Error Handling

❌ **나쁜 예:**
```typescript
try {
  const user = await db.user.findOne(id);
  return user;
} catch (error) {
  console.log(error);
  throw error;
}
```

✅ **좋은 예:**
```typescript
import { NotFoundError } from '@/utils/errors';
import { logger } from '@/utils/logger';

try {
  const user = await db.user.findOne(id);
  if (!user) {
    throw new NotFoundError('User', id);
  }
  return user;
} catch (error) {
  logger.error('Failed to fetch user', { userId: id, error });
  throw error;
}
```

## API Response Format

모든 API 응답은 다음 형식을 따릅니다:

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta?: {
    timestamp: string;
    requestId: string;
  };
}
```
```

### 3. 우선순위와 트레이드오프 명시

AI가 판단을 내려야 할 때 기준을 제공합니다.

```markdown
## 성능 vs 가독성 트레이드오프

**우선순위: 가독성 > 성능**

이유: 프로덕션 트래픽이 아직 낮고, 유지보수가 더 중요함

예외:
- Hot path (초당 1000+ 요청): 성능 최적화 우선
- 데이터 처리 파이프라인: 배치 최적화 우선
- 실시간 API (< 100ms 응답): 성능 우선

```typescript
// ✅ 기본적인 경우 - 가독성 우선
const activeUsers = users.filter(user => user.isActive);

// ✅ Hot path - 성능 우선 (미리 인덱싱된 맵 사용)
const activeUsers = activeUserMap.get(orgId);
```
```

### 4. 문서화 요구사항

AI가 생성한 코드에 필수적인 주석과 문서를 명시합니다.

```markdown
## 문서화 필수 사항

### 모든 Public API
```typescript
/**
 * 사용자를 생성합니다.
 * 
 * @param data - 생성할 사용자 데이터
 * @param data.email - 이메일 주소 (고유해야 함)
 * @param data.name - 사용자 이름
 * @returns 생성된 사용자 객체
 * @throws {ValidationError} 입력 데이터가 유효하지 않은 경우
 * @throws {ConflictError} 이메일이 이미 존재하는 경우
 * 
 * @example
 * const user = await createUser({
 *   email: 'user@example.com',
 *   name: 'John Doe'
 * });
 */
export async function createUser(data: CreateUserDto): Promise<User> {
  // ...
}
```

### 복잡한 비즈니스 로직
```typescript
/**
 * 할인 정책:
 * 1. VIP 회원: 20% 기본 할인
 * 2. 첫 구매: 10% 추가 할인
 * 3. 프로모션 코드: 최대 30% (다른 할인과 중복 불가)
 * 
 * 최종 할인율 = min(VIP할인 + 첫구매할인, 프로모션할인, 50%)
 */
function calculateDiscount(user: User, promoCode?: string): number {
  // ...
}
```

### README 업데이트
- 새 API 엔드포인트 추가 시: `docs/api/README.md` 업데이트
- 새 환경변수 추가 시: `README.md`의 Configuration 섹션 업데이트
```

## 🔄 통합 워크플로우: 모든 것을 하나로

실제 프로덕션에서는 이 모든 요소가 하나의 파이프라인으로 통합됩니다.

```yaml
# .github/workflows/ai-harness-pipeline.yml
name: AI Harness Engineering Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # Step 1: 코드 품질 검증
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      
      - name: Install dependencies
        run: npm ci
      
      - name: TypeScript Type Check
        run: npm run type-check
      
      - name: ESLint
        run: npm run lint -- --max-warnings 0
      
      - name: Prettier
        run: npm run format:check
      
      - name: Spell Check (주석 및 문서)
        run: npx cspell "**/*.{ts,tsx,md}"
  
  # Step 2: 테스트 및 커버리지
  test:
    runs-on: ubuntu-latest
    needs: quality-gate
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      
      - name: Install dependencies
        run: npm ci
      
      - name: Unit Tests
        run: npm run test:unit -- --coverage
      
      - name: Integration Tests
        run: npm run test:integration
      
      - name: E2E Tests
        run: npm run test:e2e
      
      - name: Coverage Report
        uses: codecov/codecov-action@v3
        with:
          fail_ci_if_error: true
          threshold: 80%
  
  # Step 3: 보안 스캔
  security:
    runs-on: ubuntu-latest
    needs: quality-gate
    steps:
      - uses: actions/checkout@v3
      
      - name: Dependency Vulnerability Scan
        run: npm audit --production --audit-level=high
      
      - name: SAST (Static Analysis)
        uses: github/codeql-action/analyze@v2
      
      - name: Secret Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
  
  # Step 4: 성능 및 번들 크기
  performance:
    runs-on: ubuntu-latest
    needs: quality-gate
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      
      - name: Build
        run: npm run build
      
      - name: Bundle Size Check
        run: |
          SIZE=$(du -sk dist/ | cut -f1)
          MAX_SIZE=5000  # 5MB
          if [ $SIZE -gt $MAX_SIZE ]; then
            echo "❌ Bundle size exceeded: ${SIZE}KB > ${MAX_SIZE}KB"
            exit 1
          fi
          echo "✅ Bundle size OK: ${SIZE}KB"
      
      - name: Lighthouse CI
        uses: treosh/lighthouse-ci-action@v9
        with:
          runs: 3
          budgetPath: ./budget.json
  
  # Step 5: AI 코드 메트릭 분석
  ai-metrics:
    runs-on: ubuntu-latest
    needs: [test, security, performance]
    steps:
      - uses: actions/checkout@v3
      
      - name: Code Complexity Analysis
        run: npx ts-complex --threshold 10 src/
      
      - name: Cyclomatic Complexity
        run: npx complexity-report src/ --format json --output complexity.json
      
      - name: AI Code Quality Score
        run: |
          node .github/scripts/calculate-ai-score.js
      
      - name: Comment PR with Metrics
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const metrics = require('./metrics.json');
            const comment = `
            ## 🤖 AI 코드 품질 리포트
            
            - **타입 안정성**: ${metrics.typeScore}%
            - **테스트 커버리지**: ${metrics.coverage}%
            - **코드 복잡도**: ${metrics.complexity} (최대 10)
            - **보안 점수**: ${metrics.securityScore}%
            - **번들 크기**: ${metrics.bundleSize}KB
            
            ${metrics.passed ? '✅ 모든 품질 기준 통과' : '❌ 품질 기준 미달'}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

## 📊 효과 측정: 하네스 엔지니어링의 ROI

이러한 전략을 도입한 후 실제로 측정해야 할 메트릭:

### 1. 코드 품질 메트릭

```typescript
// .github/scripts/calculate-ai-score.js
interface QualityMetrics {
  typeScore: number;        // TypeScript 타입 커버리지
  testCoverage: number;     // 테스트 커버리지
  complexity: number;       // 평균 순환 복잡도
  duplication: number;      // 코드 중복률
  securityScore: number;    // 보안 취약점 점수
  documentationScore: number; // JSDoc 커버리지
}

async function calculateScore(): Promise<number> {
  const metrics: QualityMetrics = {
    typeScore: await getTypeScriptCoverage(),
    testCoverage: await getTestCoverage(),
    complexity: await getAverageComplexity(),
    duplication: await getDuplicationRate(),
    securityScore: await getSecurityScore(),
    documentationScore: await getDocumentationCoverage()
  };

  // 가중 평균 계산
  const weights = {
    typeScore: 0.20,
    testCoverage: 0.25,
    complexity: 0.15,
    duplication: 0.10,
    securityScore: 0.20,
    documentationScore: 0.10
  };

  const score = Object.entries(metrics).reduce((total, [key, value]) => {
    return total + (value * weights[key]);
  }, 0);

  return Math.round(score);
}
```

### 2. 개발 효율성 메트릭

```typescript
interface EfficiencyMetrics {
  avgTimeToFirstCommit: number;  // 이슈 생성부터 첫 커밋까지
  avgReviewIterations: number;   // PR당 평균 리뷰 라운드
  bugReopenRate: number;         // 재오픈된 버그 비율
  aiGeneratedCodeRejection: number; // AI 코드 거부율
}

// 목표:
// - 첫 커밋까지 시간: 50% 감소
// - 리뷰 반복: 평균 1.5회 이하
// - 버그 재오픈율: 5% 이하
// - AI 코드 거부율: 10% 이하
```

## 🎓 핵심 교훈

### 1. AI는 도구, 하네스가 시스템
프롬프트만으로는 부족합니다. **제약(constraints), 검증(validation), 가이드(guidance)**의 3박자가 맞아야 합니다.

### 2. 파일 분리는 확장성의 핵심
거대한 AGENTS.md는 유지보수 악몽입니다. **모듈화, 계층화, 목차화**하세요.

### 3. 강제가 신뢰를 만든다
AI를 믿지 말고 **검증**하세요. Lint, 테스트, 훅은 선택이 아닌 필수입니다.

### 4. 점진적 개선
처음부터 완벽할 필요는 없습니다. **측정 → 개선 → 반복**의 사이클을 돌리세요.

## 📚 다음 단계 학습 자료

1. **VS Code Agent Customization 공식 문서**
   - AGENTS.md, instructions, skills의 상세 스펙

2. **Husky + lint-staged**
   - Pre-commit 훅 설정 가이드

3. **SonarQube / CodeClimate**
   - 자동화된 코드 품질 분석

4. **Renovate Bot**
   - 의존성 자동 업데이트 및 보안 패치

---

AI 에이전트는 강력하지만, 올바른 가이드라인과 제약 없이는 위험합니다. AGENTS.md와 하네스 엔지니어링 전략으로 AI의 잠재력을 안전하게 최대화하세요. 🚀
