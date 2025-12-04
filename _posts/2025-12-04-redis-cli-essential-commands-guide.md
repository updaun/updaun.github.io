---
layout: post
title: "Redis CLI 필수 명령어 완벽 가이드 - 개발자가 가장 많이 사용하는 순서대로"
categories: [Database, Cache]
tags: [redis, redis-cli, cache, nosql, database, commands, tutorial, backend]
date: 2025-12-04 09:00:00 +0900
---

## 1. Redis CLI 시작하기 - 연결 및 기본 명령어

### 1.1 Redis 서버 연결

Redis CLI는 Redis 서버와 상호작용하는 가장 기본적인 도구입니다. 개발, 디버깅, 모니터링에 필수적입니다.

```bash
# ============================================
# 기본 연결 (로컬 서버, 포트 6379)
# ============================================
redis-cli

# 출력:
# 127.0.0.1:6379>


# ============================================
# 원격 서버 연결
# ============================================
redis-cli -h hostname -p port

# 예시: 프로덕션 서버 연결
redis-cli -h redis.example.com -p 6379

# AWS ElastiCache 연결
redis-cli -h my-cluster.abc123.0001.use1.cache.amazonaws.com -p 6379


# ============================================
# 비밀번호 인증
# ============================================
redis-cli -h hostname -p port -a password

# 또는 연결 후 인증
redis-cli
127.0.0.1:6379> AUTH your_password
OK


# ============================================
# 특정 데이터베이스 선택 (0-15)
# ============================================
redis-cli -n 2  # DB 2번 선택

# 또는 연결 후 선택
127.0.0.1:6379> SELECT 2
OK
127.0.0.1:6379[2]>  # [2]는 현재 DB 번호


# ============================================
# 원라인 명령 실행 (스크립트용)
# ============================================
redis-cli GET mykey

redis-cli -h remote.server.com GET user:1000

# 여러 명령어 파이프라인
echo -e "SET key1 value1\nGET key1" | redis-cli


# ============================================
# 연결 테스트
# ============================================
redis-cli ping
# PONG (연결 성공)

redis-cli --latency
# 지연 시간 실시간 모니터링
# min: 0, max: 1, avg: 0.08 (427 samples)
```

**연결 옵션 상세:**

```bash
# 주요 옵션 정리
-h <hostname>      # 호스트 지정 (기본값: 127.0.0.1)
-p <port>          # 포트 지정 (기본값: 6379)
-a <password>      # 비밀번호 인증
-n <db>            # 데이터베이스 번호 (0-15)
-u <uri>           # Redis URI 형식
--raw              # Raw 출력 (파싱 없이)
--csv              # CSV 형식 출력
--latency          # 지연 시간 측정
--stat             # 서버 통계 실시간 출력
--bigkeys          # 큰 키 찾기
--scan             # SCAN 모드

# URI 형식 연결 예시
redis-cli -u redis://user:password@hostname:port/db

# 실전 예시: 비밀번호 있는 원격 서버의 3번 DB
redis-cli -h prod-redis.company.com -p 6379 -a "MyS3cr3tP@ss" -n 3
```

### 1.2 가장 기본적인 명령어

```bash
# ============================================
# PING - 연결 확인
# ============================================
127.0.0.1:6379> PING
PONG

127.0.0.1:6379> PING "Hello"
"Hello"

# 용도: Health check, 연결 유지 확인


# ============================================
# ECHO - 메시지 출력 (디버깅용)
# ============================================
127.0.0.1:6379> ECHO "Hello Redis"
"Hello Redis"


# ============================================
# SELECT - 데이터베이스 전환
# ============================================
127.0.0.1:6379> SELECT 1
OK
127.0.0.1:6379[1]> SELECT 0
OK
127.0.0.1:6379>

# Redis는 기본적으로 16개 DB (0-15) 제공
# 주의: 프로덕션에서는 DB 분리보다 클러스터 권장


# ============================================
# QUIT - 연결 종료
# ============================================
127.0.0.1:6379> QUIT
# 또는 Ctrl+D


# ============================================
# INFO - 서버 정보 확인
# ============================================
127.0.0.1:6379> INFO
# Server
redis_version:7.2.3
redis_mode:standalone
os:Linux 5.15.0-91-generic x86_64
...

# 특정 섹션만 보기
127.0.0.1:6379> INFO stats
# Stats
total_connections_received:1523
total_commands_processed:45231
...

127.0.0.1:6379> INFO memory
# Memory
used_memory:1048576
used_memory_human:1.00M
...

# 주요 섹션:
# - server: 서버 정보
# - clients: 클라이언트 연결 정보
# - memory: 메모리 사용량
# - stats: 통계
# - replication: 복제 정보
# - cpu: CPU 사용량
# - keyspace: 키 통계
```

---

## 2. String 명령어 - 가장 많이 사용하는 기본 데이터 타입

String은 Redis에서 가장 기본적이고 널리 사용되는 데이터 타입입니다. 텍스트, 숫자, 직렬화된 JSON, 바이너리 데이터 등을 저장할 수 있습니다.

### 2.1 SET/GET - 기본 저장 및 조회

```bash
# ============================================
# SET - 키-값 저장
# ============================================
127.0.0.1:6379> SET mykey "Hello World"
OK

127.0.0.1:6379> SET user:1000:name "John Doe"
OK

# 숫자 저장
127.0.0.1:6379> SET counter 100
OK

# JSON 저장 (문자열로 직렬화)
127.0.0.1:6379> SET user:1000 '{"name":"John","age":30}'
OK


# ============================================
# GET - 값 조회
# ============================================
127.0.0.1:6379> GET mykey
"Hello World"

127.0.0.1:6379> GET user:1000:name
"John Doe"

127.0.0.1:6379> GET nonexistent
(nil)  # 키가 없으면 nil 반환


# ============================================
# SET 옵션들 - 조건부 저장
# ============================================

# NX: 키가 없을 때만 저장 (Not eXists)
127.0.0.1:6379> SET mykey "value1" NX
OK
127.0.0.1:6379> SET mykey "value2" NX
(nil)  # 이미 존재하므로 실패

# 용도: 분산 락, 중복 방지


# XX: 키가 이미 있을 때만 저장 (eXists)
127.0.0.1:6379> SET newkey "value" XX
(nil)  # 키가 없으므로 실패
127.0.0.1:6379> SET mykey "updated" XX
OK  # 키가 있으므로 성공

# 용도: 기존 값 업데이트만 허용


# EX: 만료 시간 (초 단위)
127.0.0.1:6379> SET session:abc123 "user_data" EX 3600
OK  # 1시간 후 자동 삭제

# 용도: 세션, 캐시


# PX: 만료 시간 (밀리초 단위)
127.0.0.1:6379> SET token:xyz "auth_token" PX 5000
OK  # 5초 후 삭제


# EXAT: Unix 타임스탬프로 만료 시간 지정 (초)
127.0.0.1:6379> SET event:reminder "Meeting at 3PM" EXAT 1733320800
OK  # 2025-12-04 15:00:00에 만료


# PXAT: Unix 타임스탬프로 만료 시간 지정 (밀리초)
127.0.0.1:6379> SET flash:msg "Welcome!" PXAT 1733320800000
OK


# KEEPTTL: 기존 TTL 유지하면서 값만 업데이트
127.0.0.1:6379> SET mykey "value1" EX 100
OK
127.0.0.1:6379> SET mykey "value2" KEEPTTL
OK  # TTL은 그대로, 값만 변경


# GET: 이전 값 반환하며 새 값 설정 (원자적 swap)
127.0.0.1:6379> SET mykey "old_value"
OK
127.0.0.1:6379> SET mykey "new_value" GET
"old_value"  # 이전 값 반환
127.0.0.1:6379> GET mykey
"new_value"


# ============================================
# 복합 옵션 사용
# ============================================

# 분산 락 구현 (NX + EX)
127.0.0.1:6379> SET lock:resource:123 "worker-1" NX EX 30
OK  # 30초 동안 락 획득

127.0.0.1:6379> SET lock:resource:123 "worker-2" NX EX 30
(nil)  # 다른 워커는 락 획득 실패


# 캐시 업데이트 (XX + EX)
127.0.0.1:6379> SET cache:user:1000 '{"name":"John"}' XX EX 600
OK  # 이미 있는 캐시만 갱신


# 세션 갱신 (KEEPTTL + GET)
127.0.0.1:6379> SET session:abc '{"user_id":1000}' EX 1800
OK
127.0.0.1:6379> SET session:abc '{"user_id":1000,"last_active":"now"}' KEEPTTL GET
'{"user_id":1000}'
```

### 2.2 MGET/MSET - 다중 키 작업

```bash
# ============================================
# MSET - 여러 키를 한 번에 저장 (원자적)
# ============================================
127.0.0.1:6379> MSET key1 "value1" key2 "value2" key3 "value3"
OK

# 실전 예시: 사용자 정보 일괄 저장
127.0.0.1:6379> MSET \
  user:1000:name "John" \
  user:1000:email "john@example.com" \
  user:1000:age "30"
OK


# ============================================
# MGET - 여러 키를 한 번에 조회
# ============================================
127.0.0.1:6379> MGET key1 key2 key3
1) "value1"
2) "value2"
3) "value3"

# 존재하지 않는 키는 nil
127.0.0.1:6379> MGET key1 nonexistent key3
1) "value1"
2) (nil)
3) "value3"

# 실전 예시: 사용자 정보 일괄 조회
127.0.0.1:6379> MGET user:1000:name user:1000:email user:1000:age
1) "John"
2) "john@example.com"
3) "30"


# ============================================
# MSETNX - 모든 키가 없을 때만 저장 (원자적)
# ============================================
127.0.0.1:6379> MSETNX key4 "value4" key5 "value5"
(integer) 1  # 성공

127.0.0.1:6379> MSETNX key4 "new4" key6 "value6"
(integer) 0  # key4가 이미 있어서 전체 실패 (key6도 저장 안됨)

# 용도: 여러 리소스에 대한 원자적 락 획득
```

**성능 비교:**

```bash
# ❌ 비효율적: 개별 GET (3번 네트워크 왕복)
GET user:1000:name
GET user:1000:email  
GET user:1000:age

# ✅ 효율적: MGET (1번 네트워크 왕복)
MGET user:1000:name user:1000:email user:1000:age

# 지연 시간 차이:
# 개별 GET: 3ms × 3 = 9ms
# MGET: 3ms × 1 = 3ms (3배 빠름!)
```

### 2.3 INCR/DECR - 카운터 연산

```bash
# ============================================
# INCR - 1씩 증가 (원자적)
# ============================================
127.0.0.1:6379> SET counter 10
OK
127.0.0.1:6379> INCR counter
(integer) 11
127.0.0.1:6379> INCR counter
(integer) 12

# 키가 없으면 0에서 시작
127.0.0.1:6379> INCR new_counter
(integer) 1


# ============================================
# DECR - 1씩 감소 (원자적)
# ============================================
127.0.0.1:6379> SET inventory 100
OK
127.0.0.1:6379> DECR inventory
(integer) 99
127.0.0.1:6379> DECR inventory
(integer) 98


# ============================================
# INCRBY - 지정한 값만큼 증가
# ============================================
127.0.0.1:6379> SET points 50
OK
127.0.0.1:6379> INCRBY points 10
(integer) 60
127.0.0.1:6379> INCRBY points 25
(integer) 85

# 음수로 감소도 가능
127.0.0.1:6379> INCRBY points -5
(integer) 80


# ============================================
# DECRBY - 지정한 값만큼 감소
# ============================================
127.0.0.1:6379> SET balance 1000
OK
127.0.0.1:6379> DECRBY balance 150
(integer) 850
127.0.0.1:6379> DECRBY balance 50
(integer) 800


# ============================================
# INCRBYFLOAT - 실수 증가
# ============================================
127.0.0.1:6379> SET price 19.99
OK
127.0.0.1:6379> INCRBYFLOAT price 5.00
"24.99"
127.0.0.1:6379> INCRBYFLOAT price -2.50
"22.49"

# 과학적 표기법 지원
127.0.0.1:6379> INCRBYFLOAT price 1.5e2
"172.49"


# ============================================
# 실전 활용 예시
# ============================================

# 페이지 뷰 카운터
127.0.0.1:6379> INCR page:views:/home
(integer) 1523

# 좋아요 수
127.0.0.1:6379> INCR post:1000:likes
(integer) 42

# 재고 감소 (동시성 안전)
127.0.0.1:6379> DECR product:sku123:stock
(integer) 15

# API 요청 제한 (Rate Limiting)
127.0.0.1:6379> SET rate:user:1000 0 EX 60
OK
127.0.0.1:6379> INCR rate:user:1000
(integer) 1
127.0.0.1:6379> INCR rate:user:1000
(integer) 2
# ... 60초 후 자동 리셋

# 분산 ID 생성기
127.0.0.1:6379> INCR global:user:id
(integer) 100001
127.0.0.1:6379> INCR global:user:id
(integer) 100002


# ============================================
# 에러 케이스
# ============================================

# 문자열에 INCR 시도
127.0.0.1:6379> SET mykey "hello"
OK
127.0.0.1:6379> INCR mykey
(error) ERR value is not an integer or out of range

# 정수 범위 초과
127.0.0.1:6379> SET bignum 9223372036854775807
OK  # 64bit 최댓값
127.0.0.1:6379> INCR bignum
(error) ERR increment or decrement would overflow
```

### 2.4 APPEND/STRLEN - 문자열 조작

```bash
# ============================================
# APPEND - 문자열 끝에 추가
# ============================================
127.0.0.1:6379> SET greeting "Hello"
OK
127.0.0.1:6379> APPEND greeting " World"
(integer) 11  # 새로운 길이 반환
127.0.0.1:6379> GET greeting
"Hello World"

# 키가 없으면 SET과 동일
127.0.0.1:6379> APPEND newkey "First"
(integer) 5
127.0.0.1:6379> GET newkey
"First"

# 로그 수집 예시
127.0.0.1:6379> APPEND log:2025-12-04 "10:00 User logged in\n"
(integer) 21
127.0.0.1:6379> APPEND log:2025-12-04 "10:05 User clicked button\n"
(integer) 48


# ============================================
# STRLEN - 문자열 길이
# ============================================
127.0.0.1:6379> SET message "Hello Redis"
OK
127.0.0.1:6379> STRLEN message
(integer) 11

127.0.0.1:6379> STRLEN nonexistent
(integer) 0

# UTF-8 바이트 길이 (문자 수 아님!)
127.0.0.1:6379> SET korean "안녕하세요"
OK
127.0.0.1:6379> STRLEN korean
(integer) 15  # 5글자 × 3바이트 = 15


# ============================================
# GETRANGE - 부분 문자열 추출
# ============================================
127.0.0.1:6379> SET message "Hello Redis World"
OK

# 인덱스 0부터 시작
127.0.0.1:6379> GETRANGE message 0 4
"Hello"

127.0.0.1:6379> GETRANGE message 6 10
"Redis"

# 음수 인덱스 (끝에서부터)
127.0.0.1:6379> GETRANGE message -5 -1
"World"

# 전체 문자열
127.0.0.1:6379> GETRANGE message 0 -1
"Hello Redis World"


# ============================================
# SETRANGE - 특정 위치부터 덮어쓰기
# ============================================
127.0.0.1:6379> SET message "Hello Redis"
OK
127.0.0.1:6379> SETRANGE message 6 "World"
(integer) 11  # 새 길이
127.0.0.1:6379> GET message
"Hello World"

# 빈 공간은 null 바이트로 채움
127.0.0.1:6379> SETRANGE message 20 "!"
(integer) 21
127.0.0.1:6379> GET message
"Hello World\x00\x00\x00\x00\x00\x00\x00\x00\x00!"
```

### 2.5 GETDEL/GETEX - 조회와 동시에 삭제/만료

```bash
# ============================================
# GETDEL - 값 조회 후 즉시 삭제 (원자적)
# ============================================
127.0.0.1:6379> SET temp_token "abc123"
OK
127.0.0.1:6379> GETDEL temp_token
"abc123"
127.0.0.1:6379> GET temp_token
(nil)  # 이미 삭제됨

# 용도: 일회용 토큰, 임시 데이터


# ============================================
# GETEX - 값 조회하면서 만료 시간 설정/갱신
# ============================================

# EX: 초 단위 만료
127.0.0.1:6379> SET mykey "value"
OK
127.0.0.1:6379> GETEX mykey EX 60
"value"  # 60초 후 만료 설정됨

# PX: 밀리초 단위 만료
127.0.0.1:6379> GETEX mykey PX 5000
"value"  # 5초 후 만료

# EXAT: Unix 타임스탬프 (초)
127.0.0.1:6379> GETEX mykey EXAT 1733320800
"value"

# PXAT: Unix 타임스탬프 (밀리초)
127.0.0.1:6379> GETEX mykey PXAT 1733320800000
"value"

# PERSIST: 만료 시간 제거
127.0.0.1:6379> GETEX mykey PERSIST
"value"  # 영구 보관

# 용도: 캐시 조회하면서 TTL 갱신 (LRU 구현)
```

---

## 3. 키 관리 명령어 - 필수 유틸리티

### 3.1 EXISTS/DEL - 키 존재 확인 및 삭제

```bash
# ============================================
# EXISTS - 키 존재 여부 확인
# ============================================
127.0.0.1:6379> SET mykey "value"
OK
127.0.0.1:6379> EXISTS mykey
(integer) 1  # 존재함

127.0.0.1:6379> EXISTS nonexistent
(integer) 0  # 없음

# 여러 키 확인 (존재하는 키 개수 반환)
127.0.0.1:6379> EXISTS key1 key2 key3
(integer) 2  # 3개 중 2개 존재

# 실전 활용
if EXISTS user:session:abc123
  # 세션 유효
else
  # 로그인 필요
end


# ============================================
# DEL - 키 삭제
# ============================================
127.0.0.1:6379> SET temp "temporary"
OK
127.0.0.1:6379> DEL temp
(integer) 1  # 삭제된 키 개수

127.0.0.1:6379> DEL nonexistent
(integer) 0  # 없는 키는 0 반환

# 여러 키 동시 삭제
127.0.0.1:6379> DEL key1 key2 key3
(integer) 3

# 패턴 삭제는 SCAN + DEL 조합 (안전)
127.0.0.1:6379> SCAN 0 MATCH temp:* COUNT 100
# 결과에서 키들을 DEL로 삭제

# ⚠️ KEYS로 패턴 삭제는 프로덕션에서 금지!
# KEYS temp:*  # 전체 DB 블로킹됨!


# ============================================
# UNLINK - 비동기 삭제 (권장)
# ============================================
127.0.0.1:6379> SET bigkey "very large value..."
OK
127.0.0.1:6379> UNLINK bigkey
(integer) 1  # 백그라운드에서 삭제

# DEL vs UNLINK:
# DEL: 즉시 삭제 (큰 키는 블로킹)
# UNLINK: 백그라운드 삭제 (논블로킹, 권장)

# 큰 List/Set/Hash 삭제 시 UNLINK 사용
127.0.0.1:6379> LPUSH biglist 1 2 3 ... 100000
127.0.0.1:6379> UNLINK biglist  # 안전한 삭제
```

### 3.2 KEYS/SCAN - 키 검색

```bash
# ============================================
# KEYS - 패턴 매칭으로 키 검색 (⚠️ 프로덕션 금지!)
# ============================================
127.0.0.1:6379> KEYS *
1) "user:1000"
2) "user:1001"
3) "session:abc"
...

# 패턴 사용
127.0.0.1:6379> KEYS user:*
1) "user:1000"
2) "user:1001"

127.0.0.1:6379> KEYS session:???
1) "session:abc"
2) "session:xyz"

127.0.0.1:6379> KEYS user:[12]*
1) "user:1000"
2) "user:2000"

# ⚠️ 위험: KEYS는 전체 DB를 스캔 → 블로킹!
# 프로덕션에서는 절대 사용 금지!
# 개발/디버깅 환경에서만 사용


# ============================================
# SCAN - 안전한 키 검색 (프로덕션용)
# ============================================

# 기본 사용법: SCAN cursor [MATCH pattern] [COUNT count]
127.0.0.1:6379> SCAN 0
1) "17"     # 다음 커서 (0이면 끝)
2) 1) "key:1"
   2) "key:2"
   3) "key:3"
   ...

127.0.0.1:6379> SCAN 17
1) "0"      # 0이면 모든 키 스캔 완료
2) 1) "key:10"
   2) "key:11"
   ...

# MATCH: 패턴 필터링
127.0.0.1:6379> SCAN 0 MATCH user:* COUNT 100
1) "20"
2) 1) "user:1000"
   2) "user:1001"
   3) "user:1002"

# COUNT: 한 번에 가져올 키 개수 힌트 (정확하지 않음)
127.0.0.1:6379> SCAN 0 COUNT 1000
# 약 1000개씩 가져오기 시도

# TYPE: 특정 타입만 필터 (Redis 6.0+)
127.0.0.1:6379> SCAN 0 MATCH * TYPE string
1) "15"
2) 1) "key1"
   2) "key2"


# ============================================
# SCAN 전체 순회 패턴
# ============================================

# Bash 스크립트 예시
redis-cli --scan --pattern 'user:*' | while read key; do
  echo "Processing $key"
  redis-cli GET "$key"
done

# Python 예시
import redis
r = redis.Redis()

cursor = 0
while True:
    cursor, keys = r.scan(cursor, match='user:*', count=100)
    for key in keys:
        print(f"Processing {key}")
    if cursor == 0:
        break


# ============================================
# KEYS vs SCAN 비교
# ============================================

KEYS pattern:
  장점: 간단, 모든 키 한 번에 반환
  단점: ⚠️ 전체 DB 블로킹, O(N) 시간복잡도
  용도: 개발/디버깅 환경

SCAN cursor:
  장점: 논블로킹, 점진적 순회
  단점: 구현 복잡, 중복 가능성
  용도: 프로덕션 환경
```

### 3.3 TTL/EXPIRE - 만료 시간 관리

```bash
# ============================================
# EXPIRE - 만료 시간 설정 (초)
# ============================================
127.0.0.1:6379> SET session:abc "data"
OK
127.0.0.1:6379> EXPIRE session:abc 3600
(integer) 1  # 성공 (1시간 후 삭제)

127.0.0.1:6379> EXPIRE nonexistent 60
(integer) 0  # 키가 없으면 실패


# ============================================
# PEXPIRE - 만료 시간 설정 (밀리초)
# ============================================
127.0.0.1:6379> SET temp "data"
OK
127.0.0.1:6379> PEXPIRE temp 5000
(integer) 1  # 5초 후 삭제


# ============================================
# EXPIREAT - 특정 시각에 만료 (Unix timestamp, 초)
# ============================================
127.0.0.1:6379> SET event "reminder"
OK
127.0.0.1:6379> EXPIREAT event 1733320800
(integer) 1  # 2025-12-04 15:00:00에 삭제


# ============================================
# PEXPIREAT - 특정 시각에 만료 (밀리초)
# ============================================
127.0.0.1:6379> PEXPIREAT event 1733320800000
(integer) 1


# ============================================
# TTL - 남은 만료 시간 확인 (초)
# ============================================
127.0.0.1:6379> SET mykey "value" EX 100
OK
127.0.0.1:6379> TTL mykey
(integer) 97  # 97초 남음

127.0.0.1:6379> TTL nonexistent
(integer) -2  # 키가 없음

127.0.0.1:6379> SET permanent "forever"
OK
127.0.0.1:6379> TTL permanent
(integer) -1  # 만료 시간 없음 (영구)


# ============================================
# PTTL - 남은 만료 시간 확인 (밀리초)
# ============================================
127.0.0.1:6379> PTTL mykey
(integer) 95847  # 밀리초 단위


# ============================================
# PERSIST - 만료 시간 제거 (영구 보관)
# ============================================
127.0.0.1:6379> SET mykey "value" EX 100
OK
127.0.0.1:6379> TTL mykey
(integer) 97
127.0.0.1:6379> PERSIST mykey
(integer) 1  # 성공
127.0.0.1:6379> TTL mykey
(integer) -1  # 이제 영구 보관


# ============================================
# EXPIRETIME - 만료 Unix timestamp 조회 (초, Redis 7.0+)
# ============================================
127.0.0.1:6379> SET mykey "value" EXAT 1733320800
OK
127.0.0.1:6379> EXPIRETIME mykey
(integer) 1733320800

127.0.0.1:6379> EXPIRETIME permanent
(integer) -1  # 만료 시간 없음


# ============================================
# PEXPIRETIME - 만료 timestamp 조회 (밀리초, Redis 7.0+)
# ============================================
127.0.0.1:6379> PEXPIRETIME mykey
(integer) 1733320800000


# ============================================
# 실전 활용 예시
# ============================================

# 세션 관리 (30분)
127.0.0.1:6379> SET session:user123 '{"user_id":1000}' EX 1800

# 세션 갱신 (활동 시마다)
127.0.0.1:6379> EXPIRE session:user123 1800

# 남은 시간 확인
127.0.0.1:6379> TTL session:user123
(integer) 1523


# OTP 코드 (5분)
127.0.0.1:6379> SET otp:user123 "123456" EX 300

# 캐시 (1시간)
127.0.0.1:6379> SET cache:product:1000 '{"name":"Widget"}' EX 3600

# Rate Limiting (1분마다 리셋)
127.0.0.1:6379> SET rate:api:user123 0 EX 60
127.0.0.1:6379> INCR rate:api:user123
```

### 3.4 RENAME/TYPE - 키 이름 변경 및 타입 확인

```bash
# ============================================
# RENAME - 키 이름 변경
# ============================================
127.0.0.1:6379> SET oldkey "value"
OK
127.0.0.1:6379> RENAME oldkey newkey
OK
127.0.0.1:6379> GET oldkey
(nil)
127.0.0.1:6379> GET newkey
"value"

# ⚠️ 대상 키가 이미 있으면 덮어씀!
127.0.0.1:6379> SET key1 "value1"
OK
127.0.0.1:6379> SET key2 "value2"
OK
127.0.0.1:6379> RENAME key1 key2
OK
127.0.0.1:6379> GET key2
"value1"  # key2의 기존 값이 사라짐


# ============================================
# RENAMENX - 대상 키가 없을 때만 변경
# ============================================
127.0.0.1:6379> SET source "data"
OK
127.0.0.1:6379> RENAMENX source destination
(integer) 1  # 성공

127.0.0.1:6379> SET key1 "value1"
OK
127.0.0.1:6379> SET key2 "value2"
OK
127.0.0.1:6379> RENAMENX key1 key2
(integer) 0  # key2가 이미 있어서 실패


# ============================================
# TYPE - 키의 데이터 타입 확인
# ============================================
127.0.0.1:6379> SET mystring "hello"
OK
127.0.0.1:6379> TYPE mystring
string

127.0.0.1:6379> LPUSH mylist 1 2 3
(integer) 3
127.0.0.1:6379> TYPE mylist
list

127.0.0.1:6379> SADD myset a b c
(integer) 3
127.0.0.1:6379> TYPE myset
set

127.0.0.1:6379> HSET myhash field value
(integer) 1
127.0.0.1:6379> TYPE myhash
hash

127.0.0.1:6379> ZADD myzset 1 member
(integer) 1
127.0.0.1:6379> TYPE myzset
zset

127.0.0.1:6379> TYPE nonexistent
none

# 가능한 반환값:
# - string
# - list
# - set
# - zset (sorted set)
# - hash
# - stream (Redis 5.0+)
# - none (키 없음)


# ============================================
# OBJECT ENCODING - 내부 인코딩 확인 (고급)
# ============================================
127.0.0.1:6379> SET smallint 123
OK
127.0.0.1:6379> OBJECT ENCODING smallint
"int"  # 정수로 인코딩

127.0.0.1:6379> SET longstring "very long string..."
OK
127.0.0.1:6379> OBJECT ENCODING longstring
"raw"  # 문자열로 인코딩

127.0.0.1:6379> LPUSH smalllist 1 2 3
(integer) 3
127.0.0.1:6379> OBJECT ENCODING smalllist
"ziplist"  # 작은 리스트는 ziplist로 최적화
```

### 3.5 DUMP/RESTORE - 키 직렬화 및 복원

```bash
# ============================================
# DUMP - 키를 직렬화 (바이너리 형식)
# ============================================
127.0.0.1:6379> SET mykey "Hello"
OK
127.0.0.1:6379> DUMP mykey
"\x00\x05Hello\t\x00\xaa\xbb\xcc..."  # 직렬화된 데이터

# 용도: 키 백업, 다른 Redis로 마이그레이션


# ============================================
# RESTORE - 직렬화된 데이터를 복원
# ============================================
127.0.0.1:6379> RESTORE newkey 0 "\x00\x05Hello\t\x00\xaa\xbb\xcc..."
OK
127.0.0.1:6379> GET newkey
"Hello"

# TTL 지정 (밀리초)
127.0.0.1:6379> RESTORE tempkey 5000 "\x00\x05Hello\t\x00\xaa\xbb\xcc..."
OK  # 5초 후 삭제

# REPLACE: 기존 키 덮어쓰기
127.0.0.1:6379> RESTORE newkey 0 "..." REPLACE
OK


# ============================================
# 키 복사 (DUMP + RESTORE)
# ============================================

# 같은 Redis 내에서 복사
127.0.0.1:6379> SET original "data"
OK
127.0.0.1:6379> DUMP original > /tmp/backup.rdb
127.0.0.1:6379> RESTORE copy 0 "$(cat /tmp/backup.rdb)"
OK

# 다른 Redis로 마이그레이션 (Bash)
SERIALIZED=$(redis-cli -h source.redis.com DUMP mykey)
redis-cli -h target.redis.com RESTORE mykey 0 "$SERIALIZED"


# ============================================
# COPY - 키 복사 (Redis 6.2+, 더 간단)
# ============================================
127.0.0.1:6379> SET source "value"
OK
127.0.0.1:6379> COPY source destination
(integer) 1  # 성공

# DB 간 복사
127.0.0.1:6379> COPY source destination DB 1
(integer) 1  # DB 1로 복사

# REPLACE: 대상 키 덮어쓰기
127.0.0.1:6379> COPY source destination REPLACE
(integer) 1
```

---

## 4. Hash 명령어 - 객체 저장에 최적

Hash는 필드-값 쌍의 컬렉션으로, 객체를 표현하기에 가장 적합한 데이터 구조입니다. 메모리 효율적이며 부분 업데이트가 가능합니다.

### 4.1 HSET/HGET - 해시 필드 저장 및 조회

```bash
# ============================================
# HSET - 해시 필드 설정
# ============================================

# 단일 필드
127.0.0.1:6379> HSET user:1000 name "John Doe"
(integer) 1  # 새 필드 생성

# 여러 필드 동시 설정
127.0.0.1:6379> HSET user:1000 email "john@example.com" age 30 city "Seoul"
(integer) 3  # 3개 필드 추가

# 기존 필드 업데이트
127.0.0.1:6379> HSET user:1000 age 31
(integer) 0  # 기존 필드 업데이트 (새 필드 아님)


# ============================================
# HGET - 해시 필드 조회
# ============================================
127.0.0.1:6379> HGET user:1000 name
"John Doe"

127.0.0.1:6379> HGET user:1000 email
"john@example.com"

127.0.0.1:6379> HGET user:1000 nonexistent
(nil)


# ============================================
# HMSET - 여러 필드 설정 (레거시, HSET 권장)
# ============================================
127.0.0.1:6379> HMSET user:1001 name "Jane" email "jane@example.com" age 28
OK

# HSET으로 대체 가능 (Redis 4.0+)
127.0.0.1:6379> HSET user:1001 name "Jane" email "jane@example.com" age 28
(integer) 3


# ============================================
# HMGET - 여러 필드 조회
# ============================================
127.0.0.1:6379> HMGET user:1000 name email age
1) "John Doe"
2) "john@example.com"
3) "30"

# 없는 필드는 nil
127.0.0.1:6379> HMGET user:1000 name nonexistent city
1) "John Doe"
2) (nil)
3) "Seoul"


# ============================================
# HGETALL - 모든 필드-값 조회
# ============================================
127.0.0.1:6379> HGETALL user:1000
1) "name"
2) "John Doe"
3) "email"
4) "john@example.com"
5) "age"
6) "30"
7) "city"
8) "Seoul"

# ⚠️ 주의: 필드가 많으면 느림! (수백 개 이하만 사용)


# ============================================
# HSETNX - 필드가 없을 때만 설정
# ============================================
127.0.0.1:6379> HSETNX user:1000 country "Korea"
(integer) 1  # 성공

127.0.0.1:6379> HSETNX user:1000 country "USA"
(integer) 0  # 이미 있어서 실패

# 용도: 초기값 설정, 중복 방지
```

### 4.2 HDEL/HEXISTS - 필드 삭제 및 존재 확인

```bash
# ============================================
# HDEL - 해시 필드 삭제
# ============================================
127.0.0.1:6379> HSET user:1000 temp "temporary"
(integer) 1
127.0.0.1:6379> HDEL user:1000 temp
(integer) 1  # 삭제된 필드 개수

# 여러 필드 동시 삭제
127.0.0.1:6379> HDEL user:1000 field1 field2 field3
(integer) 2  # 3개 중 2개만 존재했음

# 없는 필드 삭제
127.0.0.1:6379> HDEL user:1000 nonexistent
(integer) 0


# ============================================
# HEXISTS - 필드 존재 여부 확인
# ============================================
127.0.0.1:6379> HEXISTS user:1000 name
(integer) 1  # 존재

127.0.0.1:6379> HEXISTS user:1000 nonexistent
(integer) 0  # 없음

# 조건부 로직
if HEXISTS user:1000 email
  # 이메일 있음
else
  # 이메일 설정 필요
end
```

### 4.3 HKEYS/HVALS/HLEN - 해시 메타데이터

```bash
# ============================================
# HKEYS - 모든 필드명 조회
# ============================================
127.0.0.1:6379> HKEYS user:1000
1) "name"
2) "email"
3) "age"
4) "city"
5) "country"

# 용도: 동적 필드 처리, 스키마 검증


# ============================================
# HVALS - 모든 값 조회
# ============================================
127.0.0.1:6379> HVALS user:1000
1) "John Doe"
2) "john@example.com"
3) "30"
4) "Seoul"
5) "Korea"


# ============================================
# HLEN - 필드 개수
# ============================================
127.0.0.1:6379> HLEN user:1000
(integer) 5

127.0.0.1:6379> HLEN nonexistent
(integer) 0


# ============================================
# HSTRLEN - 필드 값의 길이 (Redis 3.2+)
# ============================================
127.0.0.1:6379> HSTRLEN user:1000 name
(integer) 8  # "John Doe" = 8글자

127.0.0.1:6379> HSTRLEN user:1000 nonexistent
(integer) 0
```

### 4.4 HINCRBY/HINCRBYFLOAT - 해시 필드 증감

```bash
# ============================================
# HINCRBY - 정수 필드 증가
# ============================================
127.0.0.1:6379> HSET product:1000 stock 100
(integer) 1
127.0.0.1:6379> HINCRBY product:1000 stock -1
(integer) 99  # 재고 감소

127.0.0.1:6379> HINCRBY product:1000 sold 1
(integer) 1  # 판매량 증가 (필드 없으면 0에서 시작)

# 음수로 감소
127.0.0.1:6379> HINCRBY product:1000 stock -5
(integer) 94


# ============================================
# HINCRBYFLOAT - 실수 필드 증가
# ============================================
127.0.0.1:6379> HSET product:1000 price 19.99
(integer) 1
127.0.0.1:6379> HINCRBYFLOAT product:1000 price 5.00
"24.99"

127.0.0.1:6379> HINCRBYFLOAT product:1000 price -2.50
"22.49"


# ============================================
# 실전 활용 예시
# ============================================

# 상품 관리
127.0.0.1:6379> HSET product:sku123 name "Widget" price 29.99 stock 50
(integer) 3

# 주문 시 재고 감소
127.0.0.1:6379> HINCRBY product:sku123 stock -1
(integer) 49

# 판매 통계
127.0.0.1:6379> HINCRBY product:sku123 total_sold 1
(integer) 1
127.0.0.1:6379> HINCRBYFLOAT product:sku123 revenue 29.99
"29.99"


# 사용자 통계
127.0.0.1:6379> HSET user:1000:stats posts 10 likes 50 followers 100
(integer) 3

# 새 게시물
127.0.0.1:6379> HINCRBY user:1000:stats posts 1
(integer) 11

# 좋아요 증가
127.0.0.1:6379> HINCRBY user:1000:stats likes 5
(integer) 55
```

### 4.5 HSCAN - 해시 필드 순회 (대용량)

```bash
# ============================================
# HSCAN - 해시 필드를 안전하게 순회
# ============================================

# 기본 사용법: HSCAN key cursor [MATCH pattern] [COUNT count]
127.0.0.1:6379> HSCAN user:1000 0
1) "0"      # 다음 커서 (0이면 끝)
2) 1) "name"
   2) "John Doe"
   3) "email"
   4) "john@example.com"
   5) "age"
   6) "30"

# MATCH: 패턴 필터링
127.0.0.1:6379> HSCAN user:1000 0 MATCH *name*
1) "0"
2) 1) "name"
   2) "John Doe"
   3) "username"
   4) "johndoe"

# COUNT: 한 번에 가져올 힌트
127.0.0.1:6379> HSCAN large:hash 0 COUNT 100

# 전체 순회 패턴 (Python)
cursor = 0
while True:
    cursor, fields = r.hscan('user:1000', cursor, count=100)
    for field, value in fields.items():
        print(f"{field}: {value}")
    if cursor == 0:
        break


# ============================================
# Hash vs String (JSON) 비교
# ============================================

# String 방식 (JSON)
127.0.0.1:6379> SET user:1000 '{"name":"John","email":"john@example.com","age":30}'
OK
127.0.0.1:6379> GET user:1000
'{"name":"John","email":"john@example.com","age":30}'

# ❌ 부분 업데이트 불가 (전체 읽기 → 수정 → 저장)
# ❌ 메모리 비효율적
# ✅ 복잡한 중첩 구조 가능


# Hash 방식
127.0.0.1:6379> HSET user:1000 name "John" email "john@example.com" age 30
(integer) 3

# ✅ 부분 업데이트 가능
127.0.0.1:6379> HSET user:1000 age 31
(integer) 0

# ✅ 메모리 효율적 (특히 작은 해시)
# ✅ 필드별 조회/수정 빠름
# ❌ 중첩 구조 불가 (평면 구조만)

권장:
  - 평면 객체 (사용자, 상품, 설정 등): Hash
  - 중첩 구조 (복잡한 JSON): String
  - 수백 개 이상 필드: String (Hash는 느려짐)
```

---

## 5. List 명령어 - 큐와 스택 구현

List는 순서가 있는 문자열 컬렉션으로, 큐(Queue), 스택(Stack), 타임라인 등을 구현하기에 적합합니다.

### 5.1 LPUSH/RPUSH/LPOP/RPOP - 리스트 기본 연산

```bash
# ============================================
# LPUSH - 리스트 왼쪽(앞)에 추가
# ============================================
127.0.0.1:6379> LPUSH mylist "first"
(integer) 1  # 리스트 길이

127.0.0.1:6379> LPUSH mylist "second"
(integer) 2

# 여러 요소 동시 추가 (오른쪽부터 순서대로)
127.0.0.1:6379> LPUSH mylist "third" "fourth"
(integer) 4

# 결과: ["fourth", "third", "second", "first"]


# ============================================
# RPUSH - 리스트 오른쪽(뒤)에 추가
# ============================================
127.0.0.1:6379> RPUSH queue "task1"
(integer) 1
127.0.0.1:6379> RPUSH queue "task2"
(integer) 2
127.0.0.1:6379> RPUSH queue "task3" "task4"
(integer) 4

# 결과: ["task1", "task2", "task3", "task4"]


# ============================================
# LPUSHX/RPUSHX - 리스트가 있을 때만 추가
# ============================================
127.0.0.1:6379> LPUSHX existing_list "value"
(integer) 0  # 리스트 없으면 실패

127.0.0.1:6379> LPUSH existing_list "first"
(integer) 1
127.0.0.1:6379> LPUSHX existing_list "second"
(integer) 2  # 성공


# ============================================
# LPOP - 리스트 왼쪽에서 제거하고 반환
# ============================================
127.0.0.1:6379> LPUSH stack 1 2 3
(integer) 3
127.0.0.1:6379> LPOP stack
"3"
127.0.0.1:6379> LPOP stack
"2"

# 여러 개 동시 제거 (Redis 6.2+)
127.0.0.1:6379> LPOP stack 2
1) "1"


# ============================================
# RPOP - 리스트 오른쪽에서 제거하고 반환
# ============================================
127.0.0.1:6379> RPUSH queue "task1" "task2" "task3"
(integer) 3
127.0.0.1:6379> RPOP queue
"task3"

# 여러 개 제거
127.0.0.1:6379> RPOP queue 2
1) "task2"
2) "task1"


# ============================================
# 자료구조 구현 패턴
# ============================================

# 스택 (LIFO - Last In First Out)
127.0.0.1:6379> LPUSH stack "A"
127.0.0.1:6379> LPUSH stack "B"
127.0.0.1:6379> LPUSH stack "C"
127.0.0.1:6379> LPOP stack
"C"  # 마지막 입력이 먼저 출력

# 큐 (FIFO - First In First Out)
127.0.0.1:6379> RPUSH queue "A"
127.0.0.1:6379> RPUSH queue "B"
127.0.0.1:6379> RPUSH queue "C"
127.0.0.1:6379> LPOP queue
"A"  # 첫 입력이 먼저 출력


# ============================================
# 실전 활용 예시
# ============================================

# 작업 큐 (Task Queue)
127.0.0.1:6379> RPUSH jobs:pending '{"job_id":1,"type":"email"}'
127.0.0.1:6379> RPUSH jobs:pending '{"job_id":2,"type":"report"}'
# Worker가 처리
127.0.0.1:6379> LPOP jobs:pending
'{"job_id":1,"type":"email"}'

# 최근 활동 로그 (최신 100개만 유지)
127.0.0.1:6379> LPUSH user:1000:activities "Logged in"
127.0.0.1:6379> LTRIM user:1000:activities 0 99
OK

# 실시간 채팅 메시지
127.0.0.1:6379> RPUSH chat:room123 "User1: Hello"
127.0.0.1:6379> RPUSH chat:room123 "User2: Hi there"
```

### 5.2 LRANGE/LLEN/LINDEX - 리스트 조회

```bash
# ============================================
# LRANGE - 범위 조회
# ============================================
127.0.0.1:6379> RPUSH mylist 1 2 3 4 5 6 7 8 9 10
(integer) 10

# 처음 3개
127.0.0.1:6379> LRANGE mylist 0 2
1) "1"
2) "2"
3) "3"

# 전체 조회
127.0.0.1:6379> LRANGE mylist 0 -1
1) "1"
2) "2"
...
10) "10"

# 마지막 3개
127.0.0.1:6379> LRANGE mylist -3 -1
1) "8"
2) "9"
3) "10"

# 중간 범위
127.0.0.1:6379> LRANGE mylist 3 6
1) "4"
2) "5"
3) "6"
4) "7"


# ============================================
# LLEN - 리스트 길이
# ============================================
127.0.0.1:6379> LLEN mylist
(integer) 10

127.0.0.1:6379> LLEN nonexistent
(integer) 0


# ============================================
# LINDEX - 특정 인덱스 조회 (0부터 시작)
# ============================================
127.0.0.1:6379> LINDEX mylist 0
"1"  # 첫 번째

127.0.0.1:6379> LINDEX mylist 5
"6"  # 여섯 번째

# 음수 인덱스 (끝에서부터)
127.0.0.1:6379> LINDEX mylist -1
"10"  # 마지막

127.0.0.1:6379> LINDEX mylist -2
"9"

127.0.0.1:6379> LINDEX mylist 100
(nil)  # 범위 벗어남


# ============================================
# LPOS - 요소 위치 찾기 (Redis 6.0.6+)
# ============================================
127.0.0.1:6379> RPUSH fruits "apple" "banana" "cherry" "banana" "date"
(integer) 5

# 첫 번째 매칭 위치
127.0.0.1:6379> LPOS fruits "banana"
(integer) 1

# RANK: n번째 매칭 (1부터 시작)
127.0.0.1:6379> LPOS fruits "banana" RANK 2
(integer) 3  # 두 번째 banana는 인덱스 3

# COUNT: 여러 매칭 위치
127.0.0.1:6379> LPOS fruits "banana" COUNT 2
1) (integer) 1
2) (integer) 3

# MAXLEN: 검색 범위 제한
127.0.0.1:6379> LPOS fruits "date" MAXLEN 3
(nil)  # 처음 3개 안에 없음
```

### 5.3 LSET/LINSERT/LREM - 리스트 수정

```bash
# ============================================
# LSET - 특정 인덱스 값 변경
# ============================================
127.0.0.1:6379> RPUSH mylist "a" "b" "c"
(integer) 3
127.0.0.1:6379> LSET mylist 1 "B"
OK
127.0.0.1:6379> LRANGE mylist 0 -1
1) "a"
2) "B"  # 변경됨
3) "c"

# 음수 인덱스
127.0.0.1:6379> LSET mylist -1 "C"
OK

# 범위 벗어남
127.0.0.1:6379> LSET mylist 10 "x"
(error) ERR index out of range


# ============================================
# LINSERT - 특정 요소 앞/뒤에 삽입
# ============================================
127.0.0.1:6379> RPUSH mylist 1 2 4 5
(integer) 4

# BEFORE: 특정 값 앞에 삽입
127.0.0.1:6379> LINSERT mylist BEFORE "4" "3"
(integer) 5
127.0.0.1:6379> LRANGE mylist 0 -1
1) "1"
2) "2"
3) "3"
4) "4"
5) "5"

# AFTER: 특정 값 뒤에 삽입
127.0.0.1:6379> LINSERT mylist AFTER "2" "2.5"
(integer) 6

# 요소가 없으면
127.0.0.1:6379> LINSERT mylist BEFORE "nonexistent" "x"
(integer) -1


# ============================================
# LREM - 요소 제거
# ============================================
127.0.0.1:6379> RPUSH fruits "apple" "banana" "apple" "cherry" "apple"
(integer) 5

# count > 0: 앞에서부터 count개 제거
127.0.0.1:6379> LREM fruits 2 "apple"
(integer) 2  # 2개 제거
127.0.0.1:6379> LRANGE fruits 0 -1
1) "banana"
2) "cherry"
3) "apple"

# count < 0: 뒤에서부터 |count|개 제거
127.0.0.1:6379> RPUSH nums 1 2 3 2 4 2 5
(integer) 7
127.0.0.1:6379> LREM nums -2 "2"
(integer) 2  # 뒤에서 2개 제거

# count = 0: 모든 매칭 제거
127.0.0.1:6379> LREM nums 0 "2"
(integer) 1  # 남은 "2" 모두 제거


# ============================================
# LTRIM - 범위 외 요소 모두 제거 (중요!)
# ============================================
127.0.0.1:6379> RPUSH logs "log1" "log2" "log3" "log4" "log5"
(integer) 5

# 처음 3개만 유지
127.0.0.1:6379> LTRIM logs 0 2
OK
127.0.0.1:6379> LRANGE logs 0 -1
1) "log1"
2) "log2"
3) "log3"

# 최신 100개 로그만 유지 패턴
127.0.0.1:6379> LPUSH recent:logs "new log"
127.0.0.1:6379> LTRIM recent:logs 0 99
OK

# 전체 삭제 (빈 범위)
127.0.0.1:6379> LTRIM logs 1 0
OK  # 리스트가 비어짐
```

### 5.4 블로킹 명령어 - BLPOP/BRPOP

```bash
# ============================================
# BLPOP - 블로킹 LPOP (큐가 비어있으면 대기)
# ============================================

# 클라이언트 1 (Producer)
127.0.0.1:6379> RPUSH queue "task1"
(integer) 1

# 클라이언트 2 (Consumer)
127.0.0.1:6379> BLPOP queue 0
1) "queue"    # 키 이름
2) "task1"    # 값

# 큐가 비어있을 때 (무한 대기)
127.0.0.1:6379> BLPOP queue 0
# ... 대기 중 ...
# 다른 클라이언트가 RPUSH하면 즉시 반환


# ============================================
# 타임아웃 설정 (초)
# ============================================
127.0.0.1:6379> BLPOP empty_queue 5
(nil)  # 5초 후 타임아웃
(5.05s)

# 여러 큐 동시 대기 (왼쪽부터 우선순위)
127.0.0.1:6379> BLPOP high_priority normal_priority low_priority 30
# high_priority가 비어있으면 normal_priority 확인
# 30초 동안 대기


# ============================================
# BRPOP - 블로킹 RPOP
# ============================================
127.0.0.1:6379> BRPOP queue 0
1) "queue"
2) "task1"


# ============================================
# BRPOPLPUSH - 원자적 큐 이동 (블로킹)
# ============================================

# 작업 처리 패턴 (Reliable Queue)
127.0.0.1:6379> RPUSH jobs:pending "job1" "job2"
(integer) 2

# Worker가 작업 가져가서 처리 중 큐로 이동
127.0.0.1:6379> BRPOPLPUSH jobs:pending jobs:processing 0
"job2"

# 이제 jobs:processing에 있음 (처리 실패 시 재시도 가능)
127.0.0.1:6379> LRANGE jobs:processing 0 -1
1) "job2"

# 처리 완료 후 제거
127.0.0.1:6379> LREM jobs:processing 1 "job2"
(integer) 1


# ============================================
# 실전 활용: 작업 큐 시스템
# ============================================

# Producer (작업 추가)
redis-cli RPUSH jobs:pending '{"id":1,"type":"email","to":"user@example.com"}'

# Consumer (워커)
while true; do
  JOB=$(redis-cli BRPOPLPUSH jobs:pending jobs:processing 0)
  
  # 작업 처리
  process_job "$JOB"
  
  # 성공 시 제거
  if [ $? -eq 0 ]; then
    redis-cli LREM jobs:processing 1 "$JOB"
  else
    # 실패 시 재시도 큐로 이동
    redis-cli RPUSH jobs:failed "$JOB"
    redis-cli LREM jobs:processing 1 "$JOB"
  fi
done


# ============================================
# BLMOVE - 리스트 간 원자적 이동 (Redis 6.2+)
# ============================================
127.0.0.1:6379> BLMOVE source dest LEFT RIGHT 5
# source의 왼쪽에서 빼서 dest의 오른쪽에 추가 (5초 대기)
```

---

## 6. Set 명령어 - 중복 없는 컬렉션

Set은 중복이 없는 순서 없는 컬렉션으로, 유니크한 값을 관리하고 집합 연산을 수행하기에 적합합니다.

### 6.1 SADD/SMEMBERS/SISMEMBER - Set 기본 연산

```bash
# ============================================
# SADD - Set에 멤버 추가
# ============================================
127.0.0.1:6379> SADD tags "redis" "cache" "nosql"
(integer) 3  # 추가된 멤버 수

# 중복은 무시됨
127.0.0.1:6379> SADD tags "redis"
(integer) 0  # 이미 있음

127.0.0.1:6379> SADD tags "database" "redis"
(integer) 1  # "database"만 추가됨


# ============================================
# SMEMBERS - 모든 멤버 조회
# ============================================
127.0.0.1:6379> SMEMBERS tags
1) "cache"
2) "nosql"
3) "database"
4) "redis"

# ⚠️ 주의: 순서는 보장되지 않음!
# ⚠️ 멤버가 많으면 느림! (수만 개 이하만 사용)


# ============================================
# SISMEMBER - 멤버 존재 여부 확인 (O(1))
# ============================================
127.0.0.1:6379> SISMEMBER tags "redis"
(integer) 1  # 존재

127.0.0.1:6379> SISMEMBER tags "mysql"
(integer) 0  # 없음


# ============================================
# SMISMEMBER - 여러 멤버 존재 확인 (Redis 6.2+)
# ============================================
127.0.0.1:6379> SMISMEMBER tags "redis" "mysql" "cache"
1) (integer) 1  # redis: 있음
2) (integer) 0  # mysql: 없음
3) (integer) 1  # cache: 있음


# ============================================
# SCARD - Set 크기 (멤버 개수)
# ============================================
127.0.0.1:6379> SCARD tags
(integer) 4

127.0.0.1:6379> SCARD nonexistent
(integer) 0


# ============================================
# 실전 활용 예시
# ============================================

# 사용자 팔로워 (중복 방지)
127.0.0.1:6379> SADD user:1000:followers 1001 1002 1003
(integer) 3

# 이미 팔로우 중인지 확인
127.0.0.1:6379> SISMEMBER user:1000:followers 1002
(integer) 1  # 팔로우 중

# 팔로워 수
127.0.0.1:6379> SCARD user:1000:followers
(integer) 3


# 태그 시스템
127.0.0.1:6379> SADD post:100:tags "python" "redis" "tutorial"
(integer) 3

# IP 블랙리스트
127.0.0.1:6379> SADD blacklist:ip "192.168.1.100" "10.0.0.5"
(integer) 2
127.0.0.1:6379> SISMEMBER blacklist:ip "192.168.1.100"
(integer) 1  # 차단됨


# 온라인 사용자
127.0.0.1:6379> SADD online:users 1000 1001 1002
(integer) 3
127.0.0.1:6379> EXPIRE online:users 3600  # 1시간 후 리셋
```

### 6.2 SREM/SPOP/SRANDMEMBER - Set 요소 제거 및 샘플링

```bash
# ============================================
# SREM - 멤버 제거
# ============================================
127.0.0.1:6379> SADD fruits "apple" "banana" "cherry"
(integer) 3
127.0.0.1:6379> SREM fruits "banana"
(integer) 1  # 제거된 멤버 수

# 여러 멤버 동시 제거
127.0.0.1:6379> SREM fruits "apple" "date" "cherry"
(integer) 2  # "date"는 없었음


# ============================================
# SPOP - 무작위 멤버 제거하고 반환
# ============================================
127.0.0.1:6379> SADD lottery 1 2 3 4 5 6 7 8 9 10
(integer) 10
127.0.0.1:6379> SPOP lottery
"7"  # 무작위 선택됨

# 여러 개 제거
127.0.0.1:6379> SPOP lottery 3
1) "2"
2) "9"
3) "5"

# 용도: 추첨, 무작위 선택


# ============================================
# SRANDMEMBER - 무작위 멤버 조회 (제거 안함)
# ============================================
127.0.0.1:6379> SADD deck "A" "2" "3" "4" "5"
(integer) 5
127.0.0.1:6379> SRANDMEMBER deck
"3"  # 여전히 Set에 있음

# 여러 개 조회
127.0.0.1:6379> SRANDMEMBER deck 2
1) "A"
2) "5"

# 음수: 중복 허용 (샘플링)
127.0.0.1:6379> SRANDMEMBER deck -10
1) "2"
2) "A"
3) "2"  # 중복 가능
4) "5"
...


# ============================================
# 실전 활용 예시
# ============================================

# 랜덤 추천 (제거 안함)
127.0.0.1:6379> SADD recommended:movies 101 102 103 104 105
(integer) 5
127.0.0.1:6379> SRANDMEMBER recommended:movies 3
1) "102"
2) "105"
3) "101"


# 일일 퀘스트 할당 (중복 없이 제거)
127.0.0.1:6379> SADD available:quests "quest1" "quest2" "quest3"
(integer) 3
127.0.0.1:6379> SPOP available:quests 2
1) "quest2"
2) "quest1"
# 사용자에게 할당됨


# 카드 게임 (덱에서 뽑기)
127.0.0.1:6379> SADD deck:cards "AS" "KH" "QD" ... (52장)
127.0.0.1:6379> SPOP deck:cards 5  # 5장 뽑기
```

### 6.3 집합 연산 - SINTER/SUNION/SDIFF

```bash
# ============================================
# SINTER - 교집합
# ============================================
127.0.0.1:6379> SADD skills:user1 "python" "redis" "docker"
(integer) 3
127.0.0.1:6379> SADD skills:user2 "redis" "docker" "kubernetes"
(integer) 3

127.0.0.1:6379> SINTER skills:user1 skills:user2
1) "redis"
2) "docker"

# 여러 Set의 교집합
127.0.0.1:6379> SADD skills:user3 "redis" "java"
(integer) 2
127.0.0.1:6379> SINTER skills:user1 skills:user2 skills:user3
1) "redis"


# ============================================
# SINTERSTORE - 교집합을 새 Set에 저장
# ============================================
127.0.0.1:6379> SINTERSTORE common:skills skills:user1 skills:user2
(integer) 2  # 저장된 멤버 수

127.0.0.1:6379> SMEMBERS common:skills
1) "redis"
2) "docker"


# ============================================
# SUNION - 합집합
# ============================================
127.0.0.1:6379> SUNION skills:user1 skills:user2
1) "python"
2) "redis"
3) "docker"
4) "kubernetes"


# ============================================
# SUNIONSTORE - 합집합 저장
# ============================================
127.0.0.1:6379> SUNIONSTORE all:skills skills:user1 skills:user2
(integer) 4


# ============================================
# SDIFF - 차집합 (첫 Set에만 있는 것)
# ============================================
127.0.0.1:6379> SDIFF skills:user1 skills:user2
1) "python"  # user1만 가진 스킬

127.0.0.1:6379> SDIFF skills:user2 skills:user1
1) "kubernetes"  # user2만 가진 스킬


# ============================================
# SDIFFSTORE - 차집합 저장
# ============================================
127.0.0.1:6379> SDIFFSTORE unique:user1 skills:user1 skills:user2
(integer) 1


# ============================================
# SINTERCARD - 교집합 크기만 반환 (Redis 7.0+, 빠름)
# ============================================
127.0.0.1:6379> SINTERCARD 2 skills:user1 skills:user2
(integer) 2  # 교집합 멤버 개수

# LIMIT: 최대 개수만 세기 (조기 종료)
127.0.0.1:6379> SINTERCARD 2 skills:user1 skills:user2 LIMIT 1
(integer) 1  # 최소 1개는 있음 (빠름!)


# ============================================
# 실전 활용 예시
# ============================================

# 공통 친구 찾기
127.0.0.1:6379> SADD friends:user1 100 101 102 103
127.0.0.1:6379> SADD friends:user2 102 103 104 105
127.0.0.1:6379> SINTER friends:user1 friends:user2
1) "102"
2) "103"


# 추천 시스템 (친구의 친구)
127.0.0.1:6379> SUNION friends:101 friends:102 friends:103
# 모든 친구의 친구
127.0.0.1:6379> SDIFF temp:all friends:user1
# 나는 친구 아닌 사람들 (추천 후보)


# 태그 검색 (AND)
127.0.0.1:6379> SADD tag:python 1 2 3 4
127.0.0.1:6379> SADD tag:redis 2 3 5 6
127.0.0.1:6379> SADD tag:tutorial 3 4 6 7
127.0.0.1:6379> SINTER tag:python tag:redis tag:tutorial
1) "3"  # 모든 태그를 가진 게시물


# 이미 본 콘텐츠 제외
127.0.0.1:6379> SADD all:videos 1 2 3 4 5 6 7 8 9 10
127.0.0.1:6379> SADD user:1000:watched 1 3 5
127.0.0.1:6379> SDIFF all:videos user:1000:watched
1) "2"
2) "4"
3) "6"
4) "7"
5) "8"
6) "9"
7) "10"
```

### 6.4 SSCAN - Set 안전한 순회

```bash
# ============================================
# SSCAN - Set 멤버 순회 (대용량)
# ============================================

# 기본 사용: SSCAN key cursor [MATCH pattern] [COUNT count]
127.0.0.1:6379> SSCAN myset 0
1) "5"      # 다음 커서
2) 1) "member1"
   2) "member2"
   3) "member3"

127.0.0.1:6379> SSCAN myset 5
1) "0"      # 끝
2) 1) "member4"
   2) "member5"

# MATCH: 패턴 필터링
127.0.0.1:6379> SSCAN users 0 MATCH user:* COUNT 100

# Python 전체 순회
cursor = 0
all_members = []
while True:
    cursor, members = r.sscan('large:set', cursor, count=1000)
    all_members.extend(members)
    if cursor == 0:
        break
```

---

## 7. Sorted Set 명령어 - 점수 기반 정렬 컬렉션

Sorted Set은 각 멤버에 점수(score)가 있어 자동 정렬되는 컬렉션입니다. 리더보드, 랭킹, 우선순위 큐 등에 최적입니다.

### 7.1 ZADD/ZRANGE/ZSCORE - 기본 연산

```bash
# ============================================
# ZADD - Sorted Set에 멤버 추가 (점수와 함께)
# ============================================
127.0.0.1:6379> ZADD leaderboard 100 "player1"
(integer) 1

# 여러 멤버 동시 추가
127.0.0.1:6379> ZADD leaderboard 150 "player2" 120 "player3" 90 "player4"
(integer) 3

# 중복 멤버는 점수 업데이트
127.0.0.1:6379> ZADD leaderboard 200 "player1"
(integer) 0  # 기존 멤버, 점수만 업데이트


# ============================================
# ZADD 옵션들
# ============================================

# NX: 새 멤버만 추가 (기존 멤버 무시)
127.0.0.1:6379> ZADD leaderboard NX 250 "player1"
(integer) 0  # 이미 있어서 무시

# XX: 기존 멤버만 업데이트
127.0.0.1:6379> ZADD leaderboard XX 250 "player1"
(integer) 0  # 업데이트됨
127.0.0.1:6379> ZADD leaderboard XX 100 "newplayer"
(integer) 0  # 없어서 무시

# GT: 새 점수가 더 클 때만 (GreaT)
127.0.0.1:6379> ZADD leaderboard GT 260 "player1"
(integer) 0  # 250 → 260 업데이트
127.0.0.1:6379> ZADD leaderboard GT 240 "player1"
(integer) 0  # 무시 (260 > 240)

# LT: 새 점수가 더 작을 때만 (Less Than)
127.0.0.1:6379> ZADD leaderboard LT 230 "player1"
(integer) 0  # 260 → 230 업데이트

# CH: 변경된 멤버 수 반환 (기본은 추가된 수만)
127.0.0.1:6379> ZADD leaderboard CH 240 "player1" 160 "player2"
(integer) 2  # 2개 변경됨

# INCR: 점수 증가 (ZINCRBY와 동일)
127.0.0.1:6379> ZADD leaderboard INCR 10 "player1"
"250"  # 240 + 10


# ============================================
# ZRANGE - 인덱스 범위로 조회 (오름차순)
# ============================================
127.0.0.1:6379> ZRANGE leaderboard 0 2
1) "player4"   # 90점 (최저)
2) "player3"   # 120점
3) "player2"   # 160점

# 점수 함께 출력
127.0.0.1:6379> ZRANGE leaderboard 0 2 WITHSCORES
1) "player4"
2) "90"
3) "player3"
4) "120"
5) "player2"
6) "160"

# 전체 조회 (오름차순)
127.0.0.1:6379> ZRANGE leaderboard 0 -1 WITHSCORES

# 역순 (내림차순) - REV 옵션
127.0.0.1:6379> ZRANGE leaderboard 0 2 REV WITHSCORES
1) "player1"   # 최고점
2) "250"
3) "player2"
4) "160"
5) "player3"
6) "120"


# ============================================
# ZRANGEBYSCORE - 점수 범위로 조회
# ============================================
# 100점 이상 200점 이하
127.0.0.1:6379> ZRANGEBYSCORE leaderboard 100 200
1) "player3"  # 120
2) "player2"  # 160

# WITHSCORES
127.0.0.1:6379> ZRANGEBYSCORE leaderboard 100 200 WITHSCORES
1) "player3"
2) "120"
3) "player2"
4) "160"

# 무한대: -inf, +inf
127.0.0.1:6379> ZRANGEBYSCORE leaderboard -inf +inf
# 전체 조회 (점수 순)

# 경계 제외: (
127.0.0.1:6379> ZRANGEBYSCORE leaderboard (100 200
# 100 초과 200 이하

127.0.0.1:6379> ZRANGEBYSCORE leaderboard 100 (200
# 100 이상 200 미만

# LIMIT: 페이징
127.0.0.1:6379> ZRANGEBYSCORE leaderboard -inf +inf LIMIT 0 10
# 처음 10개

127.0.0.1:6379> ZRANGEBYSCORE leaderboard -inf +inf LIMIT 10 10
# 11~20번째


# ============================================
# ZREVRANGEBYSCORE - 점수 역순 조회
# ============================================
127.0.0.1:6379> ZREVRANGEBYSCORE leaderboard +inf -inf WITHSCORES
# 높은 점수부터

127.0.0.1:6379> ZREVRANGEBYSCORE leaderboard 200 100 WITHSCORES
# 200~100점 (내림차순)


# ============================================
# ZSCORE - 멤버의 점수 조회
# ============================================
127.0.0.1:6379> ZSCORE leaderboard "player1"
"250"

127.0.0.1:6379> ZSCORE leaderboard "nonexistent"
(nil)


# ============================================
# ZMSCORE - 여러 멤버 점수 조회 (Redis 6.2+)
# ============================================
127.0.0.1:6379> ZMSCORE leaderboard "player1" "player2" "player3"
1) "250"
2) "160"
3) "120"
```

### 7.2 ZINCRBY/ZRANK/ZCARD - 점수 증가 및 순위

```bash
# ============================================
# ZINCRBY - 점수 증가
# ============================================
127.0.0.1:6379> ZINCRBY leaderboard 10 "player1"
"260"  # 250 + 10

# 음수로 감소
127.0.0.1:6379> ZINCRBY leaderboard -5 "player1"
"255"

# 멤버가 없으면 0에서 시작
127.0.0.1:6379> ZINCRBY leaderboard 50 "newplayer"
"50"


# ============================================
# ZRANK - 순위 조회 (0부터 시작, 오름차순)
# ============================================
127.0.0.1:6379> ZRANK leaderboard "player4"
(integer) 0  # 최하위 (90점)

127.0.0.1:6379> ZRANK leaderboard "player1"
(integer) 3  # 최상위 (255점)

# WITHSCORE: 점수도 함께 반환 (Redis 7.2+)
127.0.0.1:6379> ZRANK leaderboard "player1" WITHSCORE
1) (integer) 3
2) "255"


# ============================================
# ZREVRANK - 역순 순위 (내림차순, 높은 점수가 0)
# ============================================
127.0.0.1:6379> ZREVRANK leaderboard "player1"
(integer) 0  # 1등

127.0.0.1:6379> ZREVRANK leaderboard "player4"
(integer) 3  # 꼴등


# ============================================
# ZCARD - Sorted Set 크기
# ============================================
127.0.0.1:6379> ZCARD leaderboard
(integer) 4

127.0.0.1:6379> ZCARD nonexistent
(integer) 0


# ============================================
# ZCOUNT - 점수 범위 내 멤버 개수
# ============================================
127.0.0.1:6379> ZCOUNT leaderboard 100 200
(integer) 2  # 100~200점 사이 멤버 수

127.0.0.1:6379> ZCOUNT leaderboard -inf +inf
(integer) 4  # 전체


# ============================================
# ZLEXCOUNT - 사전순 범위 개수 (점수 동일 시)
# ============================================
127.0.0.1:6379> ZADD words 0 "apple" 0 "banana" 0 "cherry"
(integer) 3
127.0.0.1:6379> ZLEXCOUNT words [a [c
(integer) 2  # a~c 사이 (apple, banana)


# ============================================
# 실전 활용 예시
# ============================================

# 게임 리더보드 (점수 증가)
127.0.0.1:6379> ZINCRBY game:scores 100 "user:1000"
"1500"  # 총 점수

# 순위 확인
127.0.0.1:6379> ZREVRANK game:scores "user:1000"
(integer) 5  # 6등

# Top 10 조회
127.0.0.1:6379> ZREVRANGE game:scores 0 9 WITHSCORES
1) "user:2000"
2) "5000"
...


# 인기 게시물 (조회수 기반)
127.0.0.1:6379> ZINCRBY popular:posts 1 "post:100"
"1523"  # 조회수

# 인기 Top 5
127.0.0.1:6379> ZREVRANGE popular:posts 0 4 WITHSCORES


# 타임라인 (타임스탬프 기반)
127.0.0.1:6379> ZADD timeline 1733320800 "post:1"
127.0.0.1:6379> ZADD timeline 1733320900 "post:2"

# 최신 10개
127.0.0.1:6379> ZREVRANGE timeline 0 9


# 우선순위 큐
127.0.0.1:6379> ZADD priority:tasks 1 "urgent" 5 "normal" 10 "low"
(integer) 3

# 최우선 작업 가져오기
127.0.0.1:6379> ZRANGE priority:tasks 0 0
1) "urgent"
```

### 7.3 ZREM/ZPOPMIN/ZPOPMAX - 멤버 제거

```bash
# ============================================
# ZREM - 멤버 제거
# ============================================
127.0.0.1:6379> ZREM leaderboard "player4"
(integer) 1  # 제거된 멤버 수

# 여러 멤버 동시 제거
127.0.0.1:6379> ZREM leaderboard "player1" "player2" "nonexistent"
(integer) 2  # 2개만 제거


# ============================================
# ZPOPMIN - 최소 점수 멤버 제거하고 반환
# ============================================
127.0.0.1:6379> ZADD tasks 1 "urgent" 5 "normal" 10 "low"
(integer) 3

127.0.0.1:6379> ZPOPMIN tasks
1) "urgent"
2) "1"

# 여러 개 제거
127.0.0.1:6379> ZPOPMIN tasks 2
1) "normal"
2) "5"
3) "low"
4) "10"


# ============================================
# ZPOPMAX - 최대 점수 멤버 제거하고 반환
# ============================================
127.0.0.1:6379> ZADD scores 100 "A" 200 "B" 300 "C"
(integer) 3

127.0.0.1:6379> ZPOPMAX scores
1) "C"
2) "300"

127.0.0.1:6379> ZPOPMAX scores 2
1) "B"
2) "200"
3) "A"
4) "100"


# ============================================
# BZPOPMIN/BZPOPMAX - 블로킹 버전
# ============================================
# 큐가 비어있으면 대기
127.0.0.1:6379> BZPOPMIN tasks:urgent 0
# ... 대기 중 ...
# 다른 클라이언트가 ZADD하면 즉시 반환

127.0.0.1:6379> BZPOPMIN tasks:urgent 5
(nil)  # 5초 타임아웃


# ============================================
# ZREMRANGEBYRANK - 순위 범위로 제거
# ============================================
127.0.0.1:6379> ZADD numbers 1 "one" 2 "two" 3 "three" 4 "four" 5 "five"
(integer) 5

# 하위 2개 제거
127.0.0.1:6379> ZREMRANGEBYRANK numbers 0 1
(integer) 2  # "one", "two" 제거

# 상위 제외하고 모두 제거
127.0.0.1:6379> ZREMRANGEBYRANK numbers 0 -4
# 상위 3개만 남김


# ============================================
# ZREMRANGEBYSCORE - 점수 범위로 제거
# ============================================
127.0.0.1:6379> ZADD scores 10 "A" 20 "B" 30 "C" 40 "D" 50 "E"
(integer) 5

# 20~40점 제거
127.0.0.1:6379> ZREMRANGEBYSCORE scores 20 40
(integer) 3  # B, C, D 제거

# 특정 점수 이하 제거
127.0.0.1:6379> ZREMRANGEBYSCORE scores -inf 15
(integer) 1  # A 제거


# ============================================
# ZREMRANGEBYLEX - 사전순 범위로 제거 (점수 동일 시)
# ============================================
127.0.0.1:6379> ZADD words 0 "apple" 0 "banana" 0 "cherry" 0 "date"
(integer) 4

127.0.0.1:6379> ZREMRANGEBYLEX words [b [d
(integer) 2  # banana, cherry 제거


# ============================================
# 실전 활용: 만료된 데이터 정리
# ============================================

# 타임스탬프 기반 데이터
127.0.0.1:6379> ZADD sessions 1733320800 "session:abc"
127.0.0.1:6379> ZADD sessions 1733320900 "session:def"
127.0.0.1:6379> ZADD sessions 1733321000 "session:ghi"

# 1시간 전 세션 삭제 (현재: 1733324400)
127.0.0.1:6379> ZREMRANGEBYSCORE sessions -inf 1733320800
(integer) 1

# 정기적 정리 스크립트
while true; do
  CUTOFF=$(($(date +%s) - 3600))  # 1시간 전
  redis-cli ZREMRANGEBYSCORE sessions -inf $CUTOFF
  sleep 60
done
```

### 7.4 집합 연산 - ZINTER/ZUNION/ZDIFF

```bash
# ============================================
# ZINTER - 교집합 (Redis 6.2+)
# ============================================
127.0.0.1:6379> ZADD set1 1 "a" 2 "b" 3 "c"
(integer) 3
127.0.0.1:6379> ZADD set2 2 "b" 3 "c" 4 "d"
(integer) 3

# 기본: 점수 합산
127.0.0.1:6379> ZINTER 2 set1 set2 WITHSCORES
1) "b"
2) "4"   # 2 + 2
3) "c"
4) "6"   # 3 + 3

# WEIGHTS: 가중치 적용
127.0.0.1:6379> ZINTER 2 set1 set2 WEIGHTS 1 2 WITHSCORES
1) "b"
2) "6"   # 2*1 + 2*2
3) "c"
4) "9"   # 3*1 + 3*2

# AGGREGATE: 집계 방식
127.0.0.1:6379> ZINTER 2 set1 set2 AGGREGATE MAX WITHSCORES
1) "b"
2) "2"   # max(2, 2)
3) "c"
4) "3"   # max(3, 3)

127.0.0.1:6379> ZINTER 2 set1 set2 AGGREGATE MIN WITHSCORES
# MIN, MAX, SUM 가능


# ============================================
# ZINTERSTORE - 교집합을 새 Sorted Set에 저장
# ============================================
127.0.0.1:6379> ZINTERSTORE common 2 set1 set2 WEIGHTS 1 2
(integer) 2  # 저장된 멤버 수

127.0.0.1:6379> ZRANGE common 0 -1 WITHSCORES
1) "b"
2) "6"
3) "c"
4) "9"


# ============================================
# ZUNION - 합집합
# ============================================
127.0.0.1:6379> ZUNION 2 set1 set2 WITHSCORES
1) "a"
2) "1"
3) "b"
4) "4"   # 2 + 2
5) "c"
6) "6"   # 3 + 3
7) "d"
8) "4"


# ============================================
# ZUNIONSTORE - 합집합 저장
# ============================================
127.0.0.1:6379> ZUNIONSTORE all 2 set1 set2
(integer) 4


# ============================================
# ZDIFF - 차집합 (Redis 6.2+)
# ============================================
127.0.0.1:6379> ZDIFF 2 set1 set2 WITHSCORES
1) "a"
2) "1"  # set1에만 있음


# ============================================
# ZDIFFSTORE - 차집합 저장
# ============================================
127.0.0.1:6379> ZDIFFSTORE unique 2 set1 set2
(integer) 1


# ============================================
# 실전 활용: 추천 시스템
# ============================================

# 사용자별 관심 점수
127.0.0.1:6379> ZADD user:1000:interests 10 "python" 8 "redis" 5 "docker"
127.0.0.1:6379> ZADD user:1001:interests 7 "python" 9 "redis" 6 "kubernetes"

# 공통 관심사 (교집합)
127.0.0.1:6379> ZINTER 2 user:1000:interests user:1001:interests WITHSCORES
1) "python"
2) "17"  # 10 + 7
3) "redis"
4) "17"  # 8 + 9

# 추천 콘텐츠 (친구들의 관심사 합)
127.0.0.1:6379> ZUNION 3 \
  user:1001:interests \
  user:1002:interests \
  user:1003:interests \
  WEIGHTS 1 1 1 \
  AGGREGATE MAX
```

### 7.5 ZSCAN - Sorted Set 순회

```bash
# ============================================
# ZSCAN - 안전한 순회
# ============================================

# 기본 사용: ZSCAN key cursor [MATCH pattern] [COUNT count]
127.0.0.1:6379> ZSCAN leaderboard 0
1) "10"     # 다음 커서
2) 1) "player1"
   2) "255"
   3) "player2"
   4) "160"
   ...

127.0.0.1:6379> ZSCAN leaderboard 10
1) "0"      # 끝
2) 1) "player3"
   2) "120"

# MATCH 패턴
127.0.0.1:6379> ZSCAN users:scores 0 MATCH user:1*

# Python 전체 순회
cursor = 0
all_members = []
while True:
    cursor, items = r.zscan('large:zset', cursor, count=1000)
    all_members.extend(items)  # [(member, score), ...]
    if cursor == 0:
        break
```

---

## 8. 트랜잭션 및 파이프라인

### 8.1 MULTI/EXEC - 트랜잭션

```bash
# ============================================
# MULTI - 트랜잭션 시작
# ============================================
127.0.0.1:6379> MULTI
OK

127.0.0.1:6379> SET key1 "value1"
QUEUED

127.0.0.1:6379> INCR counter
QUEUED

127.0.0.1:6379> LPUSH mylist "item"
QUEUED


# ============================================
# EXEC - 트랜잭션 실행
# ============================================
127.0.0.1:6379> EXEC
1) OK        # SET 결과
2) (integer) 1   # INCR 결과
3) (integer) 1   # LPUSH 결과


# ============================================
# DISCARD - 트랜잭션 취소
# ============================================
127.0.0.1:6379> MULTI
OK
127.0.0.1:6379> SET key "value"
QUEUED
127.0.0.1:6379> DISCARD
OK
# 모든 명령 취소됨


# ============================================
# WATCH - 낙관적 락 (Optimistic Locking)
# ============================================
127.0.0.1:6379> WATCH balance
OK

# balance 읽기
127.0.0.1:6379> GET balance
"1000"

# 트랜잭션 시작
127.0.0.1:6379> MULTI
OK
127.0.0.1:6379> DECRBY balance 100
QUEUED
127.0.0.1:6379> EXEC
1) (integer) 900  # 성공

# 만약 EXEC 전에 다른 클라이언트가 balance를 변경하면
# EXEC 결과: (nil) - 트랜잭션 실패


# ============================================
# UNWATCH - 모든 WATCH 해제
# ============================================
127.0.0.1:6379> WATCH key1 key2
OK
127.0.0.1:6379> UNWATCH
OK


# ============================================
# 실전 예시: 송금
# ============================================

# 계좌 A에서 B로 100원 송금
127.0.0.1:6379> WATCH account:A account:B
OK

127.0.0.1:6379> GET account:A
"1000"
127.0.0.1:6379> GET account:B
"500"

127.0.0.1:6379> MULTI
OK
127.0.0.1:6379> DECRBY account:A 100
QUEUED
127.0.0.1:6379> INCRBY account:B 100
QUEUED
127.0.0.1:6379> EXEC
1) (integer) 900
2) (integer) 600  # 성공


# Python 예시
def transfer(from_account, to_account, amount):
    pipe = r.pipeline()
    
    while True:
        try:
            # WATCH
            pipe.watch(from_account, to_account)
            
            # 잔액 확인
            balance = int(pipe.get(from_account) or 0)
            
            if balance < amount:
                pipe.unwatch()
                return False  # 잔액 부족
            
            # 트랜잭션
            pipe.multi()
            pipe.decrby(from_account, amount)
            pipe.incrby(to_account, amount)
            pipe.execute()
            
            return True  # 성공
            
        except redis.WatchError:
            # 충돌 발생, 재시도
            continue
```

### 8.2 파이프라인 - 성능 최적화

```bash
# ============================================
# 파이프라인 (Redis CLI에서는 직접 지원 안함)
# ============================================

# Python 예시
import redis

r = redis.Redis()

# ❌ 비효율적: 개별 명령 (10번 네트워크 왕복)
for i in range(10):
    r.set(f"key{i}", f"value{i}")

# ✅ 효율적: 파이프라인 (1번 네트워크 왕복)
pipe = r.pipeline()
for i in range(10):
    pipe.set(f"key{i}", f"value{i}")
results = pipe.execute()


# ============================================
# 트랜잭션 vs 파이프라인
# ============================================

# 트랜잭션 (MULTI/EXEC)
- 원자성 보장 (all or nothing)
- 느림 (각 명령 개별 전송)

# 파이프라인
- 원자성 없음
- 빠름 (명령 일괄 전송)

# 트랜잭션 + 파이프라인 (최고!)
pipe = r.pipeline(transaction=True)
pipe.multi()
pipe.set('key1', 'value1')
pipe.incr('counter')
pipe.execute()
```

---

## 9. 실전 활용 패턴 및 Best Practices

### 9.1 캐싱 전략

```bash
# ============================================
# Cache-Aside (Lazy Loading)
# ============================================

# 의사 코드
function get_user(user_id):
    # 1. 캐시 확인
    user = redis.GET("user:" + user_id)
    
    if user:
        return user  # 캐시 히트
    
    # 2. DB 조회
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)
    
    # 3. 캐시 저장 (TTL 1시간)
    redis.SETEX("user:" + user_id, 3600, user)
    
    return user


# ============================================
# Write-Through (쓰기 즉시 캐시)
# ============================================

function update_user(user_id, data):
    # 1. DB 업데이트
    db.update("users", user_id, data)
    
    # 2. 캐시 갱신
    redis.HSET("user:" + user_id, data)
    redis.EXPIRE("user:" + user_id, 3600)


# ============================================
# Cache Invalidation (캐시 무효화)
# ============================================

# 패턴 1: TTL 기반
127.0.0.1:6379> SET cache:product:100 "{...}" EX 600
# 10분 후 자동 삭제

# 패턴 2: 명시적 삭제
function update_product(product_id):
    db.update("products", product_id)
    redis.DEL("cache:product:" + product_id)

# 패턴 3: 버저닝
127.0.0.1:6379> SET cache:product:100:v2 "{...}"
# 스키마 변경 시 버전 증가
```

### 9.2 Rate Limiting (속도 제한)

```bash
# ============================================
# 고정 윈도우 (Fixed Window)
# ============================================

# IP당 분당 100 요청
function check_rate_limit(ip):
    key = "rate:" + ip + ":" + current_minute()
    
    count = redis.INCR(key)
    
    if count == 1:
        redis.EXPIRE(key, 60)  # 1분 TTL
    
    if count > 100:
        return False  # 제한 초과
    
    return True  # 허용


# ============================================
# 슬라이딩 윈도우 (Sliding Window)
# ============================================

# Sorted Set 활용
function check_rate_limit_sliding(user_id):
    key = "rate:" + user_id
    now = time()
    window = 60  # 1분
    limit = 100
    
    # 1. 오래된 요청 제거
    redis.ZREMRANGEBYSCORE(key, 0, now - window)
    
    # 2. 현재 요청 수 확인
    count = redis.ZCARD(key)
    
    if count < limit:
        # 3. 새 요청 추가
        redis.ZADD(key, now, unique_id())
        redis.EXPIRE(key, window)
        return True
    
    return False


# ============================================
# 토큰 버킷 (Token Bucket)
# ============================================

# Hash 활용
function get_token(user_id):
    key = "bucket:" + user_id
    capacity = 10  # 최대 토큰
    rate = 1  # 초당 1개 충전
    
    # Lua 스크립트로 원자적 실행
    return redis.eval("""
        local tokens = tonumber(redis.call('HGET', KEYS[1], 'tokens')) or capacity
        local last_refill = tonumber(redis.call('HGET', KEYS[1], 'last_refill')) or 0
        local now = tonumber(ARGV[1])
        
        -- 토큰 충전
        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + elapsed * rate)
        
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HSET', KEYS[1], 'tokens', tokens)
            redis.call('HSET', KEYS[1], 'last_refill', now)
            return 1  -- 성공
        else
            return 0  -- 실패
        end
    """, 1, key, time())
```

### 9.3 분산 락 (Distributed Lock)

```bash
# ============================================
# 기본 분산 락
# ============================================

# 락 획득
function acquire_lock(resource, ttl=30):
    lock_key = "lock:" + resource
    lock_value = unique_id()  # UUID
    
    # NX: 락이 없을 때만, EX: TTL 설정
    success = redis.SET(lock_key, lock_value, "NX", "EX", ttl)
    
    if success:
        return lock_value  # 락 획득
    
    return None  # 실패


# 락 해제
function release_lock(resource, lock_value):
    lock_key = "lock:" + resource
    
    # Lua 스크립트로 원자적 확인 후 삭제
    return redis.eval("""
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
    """, 1, lock_key, lock_value)


# 사용 예시
lock_value = acquire_lock("resource:123", 10)
if lock_value:
    try:
        # 크리티컬 섹션
        process_resource()
    finally:
        release_lock("resource:123", lock_value)


# ============================================
# Redlock 알고리즘 (다중 Redis)
# ============================================

# 5개 Redis 인스턴스에 락 획득 시도
# 과반수(3개) 이상 성공 시 락 획득
# 자세한 구현은 Redlock 라이브러리 사용 권장
```

### 9.4 성능 최적화 팁

```bash
# ============================================
# 1. 작은 키 이름 사용
# ============================================
# ❌ 비효율
user:1000:profile:firstname
user:1000:profile:lastname

# ✅ 효율적
u:1000:p:fn
u:1000:p:ln

# 또는 Hash 사용
HSET u:1000:p fn "John" ln "Doe"


# ============================================
# 2. 적절한 데이터 타입 선택
# ============================================
# ❌ 작은 리스트를 String JSON으로
SET mylist '["a","b","c"]'

# ✅ List 사용 (더 효율적)
RPUSH mylist "a" "b" "c"

# ❌ 카운터를 String으로
GET counter  # "5"
SET counter "6"

# ✅ INCR 사용 (원자적, 빠름)
INCR counter


# ============================================
# 3. 파이프라인 사용
# ============================================
# ❌ 1000번 네트워크 왕복
for i in range(1000):
    redis.GET(f"key{i}")

# ✅ 1번 네트워크 왕복
pipe = redis.pipeline()
for i in range(1000):
    pipe.get(f"key{i}")
results = pipe.execute()


# ============================================
# 4. SCAN 사용 (KEYS 금지!)
# ============================================
# ❌ 프로덕션 금지
KEYS user:*  # 전체 DB 블로킹!

# ✅ SCAN 사용
cursor = 0
while True:
    cursor, keys = redis.scan(cursor, match='user:*', count=100)
    process(keys)
    if cursor == 0:
        break


# ============================================
# 5. TTL 설정 (메모리 관리)
# ============================================
# ❌ 영구 데이터 (메모리 낭비)
SET cache:data "{...}"

# ✅ TTL 설정
SET cache:data "{...}" EX 3600


# ============================================
# 6. 큰 키 분할
# ============================================
# ❌ 거대한 Hash (수만 개 필드)
HSET huge:hash field1 value1 ... field100000 value100000

# ✅ 샤딩
HSET shard:0 field1 value1
HSET shard:1 field2 value2
...

# 또는 키 분할
SET user:1000:profile:basic "{...}"
SET user:1000:profile:extended "{...}"
```

---

## 10. 유용한 디버깅 및 모니터링 명령어

```bash
# ============================================
# MONITOR - 실시간 명령 모니터링 (⚠️ 성능 영향)
# ============================================
127.0.0.1:6379> MONITOR
OK
1733324400.123456 [0 127.0.0.1:56789] "GET" "mykey"
1733324401.234567 [0 127.0.0.1:56790] "SET" "key" "value"
...

# Ctrl+C로 종료
# ⚠️ 프로덕션에서는 매우 짧은 시간만 사용!


# ============================================
# SLOWLOG - 느린 쿼리 로그
# ============================================
127.0.0.1:6379> SLOWLOG GET 10
1) 1) (integer) 5         # ID
   2) (integer) 1733324400  # 타임스탬프
   3) (integer) 12000      # 실행 시간 (마이크로초)
   4) 1) "KEYS"
      2) "user:*"          # 명령어

127.0.0.1:6379> SLOWLOG LEN
(integer) 128  # 로그 개수

127.0.0.1:6379> SLOWLOG RESET
OK


# ============================================
# MEMORY USAGE - 키 메모리 사용량
# ============================================
127.0.0.1:6379> MEMORY USAGE mykey
(integer) 56  # 바이트

127.0.0.1:6379> MEMORY USAGE large:list
(integer) 123456


# ============================================
# DBSIZE - 키 개수
# ============================================
127.0.0.1:6379> DBSIZE
(integer) 10523


# ============================================
# CLIENT LIST - 연결된 클라이언트 목록
# ============================================
127.0.0.1:6379> CLIENT LIST
id=3 addr=127.0.0.1:56789 name= age=10 idle=0 ...


# ============================================
# CONFIG GET/SET - 런타임 설정 변경
# ============================================
127.0.0.1:6379> CONFIG GET maxmemory
1) "maxmemory"
2) "2147483648"

127.0.0.1:6379> CONFIG SET maxmemory 4gb
OK


# ============================================
# DEBUG OBJECT - 키 내부 정보
# ============================================
127.0.0.1:6379> DEBUG OBJECT mykey
Value at:0x7f... refcount:1 encoding:embstr serializedlength:6 lru:123456


# ============================================
# SAVE/BGSAVE - RDB 스냅샷 저장
# ============================================
127.0.0.1:6379> SAVE
OK  # ⚠️ 블로킹!

127.0.0.1:6379> BGSAVE
Background saving started  # 논블로킹

127.0.0.1:6379> LASTSAVE
(integer) 1733324400  # 마지막 저장 시각
```

---

## 결론 및 학습 로드맵

### 명령어 우선순위 정리

```yaml
입문 (1주차):
  필수:
    - SET, GET, DEL
    - EXISTS, TTL, EXPIRE
    - INCR, DECR
    - LPUSH, RPUSH, LPOP, RPOP
    - SADD, SMEMBERS, SISMEMBER
    
초급 (2주차):
  추가:
    - HSET, HGET, HGETALL
    - MSET, MGET
    - ZADD, ZRANGE, ZREVRANGE
    - SCAN (KEYS 금지!)
    
중급 (3-4주차):
  심화:
    - BLPOP, BRPOP (큐)
    - ZINCRBY, ZRANK (리더보드)
    - SINTER, SUNION (집합 연산)
    - MULTI, EXEC (트랜잭션)
    - 파이프라인 (성능)
    
고급 (5주차+):
  전문:
    - Lua 스크립트
    - Pub/Sub
    - Streams
    - 클러스터 명령어
```

### 학습 자료

```bash
# 공식 문서
https://redis.io/commands

# 인터랙티브 튜토리얼
https://try.redis.io

# Redis CLI 치트시트
redis-cli --help

# 로컬 Redis 설치 (Docker)
docker run -d -p 6379:6379 redis:latest

# Redis Insight (GUI 도구)
https://redis.com/redis-enterprise/redis-insight/
```

**Redis CLI 마스터의 길: 명령어를 손에 익히면 데이터가 춤춘다!** 🚀🔧

