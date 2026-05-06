---
layout: post
title: "스마트팜 센서 데이터 아키텍처 - 수집부터 실시간 대시보드까지"
date: 2026-05-06
categories: iot
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-05-06-smartfarm-sensor-realtime-architecture.webp"
---

# 스마트팜 센서 데이터 아키텍처 - 수집부터 실시간 대시보드까지

스마트팜 프로젝트를 시작하면 가장 먼저 부딪히는 질문이 있습니다.

> "온도 센서값을 1초마다 받는데, 이걸 다 DB에 넣어야 하나요? 프론트엔드에는 어떻게 실시간으로 보여주죠?"

답은 단순하지 않습니다. **얼마나 자주 저장할지, 얼마나 오래 보관할지, 어떤 채널로 프론트에 밀어줄지**는 모두 농장 규모와 의사결정 주기에 따라 달라집니다. 이번 포스트에서는 실제로 운영되는 스마트팜의 데이터 파이프라인을 분석하고, 효율적인 아키텍처를 단계별로 정리합니다.

---

## 전체 아키텍처 한눈에 보기

```
[온도 센서 / DS18B20, SHT3x 등]
        ↓ 1Hz ~ 10Hz
[게이트웨이 / Raspberry Pi, ESP32]
        ↓ MQTT (QoS 1)
[브로커 / EMQX, Mosquitto, AWS IoT Core]
        ↓
   ┌────┴────────────────────────┐
   ↓                             ↓
[스트림 처리]                  [실시간 fan-out]
Telegraf / Kafka              Redis Pub/Sub
   ↓                             ↓
[시계열 DB]                   [WebSocket 서버]
TimescaleDB / InfluxDB           ↓
   ↓                          [브라우저 대시보드]
[다운샘플링 / 연속 집계]
   ↓
[장기 보관 - S3 Parquet]
```

핵심은 **"실시간 경로"와 "저장 경로"를 분리**하는 것입니다. 같은 데이터를 한 번은 사용자에게 즉시 보여주고, 한 번은 분석/이력용으로 저장합니다.

---

## 1. 센서 측에서의 결정 - 얼마나 자주 측정할까?

대부분의 스마트팜 온실 환경에서 온도는 **물리적으로 빨리 변하지 않습니다**. 1초에 0.01℃ 단위로 진동하는 값을 모두 저장하는 건 의미가 없습니다.

### 일반적인 측정 주기

| 항목 | 측정 주기 | 이유 |
|---|---|---|
| 온도 / 습도 | 5초 ~ 1분 | 환경 변화가 느림, 액추에이터 제어 주기와 일치 |
| CO₂ | 30초 ~ 1분 | 센서 자체가 평균값 출력 |
| 광량(PAR) | 1초 ~ 10초 | 구름 통과 시 급변, 광합성 분석용 |
| 토양 수분 | 1분 ~ 5분 | 매우 천천히 변함 |
| 풍속 / 풍향 | 1초 | 환기창 제어용 |

**현장 팁**: 게이트웨이에서 **이동 평균(moving average)** 또는 **변화량 임계치(deadband)** 를 적용해 노이즈를 걸러낸 뒤 전송하면 데이터량이 5~10배 줄어듭니다.

```python
# ESP32 / 게이트웨이의 deadband 필터 예시
last_sent = None
DEADBAND = 0.2  # 0.2℃ 이상 변화할 때만 전송

def maybe_publish(temp: float):
    global last_sent
    if last_sent is None or abs(temp - last_sent) >= DEADBAND:
        mqtt_client.publish("farm/zone1/temp", temp, qos=1)
        last_sent = temp
```

---

## 2. 전송 프로토콜 - 왜 MQTT인가

HTTP POST로도 보낼 수 있지만, 센서 100개가 동시에 1초마다 POST를 날리면 게이트웨이 CPU와 모바일 회선이 먼저 죽습니다. 스마트팜에서는 거의 표준처럼 **MQTT**를 씁니다.

### MQTT가 적합한 이유

- **상시 연결(Long-lived TCP)**: 매 메시지마다 핸드셰이크 비용 없음
- **Pub/Sub 구조**: 센서는 토픽에 발행만, 소비자(저장/대시보드)는 구독만
- **QoS 레벨**: 농장 인터넷이 끊겨도 재전송 보장(QoS 1, 2)
- **Last Will**: 게이트웨이 다운을 즉시 감지

```python
# Python paho-mqtt 게이트웨이 예시
import paho.mqtt.client as mqtt
import json, time

client = mqtt.Client(client_id="gw-zone1")
client.username_pw_set("gateway", "secret")
client.will_set("farm/zone1/status", "offline", qos=1, retain=True)
client.connect("broker.farm.local", 1883)
client.publish("farm/zone1/status", "online", qos=1, retain=True)

while True:
    payload = {
        "ts": int(time.time() * 1000),
        "temp": read_ds18b20(),
        "humidity": read_sht3x_humidity(),
    }
    client.publish("farm/zone1/sensor", json.dumps(payload), qos=1)
    time.sleep(10)
```

토픽 설계는 `farm/{지역}/{구역}/{센서종류}` 같은 계층 구조로 잡아두면 나중에 와일드카드 구독(`farm/+/+/temp`)으로 유연하게 처리할 수 있습니다.

---

## 3. 데이터베이스 - 시계열 DB가 정답인 이유

PostgreSQL이나 MySQL에 그냥 넣으면 안 되냐? 처음에는 됩니다. **6개월 뒤에 안 됩니다.**

### 일반 RDBMS의 문제

- 센서 1개 × 10초 주기 = 하루 8,640행
- 센서 100개 × 1년 = **3.15억 행**
- B-tree 인덱스가 비대해져 INSERT 성능 급락
- "지난 1주일 시간당 평균"같은 쿼리가 매번 풀스캔

### 시계열 DB가 해결하는 것

| 기능 | 일반 DB | 시계열 DB |
|---|---|---|
| 시간 기반 파티셔닝 | 수동 구성 | 자동 (chunk/shard) |
| 압축 | 없음 | 10~20배 (열 지향) |
| 다운샘플링 | 직접 SQL | Continuous Aggregate / Task |
| 보존 정책 | 직접 DELETE | Retention Policy로 자동 삭제 |

**대표 선택지:**

- **TimescaleDB**: PostgreSQL 확장. 기존 SQL 그대로 쓰고 싶으면 1순위
- **InfluxDB**: 자체 쿼리(Flux/InfluxQL). 작은 농장에 OSS로 띄우기 편함
- **QuestDB / VictoriaMetrics**: 대규모 처리용

### TimescaleDB 실전 스키마

```sql
-- 1. 하이퍼테이블 생성 (시간 기준 자동 파티션)
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ NOT NULL,
    farm_id     INT NOT NULL,
    zone_id     INT NOT NULL,
    sensor_id   TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION,
    co2         DOUBLE PRECISION
);

SELECT create_hypertable('sensor_data', 'time',
    chunk_time_interval => INTERVAL '1 day');

CREATE INDEX ON sensor_data (farm_id, zone_id, time DESC);

-- 2. 압축 정책 (7일 지난 청크 자동 압축)
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id, zone_id, sensor_id'
);
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');

-- 3. 1분 단위 연속 집계 (대시보드는 이 뷰를 조회)
CREATE MATERIALIZED VIEW sensor_data_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    farm_id, zone_id, sensor_id,
    avg(temperature) AS avg_temp,
    max(temperature) AS max_temp,
    min(temperature) AS min_temp
FROM sensor_data
GROUP BY bucket, farm_id, zone_id, sensor_id;

SELECT add_continuous_aggregate_policy('sensor_data_1m',
    start_offset => INTERVAL '1 hour',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

-- 4. 보존 정책 (원본은 90일만, 집계는 영구 보관)
SELECT add_retention_policy('sensor_data', INTERVAL '90 days');
```

이 구조를 잡으면 **"지난 1년간 8월 평균 온도"** 같은 쿼리도 1초 안에 끝납니다. `sensor_data_1m`을 다시 1시간/1일 단위로 cascading 집계하면 더 빨라집니다.

---

## 4. 얼마나 오래 보관해야 하나?

스마트팜에서 데이터는 **목적에 따라 보존 기간이 다릅니다.** 하나의 정책으로 통일하면 비용이 폭발합니다.

### 계층화된 보존 전략 (Hot / Warm / Cold)

```
┌─────────────────────────────────────────────────────┐
│ Hot (7일)   - 원본 raw, 압축 X, 빠른 조회            │
│             - 실시간 대시보드, 알람, 제어 로직       │
├─────────────────────────────────────────────────────┤
│ Warm (90일) - 원본 압축, 1분 집계 활성              │
│             - 주간/월간 리포트, 이상 탐지           │
├─────────────────────────────────────────────────────┤
│ Cold (5년+) - 1시간/1일 집계만 + S3 Parquet 백업    │
│             - 연도별 비교, 작황 분석, 정부 보고서   │
└─────────────────────────────────────────────────────┘
```

**실무 팁**: 농장주가 "작년 이맘때 어땠지?"라고 묻는 빈도는 매우 낮지만, 한 번 물어볼 때 답이 없으면 신뢰를 잃습니다. **원본은 짧게, 집계는 길게** 보관하는 게 정답입니다.

### 용량 추정 예시

- 센서 50개 × 10초 주기 × 8바이트(double) × 6개 채널 = **약 21MB/일**
- 1년치 raw = 7.6GB → TimescaleDB 압축 후 **약 500MB**
- 1분 집계 1년치 = 약 50MB
- 1일 집계 10년치 = 약 1MB

→ 단일 농장은 100GB SSD면 충분합니다. 비용보다 **쿼리 속도**와 **백업 전략**에 집중하세요.

---

## 5. 프론트엔드로 실시간 전달하기 - 무엇을 쓸까

여기서 많은 분들이 헷갈립니다. **WebSocket이 항상 정답은 아닙니다.**

### 옵션 비교

| 방식 | 적합한 상황 | 단점 |
|---|---|---|
| **HTTP Polling** | 1분 이상 주기, 사용자 적음 | 빈번한 요청, 지연 |
| **SSE (Server-Sent Events)** | 서버 → 클라 단방향, 자동 재연결 | 양방향 불가, 일부 모바일 브라우저 이슈 |
| **WebSocket** | 양방향, 다채널, 제어 명령 송신 | 인프라 복잡, 스케일링 시 sticky session 필요 |
| **MQTT over WebSocket** | 브라우저가 직접 브로커 구독 | 인증/권한 설계 필요 |

### 추천 결정 트리

```
프론트가 데이터를 받기만 하나? (제어 안 함)
   ├─ Yes → SSE 추천 (구현 가장 간단)
   └─ No  → WebSocket
              ├─ 양방향 메시지 적음(채팅 X) → 일반 WebSocket
              └─ 토픽이 많고 권한이 복잡 → MQTT over WS
```

대부분의 스마트팜 대시보드는 **SSE로 충분합니다**. "온도 그래프 실시간 업데이트 + 가끔 알람"이라면 WebSocket이 오히려 오버엔지니어링입니다.

### Django + SSE 최소 구현

```python
# views.py - StreamingHttpResponse + Redis Pub/Sub
import json, redis
from django.http import StreamingHttpResponse

r = redis.Redis(host="localhost", decode_responses=True)

def sensor_stream(request, farm_id):
    def event_stream():
        pubsub = r.pubsub()
        pubsub.subscribe(f"farm:{farm_id}:sensor")
        # 최초 진입 시 마지막 값 즉시 전송
        last = r.get(f"farm:{farm_id}:last")
        if last:
            yield f"data: {last}\n\n"
        for msg in pubsub.listen():
            if msg["type"] == "message":
                yield f"data: {msg['data']}\n\n"

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Nginx 버퍼링 방지
    return response
```

```javascript
// 프론트엔드 - 3줄로 끝남
const es = new EventSource(`/api/farms/${farmId}/stream/`);
es.onmessage = (e) => {
    const { temp, humidity, ts } = JSON.parse(e.data);
    chart.append(ts, temp);
};
es.onerror = () => console.log("재연결 자동 처리됨");
```

### MQTT → Redis → SSE 브리지

MQTT 메시지를 받아 Redis로 fan-out하는 작은 워커 하나만 띄우면 됩니다.

```python
# bridge.py - 백그라운드 워커
import paho.mqtt.client as mqtt
import redis, json

r = redis.Redis()

def on_message(client, userdata, msg):
    farm_id = msg.topic.split("/")[1]  # farm/zone1/sensor
    data = msg.payload.decode()
    r.publish(f"farm:{farm_id}:sensor", data)
    r.set(f"farm:{farm_id}:last", data, ex=3600)  # 마지막 값 캐시

client = mqtt.Client()
client.on_message = on_message
client.connect("broker.farm.local")
client.subscribe("farm/+/sensor")
client.loop_forever()
```

---

## 6. 효율적인 스마트팜은 실제로 어떻게 하고 있나

국내외 대형 스마트팜(네덜란드 Priva, 국내 그린플러스, 우듬지팜 등) 운영 패턴을 보면 공통점이 있습니다.

### 공통 패턴 5가지

1. **Edge에서 1차 가공**: 게이트웨이가 평균/이상치를 계산해서 네트워크로 보냄. 클라우드 비용을 70% 이상 절감.

2. **제어 루프와 분석 루프 분리**: 환기창/난방 제어는 게이트웨이 로컬에서 즉시 처리(레이턴시 50ms 이하). 클라우드는 분석/시각화만.

3. **알람은 Push, 그래프는 Pull/Stream**: 임계치 초과는 즉시 푸시 알림(FCM/카카오)으로, 일반 그래프는 SSE로. 채널을 분리해야 알람 누락이 없습니다.

4. **모든 시계열 데이터에 `device_id`와 `firmware_version` 태그**: 센서 교체나 펌웨어 업데이트 시 데이터 단절을 추적할 수 있어야 분석이 신뢰됩니다.

5. **재처리 가능한 파이프라인**: Kafka 또는 MQTT 영구 구독으로 raw 메시지를 7일 이상 보관. 집계 로직 버그 발생 시 다시 돌릴 수 있어야 합니다.

### 실제 사례 - 네덜란드 토마토 농장

- 1ha 온실에 센서 약 800개
- 측정 주기는 센서별로 차등 (광량 1초, 토양 5분)
- TimescaleDB 단일 노드로 운영 (압축 후 연 30GB)
- 대시보드는 Grafana + 자체 React 앱
- React 앱은 **MQTT over WebSocket 직접 구독** (Django 같은 중간 서버 없음)
- 제어는 별도 PLC + OPC-UA, 클라우드는 권고만 내림

여기서 배울 점은 **"센서 → DB → API → 프론트"라는 전형적 흐름을 깨고, 실시간 채널은 별도로 빼는 것**입니다.

---

## 7. 실수하기 쉬운 함정

직접 운영하면서 만나는 실수들입니다.

### ❌ INSERT마다 트랜잭션 커밋

```python
# 안 좋은 예
for sensor in sensors:
    cursor.execute("INSERT ...", sensor)
    conn.commit()  # 매번 커밋 → 디스크 fsync 폭증
```

→ 1초 단위 배치 INSERT 또는 `COPY` 사용. TimescaleDB는 한 번에 1만 행 INSERT가 가장 효율적.

### ❌ 타임존 없는 타임스탬프

`TIMESTAMP WITHOUT TIME ZONE`으로 저장하면 서버 이전, DST 처리에서 반드시 사고가 납니다. **항상 `TIMESTAMPTZ` + UTC 저장**.

### ❌ WebSocket 한 연결에 모든 토픽

대시보드가 5개 페이지인데 센서 200개를 모두 한 WebSocket으로 밀면, 사용자가 페이지 하나만 열어도 200개 데이터를 다 받습니다. **페이지/구역별로 토픽 분리** 또는 **클라이언트 구독 메시지로 필터링**.

### ❌ 다운샘플링 없이 차트 그리기

브라우저에 1주일치 1초 데이터(60만 포인트)를 보내면 Canvas가 멈춥니다. **서버에서 화면 픽셀 수에 맞춰 LTTB 다운샘플링** 후 전송하세요.

```sql
-- TimescaleDB의 LTTB 함수
SELECT time, value FROM unnest(
    (SELECT lttb(time, temperature, 1000)
     FROM sensor_data
     WHERE farm_id = 1 AND time > now() - INTERVAL '7 days')
);
```

---

## 8. 정리 - 단계별 체크리스트

스마트팜을 처음 설계한다면 다음 순서로 가세요.

- [ ] 센서별 측정 주기를 환경 변화 속도에 맞게 차등 설정
- [ ] 게이트웨이에서 deadband 필터 + MQTT QoS 1로 전송
- [ ] TimescaleDB 하이퍼테이블 + 1분 연속 집계 + 7일 압축 정책
- [ ] 원본 90일 / 집계 5년 / S3 Parquet 백업의 3계층 보존
- [ ] 실시간 채널은 SSE를 1순위 검토, 양방향 필요 시 WebSocket
- [ ] MQTT → Redis Pub/Sub → SSE/WebSocket 브리지 워커 분리
- [ ] 알람은 별도 Push 채널, 임계치 로직은 Edge에서
- [ ] 모든 시계열에 `device_id`, `firmware_version` 태그
- [ ] 차트는 LTTB 다운샘플링으로 1000포인트 이하

---

## 마치며

스마트팜 데이터 시스템의 본질은 **"실시간성"과 "장기 분석"이라는 서로 다른 요구를 한 파이프라인에서 풀려고 하지 않는 것**입니다. 측정 주기, 저장 형식, 보존 기간, 전달 채널을 모두 분리해서 설계해야 합니다.

작게 시작한다면 **MQTT + TimescaleDB + Django SSE** 조합으로 충분합니다. 농장이 커지면 Kafka, 분산 처리, MQTT over WebSocket으로 점진적으로 확장하세요. 처음부터 Kafka를 끌고 오는 건 99% 오버엔지니어링입니다.

다음 포스트에서는 이 아키텍처 위에 **이상 탐지(Anomaly Detection)와 예측 제어**를 얹는 방법을 다뤄보겠습니다.
