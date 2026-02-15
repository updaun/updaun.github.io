---
layout: post
title: "Django로 YouTube Data API 연동: 최신 업로드 저장, 재생목록 구성, 임베딩 재생까지"
date: 2026-02-14 10:00:00 +0900
categories: [Django, Backend, API]
tags: [Django, YouTube, YouTube-Data-API, Google-Cloud, OAuth, Playlist, Embed]
image: "/assets/img/posts/2026-02-14-django-youtube-data-api-playlist-embed.webp"
---

## 들어가며

유튜브 채널을 운영한다고 가정하고, Google YouTube Data API로 최근 업로드 영상을 가져와 Django 모델에 저장한 뒤, 여러 영상을 하나의 재생목록으로 묶고 임베딩 플레이어로 재생하는 흐름을 끝까지 구현해 보겠습니다.

이 글의 목표는 다음과 같습니다.

- YouTube Data API v3로 **최근 업로드 영상 목록**을 수집한다.
- Django 모델에 영상을 저장하고 **우리 서비스용 재생목록**을 만든다.
- 재생목록을 **임베딩 플레이어**로 재생한다.

YouTube에서 실제로 재생목록을 생성하거나 비공개 데이터를 다루려면 OAuth가 필요합니다. 이번 글에서는 **공개 업로드 영상 수집은 API 키로**, **임베딩 플레이어는 서비스 내부 재생목록**으로 구현하고, 마지막에 OAuth 확장 경로도 정리합니다.

## 1. 구글 클라우드 콘솔 설정 (API 키 + OAuth)

### 1-1. 프로젝트 생성

1. Google Cloud Console 접속: https://console.cloud.google.com
2. 좌측 상단 프로젝트 드롭다운 클릭 → "새 프로젝트"
3. 프로젝트 이름 입력 (예: `youtube-django-playlist`)
4. "만들기" 클릭

### 1-2. YouTube Data API v3 활성화

1. 콘솔 좌측 메뉴 → "API 및 서비스" → "라이브러리"
2. 검색창에 `YouTube Data API v3` 입력
3. API 선택 → "사용" 클릭

### 1-3. API 키 생성

공개 채널 데이터(업로드 목록 등)를 읽는 데는 API 키만으로 충분합니다.

1. "API 및 서비스" → "사용자 인증 정보"
2. "사용자 인증 정보 만들기" → "API 키"
3. 키 생성 후 복사

#### API 키 제한 (권장)

API 키가 노출되어도 악용되지 않도록 제한합니다.

1. 생성된 API 키 클릭 → "키 제한"
2. 애플리케이션 제한: 서버라면 "IP 주소", 웹이라면 "HTTP 리퍼러"
3. API 제한: "YouTube Data API v3"만 선택
4. 저장

### 1-4. OAuth 클라이언트 생성 (옵션이지만 권장)

**비공개 영상 접근, 채널의 실제 재생목록 생성/수정**을 하려면 OAuth가 필요합니다. 이번 글의 핵심 흐름에는 직접 사용하지 않지만, 확장 구현에 대비해 설정 방법을 정리합니다.

1. "API 및 서비스" → "OAuth 동의 화면"
2. 사용자 유형 선택: 개인 프로젝트면 "외부" 선택
3. 앱 이름, 이메일 등 필수 항목 입력 → 저장
4. 범위: 우선 기본값으로 저장해도 됨 (추가 범위는 나중에)
5. 테스트 사용자 등록 (본인 계정)
6. "사용자 인증 정보" → "사용자 인증 정보 만들기" → "OAuth 클라이언트 ID"
7. 애플리케이션 유형: "웹 애플리케이션"
8. 승인된 리디렉션 URI 추가 (예: `http://localhost:8000/oauth/callback/`)
9. 생성 후 `클라이언트 ID`와 `클라이언트 보안 비밀` 복사

## 2. Django 프로젝트 준비

### 2-1. 패키지 설치

```bash
pip install google-api-python-client python-dotenv
```

### 2-2. 환경 변수 설정

`.env`에 민감 정보를 저장합니다.

```env
YOUTUBE_API_KEY=YOUR_API_KEY
YOUTUBE_CHANNEL_ID=YOUR_CHANNEL_ID
```

채널 ID는 채널 URL에서 확인하거나, YouTube Studio → 설정 → 채널 → 고급 설정에서 확인할 수 있습니다.

### 2-3. settings.py에서 환경 변수 로드

```python
# settings.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

def get_env(name: str, default: str = "") -> str:
	return os.environ.get(name, default)

YOUTUBE_API_KEY = get_env("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = get_env("YOUTUBE_CHANNEL_ID")
```

## 3. 모델 설계

`YouTubeVideo`와 `VideoPlaylist`를 만들어 서비스 내부 재생목록을 구성합니다.

```python
# app/models.py
from django.db import models

class YouTubeVideo(models.Model):
	video_id = models.CharField(max_length=50, unique=True)
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	published_at = models.DateTimeField()
	thumbnail_url = models.URLField(blank=True)
	channel_title = models.CharField(max_length=100)

	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.title


class VideoPlaylist(models.Model):
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	videos = models.ManyToManyField(YouTubeVideo, related_name="playlists")

	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.name
```

마이그레이션:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 4. YouTube Data API 호출 코드

Google API 클라이언트를 사용해 **최근 업로드 영상 목록**을 가져옵니다. 핵심은 다음 순서입니다.

1. `channels.list`로 채널의 **업로드 전용 재생목록 ID**를 가져옴
2. `playlistItems.list`로 최신 업로드 영상 리스트를 가져옴

```python
# app/services/youtube.py
from typing import List, Dict
from googleapiclient.discovery import build
from django.conf import settings

def get_youtube_client():
	return build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

def get_uploads_playlist_id(channel_id: str) -> str:
	youtube = get_youtube_client()
	response = youtube.channels().list(
		part="contentDetails",
		id=channel_id,
	).execute()

	items = response.get("items", [])
	if not items:
		raise ValueError("Channel not found or no access")

	return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def fetch_recent_uploads(channel_id: str, max_results: int = 10) -> List[Dict]:
	youtube = get_youtube_client()
	uploads_playlist_id = get_uploads_playlist_id(channel_id)

	response = youtube.playlistItems().list(
		part="snippet",
		playlistId=uploads_playlist_id,
		maxResults=max_results,
	).execute()

	items = response.get("items", [])
	results = []

	for item in items:
		snippet = item["snippet"]
		resource_id = snippet["resourceId"]

		results.append(
			{
				"video_id": resource_id["videoId"],
				"title": snippet.get("title", ""),
				"description": snippet.get("description", ""),
				"published_at": snippet.get("publishedAt"),
				"thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
				"channel_title": snippet.get("channelTitle", ""),
			}
		)

	return results
```

## 5. Django에 저장하는 동기화 로직

관리 명령을 만들어 주기적으로 실행하거나, Django Admin 버튼으로 호출하도록 할 수 있습니다.

```python
# app/management/commands/sync_youtube_uploads.py
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import YouTubeVideo
from app.services.youtube import fetch_recent_uploads

class Command(BaseCommand):
	help = "Sync recent YouTube uploads into Django models"

	def handle(self, *args, **options):
		items = fetch_recent_uploads(settings.YOUTUBE_CHANNEL_ID, max_results=20)

		created_count = 0
		for item in items:
			obj, created = YouTubeVideo.objects.update_or_create(
				video_id=item["video_id"],
				defaults={
					"title": item["title"],
					"description": item["description"],
					"published_at": item["published_at"],
					"thumbnail_url": item["thumbnail_url"],
					"channel_title": item["channel_title"],
				},
			)
			if created:
				created_count += 1

		self.stdout.write(self.style.SUCCESS(f"Synced. New videos: {created_count}"))
```

실행:

```bash
python manage.py sync_youtube_uploads
```

## 6. 재생목록 구성

재생목록은 **우리 서비스 내부 개념**으로 만들고, 여러 영상을 묶어 보여주는 방식입니다.

```python
# app/admin.py
from django.contrib import admin
from app.models import YouTubeVideo, VideoPlaylist

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
	list_display = ("title", "channel_title", "published_at")
	search_fields = ("title", "video_id")

@admin.register(VideoPlaylist)
class VideoPlaylistAdmin(admin.ModelAdmin):
	list_display = ("name",)
	filter_horizontal = ("videos",)
```

Admin에서 `VideoPlaylist`를 만들고 `videos`에 원하는 영상을 추가하면 준비 완료입니다.

## 7. 임베딩 재생 화면 만들기

YouTube 임베딩 플레이어는 `listType=playlist`와 `list=videoId1,videoId2` 조합으로 여러 영상을 재생할 수 있습니다.

### 7-1. 뷰

```python
# app/views.py
from django.shortcuts import get_object_or_404, render
from app.models import VideoPlaylist

def playlist_embed(request, playlist_id: int):
	playlist = get_object_or_404(VideoPlaylist, id=playlist_id)
	video_ids = list(playlist.videos.values_list("video_id", flat=True))

	return render(
		request,
		"playlist_embed.html",
		{
			"playlist": playlist,
			"video_ids": ",".join(video_ids),
		},
	)
```

### 7-2. URL

```python
# app/urls.py
from django.urls import path
from app import views

urlpatterns = [
	path("playlist/<int:playlist_id>/", views.playlist_embed, name="playlist_embed"),
]
```

### 7-3. 템플릿

```html
<!-- templates/playlist_embed.html -->
<!doctype html>
<html lang="ko">
  <head>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<title>{{ playlist.name }}</title>
	<style>
	  body {
		font-family: "Noto Sans KR", sans-serif;
		margin: 24px;
	  }
	  .player {
		position: relative;
		padding-top: 56.25%;
	  }
	  .player iframe {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		border: 0;
	  }
	</style>
  </head>
  <body>
	<h1>{{ playlist.name }}</h1>
	<p>{{ playlist.description }}</p>
	<div class="player">
	  <iframe
		src="https://www.youtube.com/embed?listType=playlist&list={{ video_ids }}"
		allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
		allowfullscreen
		title="{{ playlist.name }}"
	  ></iframe>
	</div>
  </body>
</html>
```

이제 브라우저에서 `/playlist/1/`을 열면 Django에서 만든 재생목록이 임베딩 플레이어로 재생됩니다.

## 8. OAuth로 실제 유튜브 재생목록을 만들려면

서비스 내부 재생목록 대신, **유튜브 계정에 실제 재생목록을 만들고 편집**하려면 OAuth 인증이 필요합니다.

### 필요한 OAuth 범위

- `https://www.googleapis.com/auth/youtube`

### 대략적인 플로우

1. 사용자에게 Google 로그인 링크 제공
2. 동의 후 리디렉션 URI에서 `code` 수신
3. `code`를 토큰으로 교환
4. 토큰으로 `playlists.insert`, `playlistItems.insert` 호출

이 과정은 길어지므로 별도 글로 다루는 것을 추천합니다. 핵심은 **YouTube 계정에 쓰기 작업**이 들어가는 순간 OAuth가 필수라는 점입니다.

## 9. 운영 팁과 흔한 오류

### 쿼터(Quota) 관리

YouTube Data API는 요청 단위로 쿼터가 소모됩니다. `playlistItems.list`는 비교적 저렴하지만, 대량 호출은 주의가 필요합니다.

### 403: accessNotConfigured

API가 활성화되지 않은 경우입니다. 콘솔에서 YouTube Data API v3를 활성화했는지 확인하세요.

### 400: channelNotFound

채널 ID가 잘못됐거나 존재하지 않을 때 발생합니다. 채널 ID를 정확히 넣었는지 다시 확인하세요.

## 마무리

이제 YouTube Data API로 **최근 업로드 영상 수집 → Django 저장 → 재생목록 구성 → 임베딩 재생**까지 완성했습니다. 다음 단계로는 정기 동기화(크론, Celery), 썸네일 캐싱, 사용자별 재생목록 기능을 붙여 더 확장할 수 있습니다.
