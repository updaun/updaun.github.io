---
layout: post
title: "AWS RDS에서 Neon으로 PostgreSQL 마이그레이션 완벽 가이드"
date: 2025-07-29 10:00:00 +0900
categories: [Database, Migration, PostgreSQL]
tags: [Neon, AWS RDS, PostgreSQL, Migration, LogicalReplication, Database, 데이터베이스, 마이그레이션, 넥온]
image: "/assets/img/posts/2025-07-29-aws-rds-to-neon-migration-guide.webp"
---

**Neon**은 현대적인 서버리스 PostgreSQL 플랫폼으로, **자동 스케일링**, **브랜치 기능**, **더 저렴한 비용** 등의 장점을 제공합니다. 이 글에서는 **AWS RDS PostgreSQL에서 Neon으로 안전하게 마이그레이션하는 전체 과정**을 논리적 복제(Logical Replication)를 활용해 단계별로 설명하겠습니다.

## 🎯 Neon이란?

**Neon**은 **서버리스 PostgreSQL 플랫폼**으로, 기존 관리형 데이터베이스의 한계를 뛰어넘는 혁신적인 기능들을 제공합니다.

### Neon의 핵심 장점
```
AWS RDS               →      Neon
┌─────────────────┐         ┌─────────────────┐
│ 고정 인스턴스    │         │ 자동 스케일링    │
│ 수동 백업 관리   │         │ 자동 브랜치 기능 │
│ 고정 비용 구조   │         │ 사용량 기반 요금 │
│ 제한된 개발 환경 │         │ 무제한 브랜치    │
└─────────────────┘         └─────────────────┘
```

## 📋 사전 준비사항

### 1. 필수 조건
- **소스**: AWS RDS PostgreSQL 인스턴스
- **목적지**: Neon 프로젝트 (미리 생성 필요)
- **권한**: 소스 DB에 대한 관리자 권한

### 2. Neon 프로젝트 생성
1. [Neon Console](https://console.neon.tech)에서 새 프로젝트 생성
2. PostgreSQL 버전 선택 (소스 DB와 동일하거나 상위 버전)
3. 리전 선택 (지연시간 최소화를 위해 AWS RDS와 가까운 리전 권장)

## 🔧 소스 데이터베이스 준비

### 1. 논리적 복제 활성화

논리적 복제를 위해 `wal_level`을 `logical`로 변경해야 합니다.

```sql
-- 현재 설정 확인
SHOW wal_level;
```

**AWS RDS에서 논리적 복제 활성화:**

1. **Parameter Group 수정**
   - RDS 콘솔 → Configuration → Parameter Groups
   - `rds.logical_replication` 파라미터를 `1`로 설정
   - 변경사항 저장

2. **인스턴스에 Parameter Group 적용**
   - RDS 인스턴스 → Modify
   - 새 Parameter Group 선택
   - Apply immediately 체크
   - 인스턴스 재부팅

3. **설정 확인**
```sql
SHOW wal_level;
-- 결과: logical
```

### 2. Neon 접속 허용 설정

**Security Group 인바운드 규칙 추가:**

Neon의 NAT Gateway IP 주소를 허용해야 합니다. 지역별 IP 주소는 [Neon 문서](https://neon.com/docs/introduction/regions#nat-gateway-ip-addresses)에서 확인 가능합니다.

```bash
# 예시: us-east-1 리전의 Neon IP 주소들
# 3.208.72.0/25
# 3.209.79.128/25
# 3.211.241.0/25
```

**Security Group 설정:**
1. RDS 인스턴스의 Security Group 클릭
2. Inbound rules → Edit inbound rules
3. PostgreSQL 포트(5432)에 대해 Neon IP 대역 추가
4. Save rules

### 3. Publication 생성

복제할 테이블을 정의하는 Publication을 생성합니다.

```sql
-- 특정 테이블만 복제하는 경우
CREATE PUBLICATION neon_migration_pub FOR TABLE users, orders, products;

-- 모든 테이블을 복제하는 경우 (권장하지 않음)
CREATE PUBLICATION neon_migration_pub FOR ALL TABLES;

-- Publication 확인
SELECT * FROM pg_publication;
```

**테이블별 Publication 권장 이유:**
- 세밀한 제어 가능
- 나중에 테이블 추가/제거 가능
- 마이그레이션 속도 조절 가능

## 🎯 목적지 데이터베이스 준비

### 1. 스키마 복사

논리적 복제는 **데이터만 복제**하므로, 스키마를 미리 준비해야 합니다.

```bash
# 소스 DB에서 스키마만 덤프
pg_dump -h your-rds-endpoint.amazonaws.com \
        -U postgres \
        -d your_database \
        --schema-only \
        --no-owner \
        --no-privileges \
        -f schema_dump.sql

# Neon에 스키마 복원
psql postgresql://username:password@ep-xxx.region.neon.tech/dbname \
     -f schema_dump.sql
```

### 2. 초기 데이터 동기화 (선택사항)

큰 데이터베이스의 경우 초기 데이터를 먼저 복사하는 것이 효율적입니다.

```bash
# 데이터만 덤프 (논리적 복제 시작 전)
pg_dump -h your-rds-endpoint.amazonaws.com \
        -U postgres \
        -d your_database \
        --data-only \
        --no-owner \
        --no-privileges \
        -f data_dump.sql

# Neon에 데이터 복원
psql postgresql://username:password@ep-xxx.region.neon.tech/dbname \
     -f data_dump.sql
```

### 3. Subscription 생성

Neon에서 AWS RDS의 Publication을 구독합니다.

```sql
-- Subscription 생성
CREATE SUBSCRIPTION neon_migration_sub 
CONNECTION 'postgresql://postgres:password@your-rds-endpoint.amazonaws.com:5432/your_database' 
PUBLICATION neon_migration_pub;

-- Subscription 상태 확인
SELECT * FROM pg_stat_subscription;
```

**연결 문자열 구성 요소:**
- `postgresql://`: 프로토콜
- `username:password`: AWS RDS 자격증명
- `host:port`: RDS 엔드포인트와 포트
- `database`: 데이터베이스 이름

## 🔄 복제 테스트 및 모니터링

### 1. 복제 상태 확인

```sql
-- Subscription 상태 조회
SELECT 
    subname,
    pid,
    received_lsn,
    latest_end_lsn,
    last_msg_send_time,
    last_msg_receipt_time
FROM pg_stat_subscription;
```

### 2. 실시간 테스트

**소스 DB에서 테스트 데이터 삽입:**
```sql
-- 테스트 테이블 생성 (이미 있다면 스키마에 포함됨)
CREATE TABLE IF NOT EXISTS test_replication (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 테스트 데이터 삽입
INSERT INTO test_replication (message) 
VALUES ('Migration test ' || NOW());
```

**목적지 DB에서 확인:**
```sql
-- 복제된 데이터 확인
SELECT * FROM test_replication ORDER BY created_at DESC LIMIT 5;

-- 레코드 수 비교
SELECT COUNT(*) FROM test_replication;
```

### 3. 지연시간 모니터링

```sql
-- 복제 지연시간 확인 (소스 DB에서 실행)
SELECT 
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    write_lag,
    flush_lag,
    replay_lag
FROM pg_stat_replication;
```

## 🔄 Sequential ID 동기화

논리적 복제에서는 **SERIAL/SEQUENCE 값이 자동으로 동기화되지 않습니다**. 마이그레이션 완료 후 다음 SQL을 실행하여 시퀀스를 동기화해야 합니다.

```sql
-- 모든 시퀀스의 현재 값을 테이블의 최대값으로 동기화
DO $$
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT 
            c.relname as seq_name,
            t.relname as tbl_name,
            a.attname as col_name
        FROM pg_class c
        JOIN pg_depend d ON d.objid = c.oid
        JOIN pg_class t ON d.refobjid = t.oid
        JOIN pg_attribute a ON t.oid = a.attrelid AND a.attnum = d.refobjsubid
        WHERE c.relkind = 'S'
    LOOP
        EXECUTE format(
            'SELECT setval(''%I'', COALESCE((SELECT MAX(%I) FROM %I), 1), true);',
            rec.seq_name,
            rec.col_name,
            rec.tbl_name
        );
        
        RAISE NOTICE '시퀀스 %이 테이블 %의 컬럼 %에 맞춰 동기화되었습니다.', 
                     rec.seq_name, rec.tbl_name, rec.col_name;
    END LOOP;
END$$;
```

**시퀀스 동기화 과정 설명:**
1. 시스템 카탈로그에서 모든 시퀀스와 연관 테이블 조회
2. 각 테이블의 해당 컬럼 최대값 확인
3. `setval()` 함수로 시퀀스 현재값 설정
4. 다음 INSERT 시 올바른 ID 할당 보장

### 수동 시퀀스 확인 및 조정

```sql
-- 특정 시퀀스 현재값 확인
SELECT currval('users_id_seq');

-- 특정 테이블의 최대 ID 확인
SELECT MAX(id) FROM users;

-- 수동으로 시퀀스 값 설정
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users), true);
```

## 🚀 애플리케이션 전환

### 1. 연결 문자열 준비

```python
# 기존 AWS RDS 연결
OLD_DATABASE_URL = "postgresql://user:pass@rds-endpoint.amazonaws.com:5432/dbname"

# 새로운 Neon 연결
NEW_DATABASE_URL = "postgresql://user:pass@ep-xxx.region.neon.tech/dbname"
```

### 2. 점진적 전환 전략

**Blue-Green 배포 방식:**
```python
import os
from datetime import datetime

class DatabaseRouter:
    def __init__(self):
        self.cutover_time = datetime(2025, 7, 29, 15, 0, 0)  # 전환 시간
        
    def get_database_url(self):
        if datetime.now() >= self.cutover_time:
            return os.getenv('NEON_DATABASE_URL')
        else:
            return os.getenv('RDS_DATABASE_URL')
```

### 3. 전환 체크리스트

- [ ] 복제 지연시간이 안정적인지 확인
- [ ] 시퀀스 동기화 완료
- [ ] 애플리케이션 연결 테스트
- [ ] 백업 및 롤백 계획 수립
- [ ] 모니터링 설정 완료

## 🔍 마이그레이션 완료 후 작업

### 1. 복제 정리

마이그레이션이 완료되면 복제 설정을 정리합니다:

```sql
-- Neon에서 Subscription 제거
DROP SUBSCRIPTION IF EXISTS neon_migration_sub;

-- AWS RDS에서 Publication 제거
DROP PUBLICATION IF EXISTS neon_migration_pub;
```

### 2. 성능 최적화

```sql
-- 통계 정보 업데이트
ANALYZE;

-- 인덱스 재구축 (필요한 경우)
REINDEX DATABASE your_database;

-- Vacuum 실행
VACUUM ANALYZE;
```

### 3. Neon 특화 기능 활용

**브랜치 생성:**
```bash
# Neon CLI로 개발용 브랜치 생성
neon branches create --name=dev-branch
neon branches create --name=staging-branch
```

**자동 스케일링 설정:**
- Neon Console에서 Compute settings 조정
- 최소/최대 CPU 및 메모리 설정
- Auto-pause 시간 설정

## 🚨 주의사항 및 트러블슈팅

### 일반적인 문제들

**1. 복제 지연 문제**
```sql
-- 지연 원인 확인
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables 
ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC;
```

**2. 연결 문제**
- Security Group 설정 재확인
- Neon IP 대역 업데이트 확인
- 방화벽 설정 점검

**3. 권한 문제**
```sql
-- Publication 권한 확인
SELECT * FROM pg_publication_tables;

-- Subscription 상태 확인
SELECT * FROM pg_subscription;
```

### 롤백 계획

1. **애플리케이션을 RDS로 되돌리기**
2. **Subscription 일시 정지**
3. **데이터 정합성 검증**
4. **필요시 역방향 복제 설정**

## 📊 마이그레이션 성과 측정

### 비용 비교
```
AWS RDS (db.t3.medium, 24/7)
- 인스턴스: $65/월
- 스토리지: $23/월 (100GB)
- 백업: $5/월
합계: $93/월

Neon (동일 워크로드)
- Compute: $19/월 (auto-pause 적용)
- 스토리지: $15/월 (압축 적용)
- 브랜치: 무료
합계: $34/월 (약 63% 절약)
```

### 성능 개선사항
- **시작 시간**: 즉시 (vs RDS 수분)
- **브랜치 생성**: 초 단위 (vs RDS 백업/복원 시간)
- **스케일링**: 자동 (vs 수동 인스턴스 크기 조정)

## 🎉 결론

AWS RDS에서 Neon으로의 마이그레이션은 **논리적 복제**를 활용하면 **무중단으로 안전하게** 진행할 수 있습니다. Neon의 **서버리스 아키텍처**, **브랜치 기능**, **비용 효율성**은 현대적인 애플리케이션 개발에 많은 이점을 제공합니다.

**핵심 성공 요소:**
- 철저한 사전 계획 및 테스트
- 시퀀스 동기화 잊지 않기
- 점진적 전환 전략 수립
- 충분한 모니터링 및 롤백 계획

Neon의 혁신적인 기능들을 활용하여 더 효율적이고 유연한 데이터베이스 환경을 구축해보세요! 🚀

---

**참고 자료:**
- [Neon 공식 마이그레이션 가이드](https://neon.com/docs/guides/logical-replication-rds-to-neon)
- [PostgreSQL 논리적 복제 문서](https://www.postgresql.org/docs/current/logical-replication.html)
- [AWS RDS 파라미터 그룹 설정](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.html)
