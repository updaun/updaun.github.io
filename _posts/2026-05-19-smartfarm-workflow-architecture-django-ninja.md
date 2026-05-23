---
layout: post
title: "스마트팜 워크플로우 아키텍처 설계 — 센서·제어·LLM을 Django Ninja로 모델링하기"
date: 2026-05-19
categories: [iot, django, architecture]
tags: [smartfarm, workflow, django-ninja, iot, node-red, n8n, llm]
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-05-19-smartfarm-workflow-architecture-django-ninja.webp"
---

# 스마트팜 워크플로우 아키텍처 설계 — 센서·제어·LLM을 Django Ninja로 모델링하기

최근 n8n, Make, Retool 같은 **워크플로우 UI**를 쓰는 서비스들을 보면, 복잡한 로직을 코드 없이 한눈에 이해할 수 있다는 점이 인상적이었습니다.

스마트팜에 이 패턴을 적용하면 이런 그림이 그려집니다.

> 온실 A동 온도가 28℃를 넘으면 → 환기창 30% 개방 → 5분 후에도 27℃ 이상이면 → 알람 + 난방 OFF

이걸 **if-else 코드**로만 관리하면, 농장주·현장 기사·개발자 모두 같은 파일을 열어야 합니다. 워크플로우 UI라면 **센서 → 조건 → 액추에이터** 흐름을 캔버스에서 보고, 슬라이더로 임계값을 바꿔가며 즉시 시험해 볼 수 있습니다. 여기에 **"28도 넘으면 환기창 열어줘"** 라고 말하면 LLM이 그래프를 편집해 주면, 비개발자도 운영할 수 있는 제어 패널이 됩니다.

이번 글은 그 아이디어를 **Django Ninja로 API·스키마를 어떻게 모델링할지**, 그리고 **노드 간 관계·통신**을 어떻게 설계할지 고민한 설계 노트입니다. (이전 글 [스마트팜 센서 데이터 아키텍처](/iot/2026/05/06/smartfarm-sensor-realtime-architecture/)가 **데이터 수집·실시간 표시**였다면, 이번 글은 **제어 로직의 구조화**에 초점을 둡니다.)

---

## 1. 다른 사람들은 어떻게 하나 — 자료 조사 요약

워크플로우 기반 자동화는 이미 IoT·업무 자동화 양쪽에서 검증된 패턴입니다. 대표 사례를 스마트팜 관점에서만 정리했습니다.

| 플랫폼 | 강점 | 데이터 모델 특징 | 스마트팜에 빌려올 점 |
|--------|------|------------------|----------------------|
| **[Node-RED](https://nodered.org/)** | MQTT·Modbus 등 IoT 노드 풍부, 엣지·게이트웨이 배포 | 노드 배열 + `wires`로 출력 포트 연결 | **플랫 JSON**, 로컬 실행, 브로커 config 노드 분리 |
| **[n8n](https://n8n.io/)** | SaaS 통합·조건 분기·실행 이력 | Directed graph, 노드 간 **item 배열** (`json`/`binary`) | **스택 기반 실행 엔진**, 부분 실행, 멀티 입력 join |
| **[Losant](https://docs.losant.com/workflows/overview)** | IoT 네이티브, 디바이스 state 트리거 | Device State Trigger → Logic → Device State Output | **속성(attribute) 단위 필터**, 무한 루프 방지 필터 |
| **[AWS IoT Things Graph](https://aws.amazon.com/iot-things-graph/)** | 디바이스 모델 시각 연결 | Flow + Thing 모델, 상태 추적·재시도 | **디바이스 추상화**와 워크플로우 분리 |
| **Priva / 그린플러스류** | 상용 온실 제어 | UI는 폐쇄, 내부는 룰 엔진 + 로컬 제어 | **제어 루프는 엣지**, 클라우드는 설정·이력 |

### 공통으로 반복되는 설계 원칙

1. **그래프 = 노드(정점) + 엣지(연결)** — UI 좌표(`x`, `y`)와 실행 그래프는 분리 저장하는 경우가 많음.
2. **트리거와 액션을 분리** — "언제 돌릴까"(센서 이벤트, cron, 수동)와 "무엇을 할까"(MQTT publish, HTTP, DB)를 다른 노드 타입으로 둠.
3. **실행 컨텍스트** — 한 번의 실행(run)마다 `payload`, `variables`, `trace`를 들고 다음 노드로 전달.
4. **안전장치** — 사이클 검출, 최대 실행 횟수, 디바이스 피드백 루프 방지(Losant의 attribute 필터처럼).

n8n은 내부적으로 **DirectedGraph**와 **실행 스택**으로 워크플로우를 돌립니다. Node-RED는 **단순한 `wires` 배열**이지만, IoT 현장에서는 오히려 이 단순함이 배포·디버깅에 유리합니다. 스마트팜 MVP는 Node-RED에 가까운 단순 그래프 + Losant식 디바이스 state 모델을 섞는 쪽이 현실적입니다.

---

## 2. 스마트팜 워크플로우가 풀어야 할 문제

### 사용자 시나리오

| 역할 | 하고 싶은 일 |
|------|-------------|
| 농장주 | "습도 80% 넘으면 제습기 켜줘"를 말로 설정 |
| 현장 기사 | 캔버스에서 임계값 슬라이더로 조정, **시뮬레이션** 후 배포 |
| 개발자 | 새 센서 타입·액추에이터를 **노드 플러그인**으로 추가 |

### 기술적 제약

- **제어 지연**: 환기·난방은 수백 ms 안에 반응해야 함 → [이전 아키텍처 글](/iot/2026/05/06/smartfarm-sensor-realtime-architecture/)처럼 **엣지(게이트웨이)에서 1차 실행**, 클라우드는 정책 동기화.
- **실패 시 동작**: 브로커 끊김 시 **안전 기본값**(fail-safe) — 예: 환기창 일부 개방.
- **감사·롤백**: 누가 어떤 룰을 언제 바꿨는지, 실행당 입·출력 스냅샷.

---

## 3. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  프론트 (React Flow 등)                                          │
│  - 캔버스 편집 / 슬라이더로 파라미터 실시간 수정                    │
│  - 실행 시뮬레이션 / 배포 버튼                                    │
│  - 자연어 → LLM → graph JSON patch                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST (Django Ninja)
┌───────────────────────────▼─────────────────────────────────────┐
│  Control Plane (Django)                                          │
│  - Workflow / Node / Edge CRUD                                     │
│  - 버전·배포·권한                                                  │
│  - LLM Orchestrator (graph diff 생성 → 검증 → 저장)               │
└───────────────┬─────────────────────────────┬───────────────────┘
                │ deploy (MQTT / HTTP)          │ execution logs
┌───────────────▼──────────────┐   ┌────────────▼──────────────────┐
│  Edge Runtime (게이트웨이)     │   │  Observability               │
│  - 컴파일된 룰 캐시            │   │  TimescaleDB / Redis stream  │
│  - 센서 subscribe → run       │   │  WebSocket/SSE 실행 상태      │
│  - 액추에이터 publish          │   └──────────────────────────────┘
└───────────────┬──────────────┘
                │ MQTT
┌───────────────▼──────────────┐
│  센서 / 환기창 / 난방 / CO₂   │
└──────────────────────────────┘
```

**핵심 분리**

| 레이어 | 책임 |
|--------|------|
| **Editor graph** | UI용 `position`, `viewport`, 주석 |
| **Execution graph** | 런타임용 topology + `config` + `compiled` 표현 |
| **Runtime** | 이벤트 수신 → DAG/룰 평가 → 디바이스 명령 |

프론트가 보내는 React Flow 형식(`nodes`, `edges`)을 그대로 DB에 넣지 말고, **정규화된 WorkflowDefinition**으로 변환해 저장하는 편이 장기적으로 안전합니다.

---

## 4. 노드 타입과 관계 — 무엇을 연결할 것인가

### 4.1 노드 카테고리 (스마트팜용)

```text
[Trigger]     sensor_threshold, schedule_cron, manual_run, mqtt_message
[Condition]   compare, range, and_or, debounce, rate_limit
[Transform]   moving_avg, unit_convert, map_zone
[Action]      actuator_command, notification, log_only, webhook
[Flow]        delay, branch, merge (join), sub_workflow
[AI]          llm_summarize, llm_classify  (운영 리포트용, 제어 직결은 신중히)
```

### 4.2 포트(Port)와 엣지(Edge)

n8n처럼 **출력 포트가 여러 개**인 노드가 필요합니다.

| 노드 | 출력 포트 | 의미 |
|------|-----------|------|
| `compare` | `true`, `false` | 조건 분기 |
| `debounce` | `passed`, `suppressed` | 노이즈 필터 통과 여부 |
| `actuator_command` | `success`, `error` | 제어 성공/실패 |

엣지 메타데이터 예:

```json
{
  "source_node_id": "n_compare_1",
  "source_port": "true",
  "target_node_id": "n_vent_1",
  "target_port": "in"
}
```

Node-RED의 `wires: [["id1"], ["id2"]]`는 **포트 인덱스**로 분기를 표현합니다. 스마트팜에서는 **이름 있는 포트**가 디버깅에 유리합니다.

### 4.3 노드 간 "통신" — 메시지가 아니라 실행 컨텍스트

노드끼리 HTTP로 직접 부르지 않습니다. **실행 엔진이 하나의 `ExecutionContext`를 들고 순회**합니다.

```python
# 개념 모델 (런타임 내부)
@dataclass
class ExecutionContext:
    run_id: str
    workflow_id: str
    workflow_version: int
    triggered_at: datetime
    trigger: dict          # {"type": "sensor", "device_id": "...", "metric": "temp"}
    payload: dict          # 현재 노드까지 누적된 데이터
    variables: dict        # 워크플로우 전역 변수 (카운터, 마지막 명령 시각)
    trace: list[dict]      # 노드별 입출력 (디버그·감사)
```

**한 노드의 출력**은 다음 형태로 통일하는 것을 권장합니다 (n8n의 item 배열을 단순화):

```json
{
  "items": [
    {
      "zone_id": "A",
      "temp": 28.4,
      "humidity": 72.1,
      "ts": 1716100000000
    }
  ],
  "meta": { "source_node": "n_sensor_1" }
}
```

| 통신 방식 | 쓰는 곳 | 설명 |
|-----------|---------|------|
| **In-process context** | 엣지 런타임, Celery 워커 | 같은 프로세스/태스크 안에서 `payload` 전달 |
| **MQTT** | 센서 → 런타임, 런타임 → 액추에이터 | 물리 디바이스와의 경계 |
| **Redis Pub/Sub** | 클라우드 ↔ UI 실시간 실행 로그 | [센서 실시간 글](/iot/2026/05/06/smartfarm-sensor-realtime-architecture/)의 SSE 브리지와 동일 패턴 |
| **DB append** | 실행 이력, 감사 | `WorkflowRun`, `NodeExecution` 테이블 |

---

## 5. Django 모델 — 데이터 구조

### 5.1 ER 개요

```text
Farm ─┬─ Zone ─┬─ Device (sensor | actuator)
      │        └─ DeviceBinding (topic, metric_key)
      │
      └─ Workflow ─┬─ WorkflowVersion (graph snapshot, status)
                   ├─ WorkflowNode
                   ├─ WorkflowEdge
                   └─ WorkflowDeployment (edge_gateway_id, compiled_rules)

WorkflowRun ─ NodeExecution
```

### 5.2 핵심 모델

```python
# apps/control/models.py
from django.db import models
import uuid

class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE)
    zone = models.ForeignKey("farms.Zone", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class WorkflowVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"
        ARCHIVED = "archived"

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
  # UI 원본 + 실행용 정규화 그래프 (분리 저장 권장)
    editor_state = models.JSONField(default=dict)   # React Flow export
    definition = models.JSONField(default=dict)     # nodes/edges 정규화
    compiled = models.JSONField(default=dict)       # 엣지 런타임용 (optional)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("workflow", "version")

class WorkflowNode(models.Model):
    class NodeKind(models.TextChoices):
        TRIGGER = "trigger"
        CONDITION = "condition"
        TRANSFORM = "transform"
        ACTION = "action"
        FLOW = "flow"

    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="nodes")
    node_key = models.CharField(max_length=64)  # 그래프 내 stable id (n_compare_1)
    kind = models.CharField(max_length=20, choices=NodeKind.choices)
    type = models.CharField(max_length=64)      # sensor_threshold, actuator_command, ...
    config = models.JSONField(default=dict)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)

    class Meta:
        unique_together = ("version", "node_key")

class WorkflowEdge(models.Model):
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="edges")
    source_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="out_edges")
    target_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="in_edges")
    source_port = models.CharField(max_length=32, default="out")
    target_port = models.CharField(max_length=32, default="in")

class WorkflowRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"
        CANCELLED = "cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(WorkflowVersion, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices)
    trigger_payload = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

class NodeExecution(models.Model):
    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="steps")
    node_key = models.CharField(max_length=64)
    status = models.CharField(max_length=20)
    input_payload = models.JSONField(default=dict)
    output_payload = models.JSONField(default=dict)
    duration_ms = models.PositiveIntegerField(null=True)
    executed_at = models.DateTimeField(auto_now_add=True)
```

**왜 `WorkflowVersion`을 두나**

- 캔버스에서 슬라이더를 움직이는 동안은 **DRAFT**만 수정.
- **배포** 시 `PUBLISHED` 스냅샷을 엣지에 push → 실행 중인 농장은 항상 고정 버전 참조.
- 롤백 = 이전 `version`을 다시 publish.

---

## 6. Django Ninja — API·스키마 모델링

### 6.1 Pydantic 스키마 (프론트 ↔ 백엔드 계약)

```python
# apps/control/schemas.py
from ninja import Schema
from typing import Literal, Any
from uuid import UUID

class NodePositionSchema(Schema):
    x: float
    y: float

class WorkflowNodeSchema(Schema):
    id: str
    kind: Literal["trigger", "condition", "transform", "action", "flow"]
    type: str
    config: dict[str, Any]
    position: NodePositionSchema

class WorkflowEdgeSchema(Schema):
    id: str
    source: str
    target: str
    source_port: str = "out"
    target_port: str = "in"

class WorkflowDefinitionSchema(Schema):
    nodes: list[WorkflowNodeSchema]
    edges: list[WorkflowEdgeSchema]

class WorkflowVersionOutSchema(Schema):
    workflow_id: UUID
    version: int
    status: str
    definition: WorkflowDefinitionSchema
    updated_at: str | None = None

class WorkflowVersionInSchema(Schema):
    definition: WorkflowDefinitionSchema
    editor_state: dict[str, Any] | None = None

# 노드별 config 검증 — 타입별로 쪼개면 LLM 출력 검증에도 유리
class SensorThresholdConfig(Schema):
    device_id: str
    metric: Literal["temp", "humidity", "co2", "par"]
    operator: Literal["gt", "gte", "lt", "lte", "between"]
    value: float
    value_high: float | None = None
    debounce_seconds: int = 0

class ActuatorCommandConfig(Schema):
    device_id: str
    command: Literal["set_position", "on", "off", "pulse"]
    params: dict[str, Any]  # {"position_pct": 30}
    safe_mode_fallback: dict[str, Any] | None = None
```

### 6.2 API 라우터

```python
# apps/control/api.py
from ninja import Router
from ninja.errors import HttpError
from uuid import UUID
from .models import Workflow, WorkflowVersion
from .schemas import WorkflowVersionInSchema, WorkflowVersionOutSchema
from .services import validate_graph, compile_graph, publish_version

router = Router(tags=["workflows"])

@router.get("/workflows/{workflow_id}/versions/{version}", response=WorkflowVersionOutSchema)
def get_version(request, workflow_id: UUID, version: int):
    wv = WorkflowVersion.objects.select_related("workflow").get(
        workflow_id=workflow_id, version=version
    )
    return {
        "workflow_id": workflow_id,
        "version": wv.version,
        "status": wv.status,
        "definition": wv.definition,
        "updated_at": wv.published_at.isoformat() if wv.published_at else None,
    }

@router.put("/workflows/{workflow_id}/versions/{version}", response=WorkflowVersionOutSchema)
def save_draft(request, workflow_id: UUID, version: int, payload: WorkflowVersionInSchema):
    wv = WorkflowVersion.objects.get(workflow_id=workflow_id, version=version)
    if wv.status != WorkflowVersion.Status.DRAFT:
        raise HttpError(409, "Published version cannot be edited directly")

    errors = validate_graph(payload.definition)
    if errors:
        raise HttpError(422, {"validation_errors": errors})

    wv.definition = payload.definition.model_dump()
    if payload.editor_state:
        wv.editor_state = payload.editor_state
    wv.save(update_fields=["definition", "editor_state"])
    return get_version(request, workflow_id, version)

@router.post("/workflows/{workflow_id}/versions/{version}/publish")
def publish(request, workflow_id: UUID, version: int):
    wv = WorkflowVersion.objects.get(workflow_id=workflow_id, version=version)
    compiled = compile_graph(wv.definition)
    wv.compiled = compiled
    wv.status = WorkflowVersion.Status.PUBLISHED
    wv.save()
    publish_version(wv)  # MQTT: farm/{id}/workflows/{wf_id}/config
    return {"ok": True, "compiled_hash": compiled.get("hash")}
```

### 6.3 그래프 검증 (`validate_graph`)

배포 전에 반드시 막아야 할 것들:

```python
# apps/control/services/validation.py
def validate_graph(defn) -> list[str]:
    errors: list[str] = []
    node_ids = {n.id for n in defn.nodes}
    triggers = [n for n in defn.nodes if n.kind == "trigger"]

    if len(triggers) != 1:
        errors.append("workflow must have exactly one trigger node")

    for e in defn.edges:
        if e.source not in node_ids or e.target not in node_ids:
            errors.append(f"edge references unknown node: {e.id}")
        if e.source == e.target:
            errors.append(f"self-loop not allowed: {e.id}")

    if has_cycle(defn):
        errors.append("cycle detected in workflow graph")

    for n in defn.nodes:
        if n.type == "sensor_threshold":
            cfg = SensorThresholdConfig(**n.config)  # pydantic 검증
        elif n.type == "actuator_command":
            ActuatorCommandConfig(**n.config)

    return errors
```

### 6.4 시뮬레이션 API — "슬라이더로 값 바꿔보며 제어"

실제 액추에이터에 명령을 내리지 않고, **가상 센서값**으로 그래프만 태워 보는 엔드포인트입니다.

```python
@router.post("/workflows/{workflow_id}/versions/{version}/simulate")
def simulate(request, workflow_id: UUID, version: int, payload: SimulateInSchema):
    """
    payload.example:
    {
      "inject": {"zone_id": "A", "temp": 29.1, "humidity": 81},
      "dry_run": true
    }
    """
    wv = WorkflowVersion.objects.get(workflow_id=workflow_id, version=version)
    result = run_workflow(wv.compiled or compile_graph(wv.definition), payload.inject, dry_run=True)
    return {"steps": result.trace, "actions": result.planned_actions}
```

프론트는 슬라이더 `onChange`마다 debounce 300ms로 이 API를 호출하면, **캔버스 위 노드가 하이라이트**되며 어떤 분기를 탔는지 보여 줄 수 있습니다.

---

## 7. 실행 엔진 — 노드 순회 알고리즘

### 7.1 컴파일 결과 예시

`compile_graph`는 런타임이 빠르게 돌 수 있게 **인접 리스트 + 트리거 매핑**을 만듭니다.

```json
{
  "hash": "a1b2c3",
  "entry": "n_trigger_1",
  "nodes": {
    "n_trigger_1": {"type": "sensor_threshold", "config": {...}, "next": {"default": "n_compare_1"}},
    "n_compare_1": {"type": "compare", "next": {"true": "n_vent_1", "false": "n_end"}},
    "n_vent_1": {"type": "actuator_command", "config": {...}, "next": {"default": "n_end"}}
  }
}
```

### 7.2 실행 루프 (의사 코드)

n8n·auxx.ai 등에서 흔히 쓰는 **while-loop + 명시적 next** 패턴입니다. 재귀보다 긴 워크플로우·취소에 유리합니다.

```python
MAX_STEPS = 200

def run_workflow(compiled: dict, inject: dict, dry_run: bool = False) -> RunResult:
    ctx = ExecutionContext(payload={"items": [inject]}, variables={}, trace=[])
    current = compiled["entry"]
    steps = 0

    while current and steps < MAX_STEPS:
        node = compiled["nodes"][current]
        handler = NODE_REGISTRY[node["type"]]
        out = handler.run(node["config"], ctx, dry_run=dry_run)
        ctx.trace.append({"node": current, "out": out.status, "payload": out.payload})

        if out.stop:
            break
        current = node["next"].get(out.port) or node["next"].get("default")
        ctx.payload = out.payload
        steps += 1

    return RunResult(trace=ctx.trace, planned_actions=out.actions if dry_run else [])
```

### 7.3 `debounce` / `delay` 노드

- **debounce**: `variables[last_fired_at]`와 비교해 N초 내 재트리거 억제 (Losant식 "너무 자주 도는 워크플로" 방지).
- **delay**: 엣지에서는 `asyncio.sleep` / Celery `countdown` — **제어 루프에 delay가 길면 클라우드가 아니라 엣지 스케줄러**에 넣는 게 맞습니다.

### 7.4 멀티 입력 Join (n8n 패턴)

"온도 조건 **AND** 습도 조건"을 합류시키려면 **merge 노드**가 두 입력을 모두 받을 때까지 `waiting` 큐에 둡니다. MVP에서는 **단일 compare 체인**으로 피하고, v2에서 join을 도입해도 늦지 않습니다.

---

## 8. LLM으로 자연어 → 워크플로우 편집

### 8.1 파이프라인

```text
사용자 발화
  → LLM (structured output: GraphPatch[])
  → validate_graph(merged_definition)
  → 실패 시 LLM에 에러 메시지 feedback (최대 2회)
  → 성공 시 DRAFT version 저장 + diff 요약 반환
```

**GraphPatch** 예 — 전체 그래프를 매번 생성하지 말고 **변경 조각**만:

```json
{
  "patches": [
    {
      "op": "upsert_node",
      "node": {
        "id": "n_compare_temp",
        "kind": "condition",
        "type": "sensor_threshold",
        "config": {"device_id": "temp-A1", "metric": "temp", "operator": "gt", "value": 28}
      }
    },
    {
      "op": "upsert_edge",
      "edge": {"id": "e1", "source": "n_trigger_zone", "target": "n_compare_temp", "source_port": "out", "target_port": "in"}
    }
  ],
  "summary_ko": "A동 온도 28℃ 초과 시 환기창 30% 개방 룰을 추가했습니다."
}
```

### 8.2 Django Ninja + LLM 엔드포인트

```python
class NaturalLanguageEditIn(Schema):
    message: str
    workflow_id: UUID
    base_version: int

class NaturalLanguageEditOut(Schema):
    version: int
    summary: str
    definition: WorkflowDefinitionSchema
    validation_warnings: list[str] = []

@router.post("/workflows/nl-edit", response=NaturalLanguageEditOut)
def nl_edit(request, payload: NaturalLanguageEditIn):
    base = WorkflowVersion.objects.get(
        workflow_id=payload.workflow_id, version=payload.base_version
    )
    patches = llm_generate_patches(
        user_message=payload.message,
        current_definition=base.definition,
        device_catalog=list_devices(payload.workflow_id),
    )
    merged = apply_patches(base.definition, patches)
    errors = validate_graph(WorkflowDefinitionSchema(**merged))
    if errors:
        patches = llm_fix_patches(payload.message, merged, errors)
        merged = apply_patches(base.definition, patches)
        errors = validate_graph(WorkflowDefinitionSchema(**merged))
        if errors:
            raise HttpError(422, {"validation_errors": errors})

    new_version = clone_as_draft(base, merged)
    return {
        "version": new_version.version,
        "summary": patches.summary_ko,
        "definition": merged,
    }
```

### 8.3 LLM에 넘길 컨텍스트

| 포함 | 이유 |
|------|------|
| 현재 `definition` JSON | 수정 기준 |
| `device_catalog` (id, type, zone, metric) | 환각 device_id 방지 |
| 허용 `node types` + config JSON Schema | structured output 범위 제한 |
| **금지 규칙** (예: 난방 OFF + 환기 100% 동시) | 안전 정책 |

제어에 직결되는 명령은 **LLM이 액추에이터 MQTT를 직접 쏘지 않게** 하고, 반드시 `validate_graph` → `publish` → 엣지 런타임 경로만 타게 합니다. ([Django Ninja AI 통합 가이드](/django/2026/01/25/django-ninja-ai-integration-guide/)에서 다룬 structured output·에러 핸들링 패턴을 그대로 적용하면 됩니다.)

---

## 9. 스마트팜 예시 워크플로우 (개념)

```text
[sensor_threshold: temp-A1 > 28℃]
        │ true
        ▼
[debounce: 60s]
        │ passed
        ▼
[actuator_command: vent-A1 set_position 30%]
        │
        ▼
[delay: 5min]
        │
        ▼
[sensor_threshold: temp-A1 > 27℃]  ← 여전히 높으면
        │ true
        ▼
[notification: slack #farm-alerts]
```

MQTT 토픽 설계는 [센서 아키텍처 글](/iot/2026/05/06/smartfarm-sensor-realtime-architecture/)의 `farm/{zone}/sensor`와 맞추고, 제어는 `farm/{zone}/actuator/{id}/command`로 분리합니다.

---

## 10. 아직 열어둔 질문들 (고민 메모)

| 주제 | 선택지 | 현재 leaning |
|------|--------|----------------|
| 그래프 저장 | JSON blob only vs Node/Edge 테이블 | **버전 스냅샷은 JSON**, 검색·감사 필요 노드만 테이블 |
| 실행 위치 | 클라우드 only vs 엣지 primary | **엣지 primary**, 클라우드는 시뮬·이력 |
| 실시간 UI | 폴링 vs SSE vs WS | 실행 로그는 **SSE**, 제어 명령은 **MQTT/WS** |
| LLM 역할 | 그래프 편집 only vs 런타임 노드 | **편집 only** (v1), 분석 리포트는 v2 |
| 버전 동시 편집 | optimistic lock vs CRDT | **version + etag** 낙관적 잠금 |

---

## 11. MVP 구현 순서 제안

1. **WorkflowVersion + definition JSON** CRUD (Django Ninja)
2. **validate_graph + simulate** (dry_run)
3. **compile → MQTT deploy** to gateway
4. **엣지 런타임** Python/Node 소형 인터프리터
5. **React Flow** 캔버스 + simulate 하이라이트
6. **nl-edit** LLM 패치 (device_catalog 필수)

---

## 12. 정리

워크플로우 UI는 스마트팜에서 **"센서 → 조건 → 제어"를 한 화면에**, **슬라이더·시뮬레이션으로 안전하게**, **자연어로 진입 장벽을 낮추는** 인터페이스입니다. 구현의 본질은 예쁜 캔버스가 아니라 **(1) 정규화된 그래프 데이터**, **(2) 검증 가능한 배포 파이프라인**, **(3) 엣지 친화 실행 엔진**, **(4) 감사 가능한 실행 이력**입니다.

Node-RED의 단순한 `wires`, n8n의 실행 스택, Losant의 device state 트리거에서 각각 한 가지씩 가져오면, Django Ninja 위에 **스마트팜 전용 제어 플레인**을 단계적으로 쌓을 수 있습니다.

---

## 참고 자료

- [Node-RED Flow Format](https://github.com/node-red/node-red/wiki/Flow-Format)
- [n8n Data structure](https://docs.n8n.io/data/data-structure/)
- [Losant Workflows Overview](https://docs.losant.com/workflows/overview)
- [Losant Device State Trigger](https://docs.losant.com/workflows/triggers/device-state)
- [Building a Visual Workflow Engine (Part 1 & 2) — auxx.ai](https://auxx.ai/blog/workflows-part-1-visual-editor)
- [이 블로그: n8n 워크플로우 자동화 가이드](/automation/2026/03/03/n8n-workflow-automation-guide/)
- [이 블로그: 스마트팜 센서 실시간 아키텍처](/iot/2026/05/06/smartfarm-sensor-realtime-architecture/)
