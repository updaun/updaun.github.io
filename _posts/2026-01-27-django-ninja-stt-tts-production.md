---
layout: post
title: "Django Ninja로 STT/TTS 파이프라인 구축 - 실서비스 아키텍처와 코드 예시"
date: 2026-01-27
categories: django
author: updaun
image: "/assets/img/posts/2026-01-27-django-ninja-stt-tts-production.webp"
---

# Django Ninja로 STT/TTS 파이프라인 구축 - 실서비스 아키텍처와 코드 예시

보이스 퍼스트 경험이 늘면서 웹 API 수준에서 안정적으로 음성 인식(STT)과 음성 합성(TTS)을 처리할 수 있는 백엔드가 중요해졌습니다. 이 글에서는 Django Ninja를 기반으로, 실서비스에서 바로 활용할 수 있는 STT/TTS 워크플로우를 설계하고 구현하는 방법을 단계별로 정리합니다. 단순 데모가 아닌, 대규모 요청을 견딜 수 있는 모듈 선택 기준(예: OpenAI Whisper·Deepgram STT, Amazon Polly·OpenAI TTS), 비동기 처리 전략, 보안·모니터링까지 다룹니다. 다음 단락부터는 선택 가능한 모듈과 실제 서비스 품질을 위해 고려할 요소를 하나씩 살펴보겠습니다.

## 모듈 선택 기준과 후보
정확도(한국어·영어 인식률), 지연 시간, 비용, 콘텐츠 안전성, 장기 운영 지원 여부가 핵심입니다. STT는 오픈소스 가중치 기반의 OpenAI Whisper(로컬·GPU), 실시간 스트리밍에 강한 Deepgram·AssemblyAI(네이티브 스트리밍), 안정적 SLA가 있는 Google Cloud Speech를 주로 씁니다. TTS는 자연스러운 한국어 톤과 캐시 전략을 고려해 Amazon Polly(가격·언어 안정성), OpenAI TTS(고품질·속도), Azure Speech(SSML 유연성) 중 하나를 고릅니다. 회사 보안 정책에 따라 온프레미스가 필요하면 Whisper를, 낮은 지연과 운영 편의성이 필요하면 AssemblyAI·Deepgram STT와 Polly·OpenAI TTS 조합이 현실적입니다.

## 요청 흐름 아키텍처
모바일·웹 클라이언트는 Presigned URL로 음성을 업로드 → Django Ninja는 업로드 위치를 검증 후 작업을 Celery+Redis 큐에 위임 → 워커가 STT/TTS API를 호출하고 결과를 S3에 저장 → 결과 URL 또는 텍스트를 Webhook·폴링 API로 전달하는 구조가 안전합니다. 실시간 필요 시 WebSocket(uvicorn)이나 Server-Sent Events로 중간 Partial 결과를 스트리밍하고, 장기 보관이 필요 없으면 만료 시간이 짧은 Signed URL을 발급해 저장 비용을 줄입니다.

## 의존성과 설정
프로덕션에서 권장하는 최소 의존성은 다음과 같습니다.

```
pip install django-ninja uvicorn[standard] httpx celery redis boto3 python-dotenv
```

`settings.py`에는 Redis 브로커, S3 자격 증명, 외부 STT/TTS API 키를 환경 변수로 분리하고, Ninja `API` 인스턴스는 전역으로 두어 라우터에서 공유합니다.

## Django Ninja STT 엔드포인트 (AssemblyAI 예시)
AssemblyAI의 `transcribe` 엔드포인트를 비동기 호출하고, 완료되면 결과를 반환하거나 Webhook으로 통지하는 예시입니다.

```python
# app/api.py
from ninja import NinjaAPI, Schema
import httpx
import os

api = NinjaAPI()

class STTRequest(Schema):
    media_url: str
    webhook_url: str | None = None

class STTResponse(Schema):
    transcript_id: str
    status: str

@api.post("/stt", response=STTResponse)
async def create_transcription(request, payload: STTRequest):
    headers = {"authorization": os.environ["ASSEMBLYAI_API_KEY"]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            json={"audio_url": payload.media_url, "webhook_url": payload.webhook_url},
            headers=headers,
        )
    resp.raise_for_status()
    data = resp.json()
    return {"transcript_id": data["id"], "status": data["status"]}
```

웹훅을 수신하는 라우트에서는 transcript `status`가 `completed`일 때 `text` 필드를 저장하고, 실패 시 재시도 로직을 Celery 작업으로 위임합니다.

## TTS 엔드포인트 (Amazon Polly 예시)
짧은 문장은 동기 응답, 긴 문장은 비동기로 돌려 S3에 저장한 뒤 URL을 반환하는 방식이 운영에 적합합니다.

```python
# app/tts.py
from ninja import Router, Schema
import boto3
import os, uuid

router = Router()

class TTSRequest(Schema):
    text: str
    voice_id: str = "Seoyeon"
    output_bucket: str | None = None

class TTSResponse(Schema):
    audio_url: str

polly = boto3.client("polly", region_name=os.getenv("AWS_REGION", "ap-northeast-2"))

@router.post("/tts", response=TTSResponse)
def synthesize(request, payload: TTSRequest):
    ssml = f"<speak>{payload.text}</speak>"
    result = polly.synthesize_speech(
        TextType="ssml",
        Text=ssml,
        OutputFormat="mp3",
        VoiceId=payload.voice_id,
    )
    audio_stream = result["AudioStream"].read()
    key = f"tts/{uuid.uuid4()}.mp3"
    bucket = payload.output_bucket or os.environ["DEFAULT_TTS_BUCKET"]
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=audio_stream, ContentType="audio/mpeg")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
    return {"audio_url": url}
```

이 라우터를 `api.add_router("", router)`로 연결하면 `/api/tts`로 사용 가능합니다. 1시간 만료 Presigned URL을 반환해 불필요한 퍼블릭 공개를 막고, TTL을 짧게 관리합니다.

## 운영 품질 체크리스트
로그·메트릭: STT/TTS 호출 시간, 성공률, 에러 코드, 평균 오디오 길이. 보안: API 키는 KMS·Secrets Manager에 저장, IP allowlist와 HMAC 서명 검증(Webhook). 비용: 긴 오디오는 16kHz 모노로 리샘플링 후 업로드, 재사용 가능한 캐시 키(text+voice)로 TTS 결과를 저장. 회복력: 외부 API 5xx 시 지수 백오프, Circuit Breaker, Dead Letter Queue 구성. 지연: 실시간이 필요하면 AssemblyAI streaming WebSocket을 Ninja의 `lifespan`에서 uvicorn `websockets`로 병행 구성합니다.

## AssemblyAI WebSocket 스트리밍 샘플
실시간 자막·콜센터 분석에는 WebSocket이 필요합니다. uvicorn에서 동작하는 간단한 핸들러 예시입니다. 오디오를 16kHz mono PCM으로 잘라 전송합니다.

```python
# app/ws.py
import asyncio
import os
import websockets
import json

ASSEMBLY_ENDPOINT = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

async def stream_audio(audio_chunks):
    async with websockets.connect(
        ASSEMBLY_ENDPOINT,
        extra_headers={"Authorization": os.environ["ASSEMBLYAI_API_KEY"]},
    ) as ws:
        await ws.send(json.dumps({"audio_format": "pcm_s16le", "sample_rate": 16000}))
        for chunk in audio_chunks:
            await ws.send(chunk)
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("message_type") == "PartialTranscript":
                yield data.get("text", "")
        await ws.send(json.dumps({"terminate_session": True}))
        _ = await ws.recv()

# Ninja lifespan에서 백그라운드 태스크로 stream_audio를 구독하면 SSE/WebSocket으로 클라이언트에 중계 가능
```

## Celery 작업과 Webhook 핸들러
STT 생성과 후처리를 워커로 분리하면 API 레이턴시가 줄고 재시도 정책을 쉽게 적용할 수 있습니다. AssemblyAI Webhook 예시입니다.

```python
# app/tasks.py
from celery import shared_task
import httpx
import os

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def notify_webhook(self, webhook_url, payload):
    try:
        httpx.post(webhook_url, json=payload, timeout=10)
    except Exception as exc:  # brief retry on transient errors
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=2, default_retry_delay=3)
def store_transcript(self, transcript_id):
    headers = {"authorization": os.environ["ASSEMBLYAI_API_KEY"]}
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # TODO: persist data["text"] to DB/storage
    return data
```

```python
# app/api.py (Webhook 수신)
from ninja import Router
from .tasks import notify_webhook, store_transcript

router = Router()

@router.post("/stt/webhook")
def assembly_webhook(request):
    payload = request.json()
    if payload.get("status") == "completed":
        store_transcript.delay(payload["id"])
    elif payload.get("status") in {"error", "failed"}:
        notify_webhook.delay(payload.get("webhook_url"), {"id": payload.get("id"), "status": payload.get("status")})
    return {"ok": True}
```

## 로컬 Whisper GPU 파이프라인
온프레미스·데이터 유출 우려 환경에서는 Whisper GPU 추론이 유용합니다. ffmpeg로 리샘플 후 로컬에서 바로 인퍼런스합니다.

```python
# app/whisper_local.py
import subprocess
import torch
import whisper
from pathlib import Path

model = whisper.load_model("medium", device="cuda" if torch.cuda.is_available() else "cpu")

def transcribe_local(input_path: str) -> str:
    wav_path = Path(input_path).with_suffix(".16k.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "16000", wav_path
    ], check=True)
    result = model.transcribe(str(wav_path), language="ko")
    return result.get("text", "")
```

Whisper 경로는 GPU 메모리를 많이 사용하므로 short-form 오디오나 사내 전용 서비스에 적합합니다. 장기적으로는 Whisper 결과를 캐싱해 동일 파일 재처리 비용을 줄이고, 품질이 중요한 경우 `large-v3`로만 제한하여 모델 일관성을 유지합니다.

## SSE/WebSocket 중계 샘플 (Ninja + uvicorn)
스트리밍 STT를 클라이언트로 중계할 때 SSE는 단방향(브라우저 호환성), WebSocket은 양방향(모바일 앱) 용도로 구분합니다.

```python
# app/stream.py
from ninja import Router
from starlette.responses import EventSourceResponse
from .ws import stream_audio

router = Router()

@router.get("/stt/stream/sse")
async def stt_sse(request):
    async def event_generator():
        async for partial in stream_audio(request.state.audio_chunks):
            yield f"data: {partial}\n\n"
    return EventSourceResponse(event_generator())

@router.websocket("/stt/stream/ws")
async def stt_ws(request, ws):
    await ws.accept()
    async for partial in stream_audio(request.state.audio_chunks):
        await ws.send_text(partial)
    await ws.close()
```

`request.state.audio_chunks`는 미리 수집된 PCM 바이트 제너레이터로 주입하면 됩니다. SSE 응답은 자동으로 `text/event-stream` 헤더를 설정합니다.

## Dockerfile (GPU Whisper)
로컬 Whisper 추론용 CUDA 베이스 이미지를 사용하고, ffmpeg·Python 의존성을 포함합니다.

```dockerfile
FROM nvidia/cuda:12.3.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y ffmpeg git python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.api:api", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

`requirements.txt`에는 `whisper`, `torch==2.1.0+cu121`(pip wheel), `ninja`(PyTorch 빌드 의존성), `django-ninja`, `uvicorn[standard]`, `httpx`, `boto3` 등을 명시합니다. 컨테이너 실행 시 `--gpus all` 옵션을 붙여 GPU를 노출합니다.

## DB 스키마와 캐싱 키 전략
STT/TTS 결과를 재사용하려면 입력 파라미터로 캐시 키를 만들고, 결과 메타데이터를 저장합니다.

```sql
CREATE TABLE stt_results (
    id UUID PRIMARY KEY,
    source_url TEXT NOT NULL,
    transcript TEXT,
    status VARCHAR(32) NOT NULL,
    engine VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE tts_results (
    id UUID PRIMARY KEY,
    text_hash CHAR(64) NOT NULL,
    voice_id VARCHAR(32) NOT NULL,
    audio_url TEXT NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_tts_cache ON tts_results(text_hash, voice_id);
```

```python
# cache key helper
import hashlib

def tts_cache_key(text: str, voice_id: str) -> str:
    raw = f"{voice_id}:{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
```

DB에는 해시와 voice_id를 기준으로 조회해 캐시된 URL을 반환하고, 만료 시 S3 객체 삭제와 함께 레코드를 정리합니다. STT는 동일 `source_url`에 대해 중복 요청이 오면 기존 결과를 반환하도록 `status`가 `completed`인 경우 단건을 우선 제공합니다.
