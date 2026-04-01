---
layout: post
title: "Django-Ninja + AWS + LLM으로 미디어 자동 검색 색인 시스템 구축하기"
date: 2026-04-01
categories: backend
tags: [django-ninja, aws, s3, llm, search, opensearch, python, fastapi-style]
author: updaun
image: "/assets/img/posts/2026-04-01-django-ninja-aws-llm-media-search-index.webp"
render_with_liquid: false
---

# Django-Ninja + AWS + LLM으로 미디어 자동 검색 색인 시스템 구축하기

이미지와 영상을 업로드하면 LLM이 자동으로 내용을 분석해 한국어·영어 검색 색인을 생성하고, 사용자가 어떤 언어로 검색하든 원하는 자료를 바로 찾을 수 있는 시스템을 만들어보겠습니다. 핵심 스택은 **Django-Ninja**(고성능 REST API), **AWS S3 + CloudFront**(미디어 저장·배포), **OpenAI GPT-4o / Claude**(자동 색인 생성), 그리고 **PostgreSQL full-text search**(검색 엔진)입니다.

이 포스트를 끝까지 읽고 나면 "파일 업로드 → 클라우드 저장 → LLM 분석 → 한·영 색인 저장 → 검색 API 제공"까지 동작하는 완성된 흐름을 갖게 됩니다.

---

## 시스템 아키텍처 전체 흐름

구현을 시작하기 전에 데이터가 어떤 경로로 흐르는지 전체 그림을 먼저 잡겠습니다.

```
클라이언트 (브라우저 / 앱)
        │
        ▼
[Django-Ninja API 서버]
  ① Presigned URL 발급 or 직접 업로드 수신
        │
        ▼
[AWS S3]  ─────────────────  [AWS CloudFront]
  미디어 원본 저장               CDN 배포
        │
        ▼
[Celery Task Queue]
  비동기 LLM 분석 작업 큐
        │
        ▼
[LLM (GPT-4o / Claude)]
  이미지·영상 → 설명 텍스트 생성
  한국어 태그 / 영어 태그 추출
        │
        ▼
[PostgreSQL]
  media_items 테이블
  search_index 테이블 (tsvector 컬럼)
        │
        ▼
[Django-Ninja Search API]
  한·영 통합 검색 응답 반환
```

핵심 포인트는 파일 저장과 LLM 분석을 **비동기로 분리**한다는 점입니다. 업로드 응답은 즉시 반환하고, LLM 호출은 Celery 워커가 백그라운드에서 처리합니다. 이렇게 하면 사용자가 업로드 중에 LLM 응답 지연을 기다리지 않아도 됩니다.

---

## 프로젝트 초기 설정

### 의존성 설치

```bash
pip install django-ninja boto3 celery redis openai anthropic \
            Pillow python-magic django-storages \
            psycopg2-binary python-dotenv
```

| 패키지 | 역할 |
|---|---|
| `django-ninja` | FastAPI 스타일의 고성능 Django REST API |
| `boto3` | AWS S3 연동 SDK |
| `celery` | 비동기 태스크 큐 |
| `openai` / `anthropic` | GPT-4o, Claude LLM API |
| `Pillow` | 이미지 메타데이터 처리 |
| `python-magic` | 파일 MIME 타입 검증 |
| `django-storages` | Django ↔ S3 스토리지 백엔드 |

### Django 설정 (`settings.py`)

```python
# settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

INSTALLED_APPS = [
    ...
    "storages",
    "media_index",   # 이번에 만들 앱
]

# ── AWS S3 ──────────────────────────────────────────────
AWS_ACCESS_KEY_ID       = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY   = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME      = os.getenv("AWS_S3_REGION_NAME", "ap-northeast-2")
AWS_S3_CUSTOM_DOMAIN    = os.getenv("AWS_CLOUDFRONT_DOMAIN")  # CloudFront 도메인
AWS_S3_FILE_OVERWRITE   = False
AWS_DEFAULT_ACL         = "private"          # 퍼블릭 직접 접근 차단
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

# 미디어 파일을 S3로 라우팅
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# ── Celery (Redis 브로커) ──────────────────────────────
CELERY_BROKER_URL        = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND    = CELERY_BROKER_URL
CELERY_TASK_SERIALIZER   = "json"
CELERY_ACCEPT_CONTENT    = ["json"]

# ── LLM ───────────────────────────────────────────────
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "openai")   # "openai" | "anthropic"
```

보안 원칙상 AWS 키는 절대 소스 코드에 하드코딩하지 않고 `.env` 파일 또는 AWS Secrets Manager에서 읽어옵니다. 프로덕션에서는 EC2·ECS IAM 역할로 `AWS_ACCESS_KEY_ID` 없이 인증하는 것을 권장합니다.

---

## 데이터베이스 모델 설계

```python
# media_index/models.py
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class MediaItem(models.Model):
    """업로드된 이미지·영상 원본"""

    class MediaType(models.TextChoices):
        IMAGE = "image", "이미지"
        VIDEO = "video", "영상"

    class IndexStatus(models.TextChoices):
        PENDING   = "pending",   "색인 대기"
        INDEXING  = "indexing",  "색인 중"
        COMPLETED = "completed", "색인 완료"
        FAILED    = "failed",    "색인 실패"

    # 파일 정보
    file         = models.FileField(upload_to="media/%Y/%m/")
    original_name = models.CharField(max_length=255)
    media_type   = models.CharField(max_length=10, choices=MediaType.choices)
    file_size    = models.PositiveBigIntegerField()          # bytes
    mime_type    = models.CharField(max_length=100)
    duration_sec = models.FloatField(null=True, blank=True)  # 영상 전용

    # 메타데이터
    width        = models.PositiveIntegerField(null=True, blank=True)
    height       = models.PositiveIntegerField(null=True, blank=True)
    uploaded_by  = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="media_items"
    )
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    # LLM 색인 상태
    index_status = models.CharField(
        max_length=20, choices=IndexStatus.choices, default=IndexStatus.PENDING
    )
    index_error  = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["index_status", "media_type"])]

    def __str__(self):
        return f"{self.media_type}:{self.original_name}"


class MediaSearchIndex(models.Model):
    """LLM이 생성한 한·영 검색 색인"""

    media        = models.OneToOneField(
        MediaItem, on_delete=models.CASCADE, related_name="search_index"
    )

    # LLM 생성 설명 (원문 보존)
    description_ko = models.TextField(blank=True)   # 한국어 설명
    description_en = models.TextField(blank=True)   # 영어 설명

    # 태그 (콤마 구분 저장, 검색용)
    tags_ko        = models.TextField(blank=True)   # 예: "夕陽,하늘,노을"
    tags_en        = models.TextField(blank=True)   # 예: "sunset,sky,orange"

    # PostgreSQL Full-Text Search 벡터 컬럼
    search_vector_ko = SearchVectorField(null=True)
    search_vector_en = SearchVectorField(null=True)
    search_vector_combined = SearchVectorField(null=True)  # 한+영 통합

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector_ko"],       name="idx_sv_ko"),
            GinIndex(fields=["search_vector_en"],       name="idx_sv_en"),
            GinIndex(fields=["search_vector_combined"], name="idx_sv_combined"),
        ]
```

`SearchVectorField`와 `GinIndex`를 사용하면 PostgreSQL 내장 전문 검색(Full-Text Search) 기능을 그대로 활용할 수 있습니다. 별도의 Elasticsearch 클러스터를 띄우지 않아도 수백만 건 규모까지 충분히 커버됩니다.

---

## AWS S3 업로드 유틸리티

```python
# media_index/s3_utils.py
import magic
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_MIME = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
MAX_IMAGE_SIZE = 50 * 1024 * 1024   # 50 MB
MAX_VIDEO_SIZE = 2  * 1024 * 1024 * 1024  # 2 GB


def validate_file(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    파일 바이트를 검증하고 (mime_type, media_type) 튜플 반환.
    허용되지 않는 파일 형식은 ValueError 발생.
    """
    mime = magic.from_buffer(file_bytes[:2048], mime=True)

    if mime in ALLOWED_IMAGE_MIME:
        return mime, "image"
    if mime in ALLOWED_VIDEO_MIME:
        return mime, "video"

    raise ValueError(f"허용되지 않는 파일 형식입니다: {mime}")


def generate_presigned_upload_url(s3_key: str, mime_type: str, expires: int = 3600) -> str:
    """
    클라이언트가 S3에 직접 업로드할 수 있는 Presigned URL 생성.
    서버 메모리를 거치지 않으므로 대용량 영상에 적합.
    """
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
    )
    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket":      settings.AWS_STORAGE_BUCKET_NAME,
            "Key":         s3_key,
            "ContentType": mime_type,
        },
        ExpiresIn=expires,
    )
    return url


def generate_presigned_download_url(s3_key: str, expires: int = 3600) -> str:
    """비공개 파일의 임시 다운로드 URL 생성"""
    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires,
    )


def delete_s3_object(s3_key: str) -> None:
    """미디어 삭제 시 S3 원본도 함께 제거"""
    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
    try:
        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
    except ClientError as e:
        # 이미 없는 키는 무시, 나머지 에러는 상위로 전파
        if e.response["Error"]["Code"] != "NoSuchKey":
            raise
```

Presigned URL 방식을 사용하면 대용량 영상 파일이 Django 서버 메모리를 전혀 거치지 않고 클라이언트 → S3 직접 전송이 가능합니다. 업로드 완료 후 클라이언트가 서버에 "업로드 완료" 콜백을 보내면 DB 저장 및 LLM 색인 태스크가 시작됩니다.

---

## LLM 색인 생성 엔진

LLM에게 이미지·영상 스크린샷을 보내고, 한국어·영어 설명과 태그를 JSON 형식으로 받아옵니다. 프롬프트 설계가 핵심입니다.

```python
# media_index/llm_indexer.py
import base64
import json
import re
from pathlib import Path
from django.conf import settings

# ── 공통 시스템 프롬프트 ───────────────────────────────────────────────────
SYSTEM_PROMPT = """
당신은 미디어 자산 관리 시스템의 검색 색인 생성 전문가입니다.
이미지 또는 영상 프레임을 분석하여 검색에 최적화된 메타데이터를 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
  "description_ko": "이미지/영상의 상세 한국어 설명 (3-5문장)",
  "description_en": "Detailed English description of the image/video (3-5 sentences)",
  "tags_ko": ["태그1", "태그2", "태그3", "..."],
  "tags_en": ["tag1", "tag2", "tag3", "..."],
  "dominant_colors": ["색상1", "색상2"],
  "scene_type": "indoor | outdoor | abstract | document | other",
  "content_rating": "safe | sensitive"
}

tags_ko: 한국어 태그 10~20개. 피사체, 장소, 분위기, 색상, 활동 등을 포함.
tags_en: 영어 태그 10~20개. 동의어와 관련 개념을 풍부하게 포함.
"""


def _encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _parse_llm_response(raw: str) -> dict:
    """LLM 응답에서 JSON 블록만 추출"""
    # 마크다운 코드 블록 제거
    cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback: 첫 번째 { } 블록 추출
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM 응답 파싱 실패: {raw[:200]}")


def index_with_openai(image_path: str, mime_type: str) -> dict:
    """GPT-4o Vision으로 이미지 분석"""
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    b64 = _encode_image_to_base64(image_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": "이 이미지의 검색 색인을 생성해주세요."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ],
            },
        ],
        max_tokens=1024,
        temperature=0.2,   # 재현성 높게 유지
    )
    raw = response.choices[0].message.content
    return _parse_llm_response(raw)


def index_with_anthropic(image_path: str, mime_type: str) -> dict:
    """Claude로 이미지 분석"""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    b64 = _encode_image_to_base64(image_path)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime_type, "data": b64},
                    },
                    {"type": "text", "text": "이 이미지의 검색 색인을 생성해주세요."},
                ],
            }
        ],
    )
    raw = response.content[0].text
    return _parse_llm_response(raw)


def generate_search_index(image_path: str, mime_type: str) -> dict:
    """
    설정된 LLM_PROVIDER에 따라 적절한 분석 함수 호출.
    응답 예시:
    {
      "description_ko": "푸른 하늘 아래 펼쳐진 광활한 초원...",
      "description_en": "A vast meadow under a clear blue sky...",
      "tags_ko": ["초원", "하늘", "자연", "풍경", ...],
      "tags_en": ["meadow", "sky", "nature", "landscape", ...],
      "dominant_colors": ["푸른색", "초록색"],
      "scene_type": "outdoor",
      "content_rating": "safe"
    }
    """
    provider = settings.LLM_PROVIDER

    if provider == "openai":
        return index_with_openai(image_path, mime_type)
    elif provider == "anthropic":
        return index_with_anthropic(image_path, mime_type)
    else:
        raise ValueError(f"지원하지 않는 LLM_PROVIDER: {provider}")
```

시스템 프롬프트에서 **JSON 형식만 반환하도록** 엄격하게 지정하고, 파싱 단계에서도 마크다운 코드 블록을 제거하는 방어 로직을 추가했습니다. `temperature=0.2`로 낮게 설정해 색인의 일관성을 높입니다.

---

## 영상 프레임 추출 (영상 색인 지원)

영상은 직접 LLM에 전달할 수 없으므로 대표 프레임을 추출해서 이미지로 분석합니다.

```python
# media_index/video_utils.py
import os
import subprocess
import tempfile
from pathlib import Path


def extract_video_frames(video_path: str, num_frames: int = 4) -> list[str]:
    """
    FFmpeg로 영상에서 균등 간격 프레임을 추출하여 임시 파일 경로 리스트 반환.
    호출자가 사용 후 파일을 직접 삭제해야 합니다.
    """
    # 영상 길이 파악
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())

    frames = []
    temp_dir = tempfile.mkdtemp(prefix="vframe_")

    for i in range(num_frames):
        timestamp = duration * (i + 1) / (num_frames + 1)
        out_path  = os.path.join(temp_dir, f"frame_{i:02d}.jpg")
        cmd = [
            "ffmpeg", "-ss", str(timestamp),
            "-i",  video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_path, "-y",
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        frames.append(out_path)

    return frames


def cleanup_frames(frame_paths: list[str]) -> None:
    """임시 프레임 파일 및 디렉터리 정리"""
    for path in frame_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    if frame_paths:
        parent = Path(frame_paths[0]).parent
        try:
            parent.rmdir()
        except OSError:
            pass
```

4개의 균등 간격 프레임을 추출해 각각 LLM에 분석 요청을 보낸 뒤, 결과 태그를 합산해 최종 색인으로 병합합니다. 이렇게 하면 영상 전체 내용을 보다 풍부하게 커버할 수 있습니다.

---

## Celery 비동기 색인 태스크

```python
# media_index/tasks.py
import logging
import tempfile
import os
from celery import shared_task
from django.contrib.postgres.search import SearchVector
from django.db import transaction

from .models import MediaItem, MediaSearchIndex
from .llm_indexer import generate_search_index
from .video_utils import extract_video_frames, cleanup_frames

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # 1분 후 재시도
    autoretry_for=(Exception,),
    retry_backoff=True,        # 지수 백오프: 60s → 120s → 240s
)
def generate_media_search_index(self, media_item_id: int) -> dict:
    """
    미디어 아이템의 LLM 색인을 비동기로 생성.
    실패 시 최대 3회 재시도.
    """
    try:
        item = MediaItem.objects.get(pk=media_item_id)
    except MediaItem.DoesNotExist:
        logger.error(f"MediaItem {media_item_id} not found")
        return {"status": "not_found"}

    item.index_status = MediaItem.IndexStatus.INDEXING
    item.save(update_fields=["index_status"])

    try:
        if item.media_type == "image":
            index_data = _index_image(item)
        else:
            index_data = _index_video(item)

        _save_index(item, index_data)
        return {"status": "completed", "media_id": media_item_id}

    except Exception as exc:
        logger.exception(f"색인 실패 media_id={media_item_id}: {exc}")
        item.index_status = MediaItem.IndexStatus.FAILED
        item.index_error  = str(exc)
        item.save(update_fields=["index_status", "index_error"])
        raise


def _index_image(item: MediaItem) -> dict:
    """이미지 파일을 임시 다운로드 후 LLM 분석"""
    import boto3
    from django.conf import settings

    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
    s3_key = item.file.name

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, s3_key, tmp.name)
        tmp_path = tmp.name

    try:
        return generate_search_index(tmp_path, item.mime_type)
    finally:
        os.unlink(tmp_path)


def _index_video(item: MediaItem) -> dict:
    """영상에서 복수 프레임 추출 후 각 프레임을 LLM 분석하여 결과 병합"""
    import boto3
    from django.conf import settings

    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
    s3_key = item.file.name

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, s3_key, tmp.name)
        video_path = tmp.name

    frames = []
    try:
        frames = extract_video_frames(video_path, num_frames=4)
        results = [generate_search_index(f, "image/jpeg") for f in frames]
        return _merge_video_results(results)
    finally:
        cleanup_frames(frames)
        os.unlink(video_path)


def _merge_video_results(results: list[dict]) -> dict:
    """여러 프레임 분석 결과를 하나의 통합 색인으로 병합"""
    if not results:
        return {}

    # 설명: 첫 번째 프레임 기준 (가장 대표적)
    merged = {
        "description_ko": results[0].get("description_ko", ""),
        "description_en": results[0].get("description_en", ""),
        "scene_type":     results[0].get("scene_type", "other"),
        "content_rating": results[0].get("content_rating", "safe"),
    }

    # 태그: 전체 결과에서 중복 제거 후 통합
    all_tags_ko = []
    all_tags_en = []
    for r in results:
        all_tags_ko.extend(r.get("tags_ko", []))
        all_tags_en.extend(r.get("tags_en", []))

    # 빈도 높은 태그를 앞에 정렬
    from collections import Counter
    merged["tags_ko"] = [t for t, _ in Counter(all_tags_ko).most_common(30)]
    merged["tags_en"] = [t for t, _ in Counter(all_tags_en).most_common(30)]

    return merged


@transaction.atomic
def _save_index(item: MediaItem, data: dict) -> None:
    """색인 데이터를 DB에 저장하고 tsvector 업데이트"""
    tags_ko_str = " ".join(data.get("tags_ko", []))
    tags_en_str = " ".join(data.get("tags_en", []))
    desc_ko     = data.get("description_ko", "")
    desc_en     = data.get("description_en", "")

    index, _ = MediaSearchIndex.objects.update_or_create(
        media=item,
        defaults={
            "description_ko": desc_ko,
            "description_en": desc_en,
            "tags_ko":        ",".join(data.get("tags_ko", [])),
            "tags_en":        ",".join(data.get("tags_en", [])),
        },
    )

    # PostgreSQL tsvector 업데이트 (언어별 stemmer 적용)
    MediaSearchIndex.objects.filter(pk=index.pk).update(
        search_vector_ko=SearchVector("description_ko", "tags_ko", config="simple"),
        search_vector_en=SearchVector("description_en", "tags_en", config="english"),
        search_vector_combined=SearchVector("description_ko", "tags_ko", config="simple")
                               + SearchVector("description_en", "tags_en", config="english"),
    )

    item.index_status = MediaItem.IndexStatus.COMPLETED
    item.save(update_fields=["index_status", "index_error"])
```

`config="english"` 설정으로 영어는 Porter 어간 추출(stemming)이 적용됩니다. "running"으로 검색하면 "run", "runs", "ran"도 같이 히트됩니다. 한국어는 현재 PostgreSQL에 내장된 한국어 사전이 없으므로 `config="simple"`로 공백 분리 토크나이징을 사용합니다. 실 서비스에서는 mecab 기반 `pg_bigm` 확장을 추가하면 한국어 형태소 검색 성능이 크게 향상됩니다.

---

## Django-Ninja API 설계

```python
# media_index/api.py
import mimetypes
import uuid
from typing import Optional

from django.contrib.auth.models import User
from ninja import NinjaAPI, File, Schema
from ninja.files import UploadedFile
from ninja.security import django_auth

from .models import MediaItem, MediaSearchIndex
from .s3_utils import validate_file, generate_presigned_upload_url, generate_presigned_download_url
from .tasks import generate_media_search_index

api = NinjaAPI(title="Media Search Index API", version="1.0")


# ── 스키마 定義 ─────────────────────────────────────────────────────────────

class PresignedUploadRequest(Schema):
    filename: str
    file_size: int
    mime_type: str


class PresignedUploadResponse(Schema):
    upload_url:   str
    s3_key:       str
    expires_in:   int = 3600


class UploadCompleteRequest(Schema):
    s3_key:        str
    original_name: str
    file_size:     int
    mime_type:     str
    width:         Optional[int] = None
    height:        Optional[int] = None
    duration_sec:  Optional[float] = None


class MediaItemOut(Schema):
    id:           int
    original_name: str
    media_type:   str
    file_size:    int
    index_status: str
    download_url: Optional[str] = None
    uploaded_at:  str


class SearchResultItem(Schema):
    id:             int
    original_name:  str
    media_type:     str
    description_ko: str
    description_en: str
    tags_ko:        list[str]
    tags_en:        list[str]
    download_url:   str
    score:          float


# ── 업로드 API ──────────────────────────────────────────────────────────────

@api.post("/upload/presigned", auth=django_auth, response=PresignedUploadResponse)
def request_presigned_upload(request, payload: PresignedUploadRequest):
    """
    1단계: Presigned Upload URL 발급.
    클라이언트는 반환된 upload_url로 S3에 직접 PUT 업로드.
    """
    allowed_types = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4",  "video/webm", "video/quicktime",
    }
    if payload.mime_type not in allowed_types:
        return api.create_response(request, {"detail": "허용되지 않는 파일 형식"}, status=400)

    ext     = mimetypes.guess_extension(payload.mime_type) or ""
    s3_key  = f"uploads/{request.user.id}/{uuid.uuid4().hex}{ext}"
    url     = generate_presigned_upload_url(s3_key, payload.mime_type)

    return PresignedUploadResponse(upload_url=url, s3_key=s3_key)


@api.post("/upload/complete", auth=django_auth, response=MediaItemOut)
def complete_upload(request, payload: UploadCompleteRequest):
    """
    2단계: S3 직접 업로드 완료 후 호출.
    DB에 메타데이터를 저장하고 LLM 색인 태스크를 큐에 등록.
    """
    media_type = "video" if payload.mime_type.startswith("video/") else "image"

    item = MediaItem.objects.create(
        file=payload.s3_key,
        original_name=payload.original_name,
        media_type=media_type,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        width=payload.width,
        height=payload.height,
        duration_sec=payload.duration_sec,
        uploaded_by=request.user,
    )

    # 비동기 LLM 색인 태스크 등록
    generate_media_search_index.delay(item.pk)

    return MediaItemOut(
        id=item.pk,
        original_name=item.original_name,
        media_type=item.media_type,
        file_size=item.file_size,
        index_status=item.index_status,
        uploaded_at=item.uploaded_at.isoformat(),
    )


@api.post("/upload/direct", auth=django_auth, response=MediaItemOut)
def upload_direct(request, file: UploadedFile = File(...)):
    """
    소용량 이미지를 서버 경유로 직접 업로드 (50MB 이하만 허용).
    내부적으로 django-storages가 S3에 저장.
    """
    content = file.read()
    if len(content) > 50 * 1024 * 1024:
        return api.create_response(request, {"detail": "50MB 이하 파일만 허용됩니다"}, status=400)

    mime_type, media_type = validate_file(content, file.name)

    from django.core.files.base import ContentFile
    item = MediaItem(
        original_name=file.name,
        media_type=media_type,
        file_size=len(content),
        mime_type=mime_type,
        uploaded_by=request.user,
    )
    item.file.save(file.name, ContentFile(content), save=True)

    generate_media_search_index.delay(item.pk)

    return MediaItemOut(
        id=item.pk,
        original_name=item.original_name,
        media_type=item.media_type,
        file_size=item.file_size,
        index_status=item.index_status,
        uploaded_at=item.uploaded_at.isoformat(),
    )


# ── 검색 API ────────────────────────────────────────────────────────────────

@api.get("/search", response=list[SearchResultItem])
def search_media(
    request,
    q:          str,
    media_type: Optional[str] = None,   # "image" | "video" | None(전체)
    lang:       str = "auto",           # "ko" | "en" | "auto"
    limit:      int = 20,
    offset:     int = 0,
):
    """
    한·영 통합 전문 검색 API.
    - lang=auto: 쿼리 언어 자동 감지 후 해당 언어 벡터 우선 검색
    - lang=ko / lang=en: 강제 지정
    - 두 언어 모두 동시 검색하여 combined 벡터로 최종 랭킹
    """
    from django.contrib.postgres.search import SearchQuery, SearchRank

    if limit > 100:
        limit = 100

    # 언어 자동 감지 (한글 유니코드 범위 판별)
    if lang == "auto":
        has_korean = any("\uAC00" <= c <= "\uD7A3" for c in q)
        lang = "ko" if has_korean else "en"

    if lang == "ko":
        query  = SearchQuery(q, config="simple")
        vector = "search_vector_ko"
    else:
        query  = SearchQuery(q, config="english")
        vector = "search_vector_en"

    qs = (
        MediaSearchIndex.objects
        .filter(**{f"{vector}__icontains": ""})   # 색인 완료 항목만
        .annotate(score=SearchRank(vector, query))
        .filter(score__gt=0.0)
        .select_related("media")
        .order_by("-score")
    )

    if media_type in ("image", "video"):
        qs = qs.filter(media__media_type=media_type)

    results = []
    for idx in qs[offset : offset + limit]:
        item = idx.media
        results.append(
            SearchResultItem(
                id=item.pk,
                original_name=item.original_name,
                media_type=item.media_type,
                description_ko=idx.description_ko,
                description_en=idx.description_en,
                tags_ko=idx.tags_ko.split(",") if idx.tags_ko else [],
                tags_en=idx.tags_en.split(",") if idx.tags_en else [],
                download_url=generate_presigned_download_url(item.file.name),
                score=round(idx.score, 4),
            )
        )

    return results


@api.get("/media/{media_id}/status", auth=django_auth, response=dict)
def get_index_status(request, media_id: int):
    """색인 진행 상태 조회 (클라이언트 폴링용)"""
    try:
        item = MediaItem.objects.get(pk=media_id, uploaded_by=request.user)
    except MediaItem.DoesNotExist:
        return api.create_response(request, {"detail": "Not found"}, status=404)

    resp = {"id": item.pk, "status": item.index_status}
    if item.index_status == MediaItem.IndexStatus.COMPLETED:
        try:
            idx = item.search_index
            resp["tags_ko"] = idx.tags_ko.split(",")[:10]
            resp["tags_en"] = idx.tags_en.split(",")[:10]
        except MediaSearchIndex.DoesNotExist:
            pass
    elif item.index_status == MediaItem.IndexStatus.FAILED:
        resp["error"] = item.index_error

    return resp
```

Django-Ninja는 Pydantic 스키마로 요청·응답을 자동 직렬화하고, `/api/docs`에서 Swagger UI를 자동으로 제공합니다. 별도 문서화 작업 없이 API 명세가 항상 최신 상태로 유지됩니다.

---

## URL 등록 및 Celery 앱 설정

```python
# config/urls.py
from django.urls import path
from media_index.api import api

urlpatterns = [
    path("api/", api.urls),
]
```

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ("celery_app",)
```

워커 실행:

```bash
# 개발 환경
celery -A config worker -l info -c 4   # 동시 4 워커

# 프로덕션 (supervisord 관리 권장)
celery -A config worker -l warning -c 8 --max-tasks-per-child=100
```

---

## 한·영 검색 성능 최적화 전략

단순 키워드 매칭만으로는 검색 품질에 한계가 있습니다. 다음 네 가지 전략을 추가하면 검색 재현율(recall)과 정밀도(precision)를 크게 높일 수 있습니다.

### 1. 태그 동의어 확장 (Synonym Expansion)

```python
# media_index/synonym_expander.py
SYNONYM_MAP_KO = {
    "강아지": ["개", "반려견", "댕댕이"],
    "고양이": ["냥이", "반려묘"],
    "자동차": ["차", "승용차", "차량"],
    "건물":   ["빌딩", "건축물", "구조물"],
}

SYNONYM_MAP_EN = {
    "car":  ["automobile", "vehicle", "auto"],
    "dog":  ["puppy", "canine", "hound"],
    "cat":  ["feline", "kitten"],
    "building": ["structure", "edifice", "architecture"],
}

def expand_query(query: str, lang: str) -> str:
    """검색어에 동의어를 OR 연산으로 추가"""
    synonym_map = SYNONYM_MAP_KO if lang == "ko" else SYNONYM_MAP_EN
    terms = query.split()
    expanded = []
    for term in terms:
        synonyms = synonym_map.get(term, [])
        expanded.append(term)
        expanded.extend(synonyms)
    return " | ".join(expanded)   # PostgreSQL tsquery OR 연산자
```

### 2. LLM 기반 쿼리 재작성 (Query Rewriting)

```python
def rewrite_query_with_llm(query: str) -> dict:
    """
    짧은 검색어를 LLM으로 확장하여 양 언어 검색어를 동시에 생성.
    예: "바다 일몰" → {"ko": "바다 일몰 노을 해변 파도", "en": "sea sunset ocean beach waves dusk"}
    """
    from openai import OpenAI
    from django.conf import settings

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = f"""
다음 검색어를 분석하여 관련 키워드를 확장해주세요.
검색어: "{query}"

반드시 JSON 형식으로 응답하세요:
{{
  "ko": "원래 검색어와 관련된 한국어 키워드들 (공백 구분, 10개 이내)",
  "en": "related English keywords (space separated, max 10 words)"
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # 빠른 응답을 위해 mini 모델 사용
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.1,
    )
    import json, re
    raw = response.choices[0].message.content
    cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip()
    return json.loads(cleaned)
```

### 3. 통합 검색 함수 (실제 서비스 적용 버전)

```python
# media_index/search_service.py
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .models import MediaSearchIndex
from .synonym_expander import expand_query

def search_media_items(
    query: str,
    media_type: str = None,
    limit: int = 20,
    offset: int = 0,
    use_llm_expansion: bool = False,
) -> list[MediaSearchIndex]:
    """
    한·영 통합 검색 서비스 레이어.
    동의어 확장 + 가중치 랭킹 + 크로스 언어 폴백을 지원.
    """
    # 언어 감지
    has_korean = any("\uAC00" <= c <= "\uD7A3" for c in query)
    primary_lang  = "ko" if has_korean else "en"
    fallback_lang = "en" if has_korean else "ko"

    # LLM 쿼리 확장 (선택적, 캐싱 권장)
    if use_llm_expansion:
        from .synonym_expander import rewrite_query_with_llm
        expanded = rewrite_query_with_llm(query)
        query_ko = expanded.get("ko", query)
        query_en = expanded.get("en", query)
    else:
        query_ko = expand_query(query, "ko")
        query_en = expand_query(query, "en")

    sq_ko = SearchQuery(query_ko, config="simple",  search_type="raw")
    sq_en = SearchQuery(query_en, config="english", search_type="plain")

    # 기본 언어 랭크에 가중치 1.2배 부여
    if primary_lang == "ko":
        rank_expr = SearchRank("search_vector_ko", sq_ko) * 1.2 \
                  + SearchRank("search_vector_en", sq_en)
    else:
        rank_expr = SearchRank("search_vector_en", sq_en) * 1.2 \
                  + SearchRank("search_vector_ko", sq_ko)

    qs = (
        MediaSearchIndex.objects
        .annotate(score=rank_expr)
        .filter(score__gt=0.01)
        .select_related("media")
        .order_by("-score")
    )

    if media_type in ("image", "video"):
        qs = qs.filter(media__media_type=media_type)

    return list(qs[offset : offset + limit])
```

### 4. 색인 품질 지표 모니터링

```python
# management/commands/check_index_quality.py
from django.core.management.base import BaseCommand
from media_index.models import MediaItem

class Command(BaseCommand):
    help = "색인 상태 현황 출력"

    def handle(self, *args, **opts):
        from django.db.models import Count
        stats = (
            MediaItem.objects
            .values("index_status", "media_type")
            .annotate(count=Count("id"))
            .order_by("index_status", "media_type")
        )
        self.stdout.write("\n=== 미디어 색인 현황 ===")
        for s in stats:
            self.stdout.write(
                f"  [{s['media_type']:5}] {s['index_status']:10} : {s['count']:>6,}건"
            )
```

---

## 전체 API 흐름 요약 및 테스트

```
# 1. Presigned URL 요청
POST /api/upload/presigned
Authorization: Session ...
{
  "filename": "sunset.jpg",
  "file_size": 2048000,
  "mime_type": "image/jpeg"
}
→ { "upload_url": "https://s3.ap-northeast-2.amazonaws.com/...", "s3_key": "uploads/42/abc123.jpg" }

# 2. S3에 직접 업로드 (클라이언트 → S3)
PUT {upload_url}
Content-Type: image/jpeg
[바이너리 파일 데이터]

# 3. 업로드 완료 알림
POST /api/upload/complete
{ "s3_key": "uploads/42/abc123.jpg", "original_name": "sunset.jpg",
  "file_size": 2048000, "mime_type": "image/jpeg", "width": 1920, "height": 1080 }
→ { "id": 99, "index_status": "pending", ... }

# 4. 색인 완료 대기 (폴링)
GET /api/media/99/status
→ { "id": 99, "status": "completed", "tags_ko": ["노을","하늘","바다",...], "tags_en": ["sunset","sky","ocean",...] }

# 5. 검색 (한국어)
GET /api/search?q=바다+노을&media_type=image
→ [{ "id": 99, "description_ko": "...", "tags_ko": [...], "score": 0.3214, ... }]

# 6. 검색 (영어, 동일 자료 히트)
GET /api/search?q=ocean+sunset&lang=en
→ [{ "id": 99, "description_en": "...", "tags_en": [...], "score": 0.2891, ... }]
```

---

## 마치며

이 시스템의 핵심 가치는 두 가지입니다. 첫째, **업로드 시점**에 LLM이 자동으로 한국어·영어 설명과 태그를 생성하므로 사용자가 별도로 메타데이터를 입력하지 않아도 됩니다. 둘째, 두 언어의 색인을 독립적으로 유지하면서 검색 시에는 **가중치 기반으로 통합 랭킹**을 계산하므로 "한글로 업로드했는데 영어로 못 찾는" 문제가 사라집니다.

실제 서비스로 확장할 때는 다음 항목을 고려해보세요. 한국어 형태소 분석 정확도를 높이려면 `pg_bigm` 확장 또는 Elasticsearch + Nori 플러그인 도입이 효과적입니다. 색인 호출 횟수가 많아지면 LLM API 비용이 급증하므로 동일 파일 해시에 대한 캐시 레이어를 Redis에 추가하는 것을 권장합니다. 검색 트래픽이 높아지면 PostgreSQL의 `tsvector` 인덱스 대신 Elasticsearch나 OpenSearch로 마이그레이션하고, Django-Ninja의 검색 API만 교체하면 됩니다. 나머지 업로드·색인 파이프라인은 그대로 재사용 가능합니다.
