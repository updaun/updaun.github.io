---
layout: post
title: "인스타그램 API 완벽 가이드: Meta 앱 등록부터 인스타그램 게시글 메트릭 조회까지"
date: 2026-03-04
categories: [api, instagram, meta, social-media]
tags: [instagram-api, meta-developers, api-integration, graph-api, social-media-analytics]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-03-04-instagram-api-guide.webp"
---

## 소개: 인스타그램 API로 할 수 있는 것들

인스타그램은 개인 프로필과 브랜드, 기업 계정으로 나뉘어 있으며, **비즈니스 또는 크리에이터 계정**만이 인스타그램 API를 통해 데이터에 접근할 수 있습니다. 인스타그램 API를 활용하면 게시글의 조회수(Impressions), 도달한 사람-명(Reach), 저장 수, 공유 수, 클릭 수, 좋아요 수, 댓글 수, 팔로워 이동, 프로필 방문 수 등의 **Insights 데이터**에 접근할 수 있으며, 게시글, 릴스, 스토리 등의 정보를 프로그래매틱하게 조회할 수 있습니다.

이 가이드에서는 Meta의 공식 개발자 페이지에서 Facebook과 인스타그램을 연동한 후, 실제로 인스타그램 비즈니스 계정의 메트릭 데이터를 API를 통해 조회하는 **전체 과정을 상세하게 설명**합니다. 초보자도 이 가이드를 따라하면 30분 안에 인스타그램 API를 활용할 수 있을 것입니다.

## 1단계: Meta 개발자 계정 생성 및 앱 등록

### Meta 개발자 페이지 접속

모든 과정은 **[Meta Developers 공식 사이트](https://developers.facebook.com/)**에서 시작합니다. 이 사이트는 Facebook, Instagram, WhatsApp, Messenger 등 Meta의 모든 서비스를 위한 개발자 도구를 제공하는 공식 플랫폼입니다.

1. [developers.facebook.com](https://developers.facebook.com/)에 접속합니다.
2. 우측 상단의 **"로그인"** 버튼을 클릭하고, 자신의 Facebook 계정으로 로그인합니다. (Facebook 계정이 없다면 먼저 생성해야 합니다)
3. 로그인 후, 좌측 메뉴에서 **"내 앱"** → **"앱 만들기"**를 클릭합니다.

### 새 앱 생성하기

앱을 만들기 위한 대화창이 나타나면 다음과 같이 진행합니다:

1. **앱 이름 입력**: "Instagram Analytics" 또는 원하는 앱 이름을 입력합니다. 이 이름은 나중에 변경할 수 있으므로, 현재는 프로젝트를 대표하는 이름을 지으면 됩니다.

2. **앱 유형 선택**: 대화창에서 **"사용할 앱 유형을 선택하세요"**라는 질문이 나옵니다. 여기서 **"기타"**를 선택합니다. (비즈니스 유형에 따라 "소비자", "기업", "기타" 중 하나를 선택할 수 있습니다)

3. **앱 용도 설명**: 간단한 설명을 입력합니다. 예: "인스타그램 게시글의 조회수, 좋아요수, 댓글 수 등을 수집하고 분석하기 위한 앱"

4. **연락처 정보 입력**: 이메일 주소를 입력하고 동의 사항에 체크한 후 **"앱 만들기"**를 클릭합니다.

### 앱 ID와 App Secret 확인하기

앱이 성공적으로 생성되면, 앱의 대시보드(Dashboard) 화면이 자동으로 표시됩니다. 우측 상단에 **"앱 ID"**와 **"App Secret"** 정보가 표시됩니다. 이 두 가지 정보는 매우 중요하므로 **안전한 곳에 메모**해두어야 합니다 (특히 App Secret은 노출되면 안 됨).

- **앱 ID (App ID)**: 앱을 식별하는 고유한 번호 (예: 1234567890123456)
- **App Secret**: 앱 인증을 위한 비밀 키이며, 절대로 공개되면 안 됩니다.

대시보드 좌측의 탭 중 **"설정"** → **"기본"**을 클릭하면 더 자세한 앱 정보를 확인할 수 있습니다.

## 2단계: Instagram Graph API 제품 추가하기

### 제품 추가 메뉴 접근

Meta 앱을 생성한 후에는, 이 앱에 어떤 API를 사용할 것인지 선택해야 합니다. 우리는 인스타그램 데이터를 다루므로 **Instagram Graph API**를 추가해야 합니다.

1. 앱 대시보드 좌측 메뉴에서 **"제품"** 섹션을 찾습니다.
2. **"제품 추가"** 또는 **"+"** 아이콘을 클릭합니다.
3. 팝업 창에서 사용 가능한 제품 목록이 표시되는데, 그 중에서 **"Instagram Graph API"**를 찾아 클릭합니다.

### Instagram Graph API 추가 완료

제품 추가를 클릭하면 몇 가지 권한과 용도에 대한 설정이 나타날 수 있습니다. 기본 설정으로 진행해도 괜찮으며, 나중에 더 세부적인 권한 설정을 할 수 있습니다. 

설정 후 **"추가"** 또는 **"완료"** 버튼을 클릭하면 Instagram Graph API가 앱에 추가됩니다.

## 3단계: Facebook 페이지와 인스타그램 계정 연동하기

인스타그램 API를 사용하려면, **Facebook 페이지와 인스타그램 비즈니스/크리에이터 계정을 연동**해야 합니다. 이 과정이 다소 복잡해 보일 수 있지만, 한 단계씩 따라하면 충분히 완료할 수 있습니다.

### Facebook 페이지 생성 또는 확인

먼저, 비즈니스용 Facebook 페이지가 필요합니다. 이미 Facebook 페이지가 있다면 건너뛸 수 있습니다.

1. [facebook.com](https://www.facebook.com/)에 접속하고 로그인합니다.
2. 좌측 하단의 **"페이지 만들기"**를 클릭하거나, 메뉴에서 **"페이지"**를 선택합니다.
3. 비즈니스 또는 브랜드 유형을 선택하고 페이지를 생성합니다.
4. 페이지의 **"정보"** 섹션으로 가서 페이지 ID를 기록해둡니다. (URL 설정에서도 페이지 ID를 확인할 수 있습니다)

Facebook 페이지는 인스타그램 계정과 연결되어야 하며, 페이지 ID는 나중에 API 설정에 필요합니다.

### 인스타그램 비즈니스/크리에이터 계정 준비

인스타그램에 로그인한 후:

1. 프로필의 **"설정"** → **"계정 유형 및 도구"** 또는 **"전환"**을 선택합니다.
2. **"비즈니스 계정으로 전환"** 또는 **"크리에이터 계정으로 전환"**을 선택합니다. (개인 계정만으로는 API 접근이 불가능합니다)
3. **"Facebook 페이지와 연결"**을 선택하고, 위에서 생성한 Facebook 페이지를 선택합니다.
4. 프로필 정보 (카테고리, 이름, 설명 등)를 입력하고 완료합니다.

이제 인스타그램 계정이 Facebook 페이지와 연동되었습니다.

### App Dashboard에서 Instagram 비즈니스 계정 연결

Meta Developers 대시보드로 돌아가서:

1. 좌측 메뉴의 **"설정"** → **"기본"**   또는 특정 제품의 설정 섹션에 들어갑니다.
2. **"비즈니스 계정 관리"** 또는 **"권한"**이라는 섹션을 찾습니다.
3. **"시스템 사용자 생성"** 또는 **"액세스 토큰 생성"** 옵션을 찾으면, 앱에 필요한 권한을 설정합니다.

이 과정에서는 다음 권한들이 필요합니다:
- `instagram_basic`: 인스타그램 기본 정보 조회
- `instagram_manage_messages`: 메시지 관리 (선택사항)
- `pages_read_engagement`: 페이지 참여도 데이터 조회
- `pages_read_user_content`: 페이지 콘텐츠 조회
- `business_management`: 비즈니스 프로필 관리

필요한 권한들을 선택한 후 진행합니다.

## 4단계: 액세스 토큰 생성하기

### 액세스 토큰의 종류와 이해

Meta의 API를 사용할 때는 **액세스 토큰(Access Token)**이라는 인증 토큰이 필요합니다. 액세스 토큰에는 여러 종류가 있으며, 각각의 용도와 유효 기간이 다릅니다:

1. **User Access Token** - 특정 사용자의 권한으로 작동하며, 유효기간은 약 60일입니다. 주로 테스트 및 개발 단계에서 사용합니다.
2. **App Access Token** - 앱 자체의 권한으로 작동하며, 유효기간은 무제한입니다. 프로덕션 환경에서는 이것을 사용하는 것이 권장됩니다.
3. **Page Access Token** - 특정 Facebook 페이지의 권한으로 작동하며, 유효기간은 무제한입니다. 인스타그램 비즈니스 계정에 연연결된 Facebook 페이지의 토큰입니다.

인스타그램 API를 사용할 때는 주로 **Page Access Token을 사용하는 것이 권장**됩니다. 왜냐하면 특정 페이지와 연결된 인스타그램 계정에만 접근하도록 제한할 수 있기 때문입니다.

### Graph API Explorer를 이용한 토큰 생성 (가장 간단한 방법)

개발 단계에서는 **Graph API Explorer**를 사용하여 빠르게 토큰을 생성할 수 있습니다:

1. [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer/)에 접속합니다.
2. 우측 상단의 **드롭다운**에서 자신이 만든 앱을 선택합니다.
3. 좌측 상단의 **드롭다운**을 클릭하고, **"User Token"** 또는 **"Page Token"**을 선택합니다.
4. **"페이지 관리"** 또는 **"액세스 토큰 생성"** 옵션을 클릭합니다.
5. 권한 요청 팝업에서 필요한 권한들을 선택하고 **"승인"**을 클릭합니다.

이제 긴 문자열의 액세스 토큰이 화면에 표시됩니다. 이를 복사하여 안전한 곳에 저장합니다. **절대로 공개된 저장소(GitHub 등)에 업로드하면 안 됩니다.**

### 프로덕션 환경을 위한 토큰 관리

프로덕션 환경에서의 토큰 관리는 다음과 같습니다:

1. **앱 토큰 생성**: Meta Developers 대시보드의 **"설정"** → **"기본"**에서 App ID와 App Secret 정보를 이용해 App Access Token을 생성할 수 있습니다.

2. **페이지 토큰 관리**: 프로덕션에서 특정 인스타그램 비즈니스 계정의 데이터에 접근하려면 **Page Token**을 사용합니다. 이는 자신의 Facebook 페이지 설정에서 생성하고 관리할 수 있습니다.

3. **환경 변수로 관리**: 토큰을 코드에 직접 입력하면 안 되며, 반드시 **.env 파일** 또는 **환경 변수**로 관리해야 합니다:

```bash
INSTAGRAM_ACCESS_TOKEN=your_long_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id
```

## 5단계: 인스타그램 비즈니스 계정 ID 확인하기

API를 사용하려면 자신의 **인스타그램 비즈니스 계정 ID**를 알아야 합니다. 이는 Facebook 페이지에 연결된 인스타그램 계정의 고유 ID입니다.

### 방법 1: Graph API Explorer를 이용한 확인 (가장 빠른 방법)

1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/)에 접속합니다.
2. 위의 검색창에 다음 쿼리를 입력합니다:
```
/me/instagram_business_accounts
```

3. **[GET]** 버튼을 클릭하면, 연결된 인스타그램 비즈니스 계정의 ID와 이름이 JSON 형식으로 반환됩니다:

```json
{
  "data": [
    {
      "id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID",
      "name": "Your Instagram Business Account Name"
    }
  ]
}
```

이 ID를 복사하여 저장합니다.

### 방법 2: Facebook 페이지 설정을 통한 확인

1. Facebook 페이지로 이동합니다.
2. **"설정"** → **"인스타그램 계정"** 또는 **"앱 및 웹사이트"**를 찾습니다.
이 ID를 복사하여 저장합니다.

### 방법 2: Facebook 페이지 설정을 통한 확인

1. Facebook 페이지로 이동합니다.
2. **"설정"** → **"인스타그램 계정"** 또는 **"앱 및 웹사이트"**를 찾습니다.
3. 연결된 인스타그램 계정 정보에서 프로필의 **"사용자 ID"** 또는 **"계정 ID"**를 찾을 수 있습니다.

## 6단계: Instagram Graph API 기본 이해하기

### API 기본 구조

Instagram Graph API는 RESTful API이며, 모든 요청은 다음과 같은 기본 구조를 따릅니다:

```
GET https://graph.instagram.com/{api-version}/{object-id}?fields={fields}&access_token={your-access-token}
```

여기서:
- **{api-version}**: API 버전 (현재 기본값은 v18.0, 자주 업데이트됩니다)
- **{object-id}**: 조회할 객체의 ID (인스타그램 비즈니스 계정 ID, 게시글 ID 등)
- **{fields}**: 응답으로 받을 데이터 필드들
- **{your-access-token}**: 위에서 생성한 액세스 토큰

REST API를 실습할 때는 cURL이나 Postman 같은 도구를 사용하거나, 계속해서 Graph API Explorer를 사용할 수 있습니다.

### Instagram Graph API의 주요 객체 계층 구조

인스타그램 API에서는 계층적인 객체 구조를 가집니다:

```
Instagram Business Account
  ├── Media (게시글, 릴스, 스토리)
  ├── Insights (통계 데이터)
  ├── Followers (팔로워 정보)
  └── Hashtag (해시태그)
```

각 게시글은 고유한 Media ID를 가지며, 이를 통해 게시글의 상세 정보와 인사이트를 조회할 수 있습니다.

## 7단계: 게시글 목록 조회하기

### 전체 게시글 목록 조회

자신의 인스타그램 비즈니스 계정에 업로드한 모든 게시글을 조회하려면:

**Graph API Explorer에서:**

```
/{YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID}/media
```

를 입력하고 **[GET]** 버튼을 클릭합니다.

또는 **cURL**을 이용하여:

```bash
curl -X GET "https://graph.instagram.com/v18.0/{YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID}/media?fields=id,caption,media_type,timestamp&access_token={YOUR_ACCESS_TOKEN}"
```

**응답 예시:**

```json
{
  "data": [
    {
      "id": "17899234343421234",
      "caption": "Beautiful sunset ☀️",
      "media_type": "IMAGE",
      "timestamp": "2026-03-02T10:30:00+0000"
    },
    {
      "id": "17899234343421235",
      "caption": "Weekend vibes 🌿",
      "media_type": "CAROUSEL_ALBUM",
      "timestamp": "2026-03-01T14:20:00+0000"
    }
  ],
  "paging": {
    "cursors": {
      "before": "QVFIUnAbCdKlvGtMiE...",
      "after": "QVFIUSBkRkxxNXpaYlo..."
    }
  }
}
```

반환된 데이터에서:
- **id**: 게시글의 고유 ID (이를 통해 상세 정보 조회 가능)
- **caption**: 게시글의 글귀
- **media_type**: 게시글의 타입 (IMAGE, VIDEO, CAROUSEL_ALBUM 등)
- **timestamp**: 게시글이 업로드된 시간
- **paging**: 페이지네이션 정보 (더 많은 게시글이 있을 때 다음 페이지를 불러오는 데 사용)

### 특정 게시글의 상세 정보 조회

특정 게시글의 ID를 알면, 그 게시글의 상세 정보를 조회할 수 있습니다:

```
/{MEDIA_ID}?fields=id,caption,like_count,comments_count,media_type,timestamp,permalink
```

**응답 예시:**

```json
{
  "id": "17899234343421234",
  "caption": "Beautiful sunset ☀️",
  "like_count": 245,
  "comments_count": 12,
  "media_type": "IMAGE",
  "timestamp": "2026-03-02T10:30:00+0000",
  "permalink": "https://www.instagram.com/p/ABC123..."
}
```

**중요:** 여기서 `like_count`와 `comments_count`는 **즉시 조회 가능**한 필드이지만, 더 자세한 Insights 데이터 (조회수, 도달한 사람의 수, 기기별 통계 등)는 별도의 Insights 엔드포인트에서 조회해야 합니다.

## 8단계: Insights API를 통한 상세 메트릭 조회

### Insights API 개요

Insights API는 인스타그램 비즈니스 계정과 그 게시글의 **상세한 성과 데이터**를 제공합니다. 이를 통해 조회수, 도달한 사람의 수, 저장 수, 공유 수, 클릭 수, 기기별 통계, 위치별 통계 등을 얻을 수 있습니다.

Insights 데이터는 다음과 같은 특징이 있습니다:

- **비즈니스/크리에이터 계정 필수**: 개인 계정으로는 조회 불가능
- **지정된 필드만 조회 가능**: 모든 필드를 한 번에 조회하면 안 되고, 필요한 필드를 명시적으로 요청해야 함
- **과거 데이터 조회 가능**: 특정 기간의 Insights 통계를 조회할 수 있음
- **실시간 데이터 아님**: 최대 24시간의 지연이 있을 수 있음

### 게시글의 Insights 데이터 조회

특정 게시글의 성과 데이터를 조회하려면:

```
/{MEDIA_ID}/insights?metric={metric_name}&breakdown={breakdown_type}
```

**자주 사용되는 메트릭들:**

| 메트릭 | 설명 | 타입 |
|--------|-----|------|
| `impressions` | 게시글이 화면에 표시된 횟수 | 정수 |
| `reach` | 게시글을 본 고유한 사람의 수 | 정수 |
| `saved` | 게시글이 저장된 횟수 | 정수 |
| `shares` | 게시글이 공유된 횟수 | 정수 |
| `engagement` | 좋아요, 댓글, 저장, 공유의 합계 | 정수 |
| `likes` | 게시글이 받은 좋아요 수 | 정수 |
| `comments` | 게시글이 받은 댓글 수 | 정수 |

**Graph API Explorer를 이용한 조회:**

```
/{MEDIA_ID}/insights?metric=impressions,reach,saved,engagement,likes,comments
```

를 입력하고 **[GET]** 버튼을 클릭합니다.

**응답 예시:**

```json
{
  "data": [
    {
      "name": "impressions",
      "period": "lifetime",
      "values": [{"value": 1234}],
      "title": "Impressions"
    },
    {
      "name": "reach",
      "period": "lifetime",
      "values": [{"value": 856}],
      "title": "Reach"
    },
    {
      "name": "saved",
      "period": "lifetime",
      "values": [{"value": 45}],
      "title": "Saved"
    },
    {
      "name": "engagement",
      "period": "lifetime",
      "values": [{"value": 312}],
      "title": "Post Engagement"
    },
    {
      "name": "likes",
      "period": "lifetime",
      "values": [{"value": 245}],
      "title": "Like Count"
    },
    {
      "name": "comments",
      "period": "lifetime",
      "values": [{"value": 12}],
      "title": "Comments"
    }
  ]
}
```

### 비디오 조회수 추가 메트릭

비디오 게시글의 경우, 추가적인 메트릭을 조회할 수 있습니다:

```
/{MEDIA_ID}/insights?metric=video_views,video_play_actions
```

- **video_views**: 비디오가 재생된 횟수
- **video_play_actions**: 사용자가 비디오 재생을 클릭한 횟수

### 스토리의 성과 데이터 조회

스토리는 게시글보다 다른 Insights 메트릭을 제공합니다:

```
/{STORY_ID}/insights?metric=impressions,reach,exits,taps_back,taps_forward
```

- **impressions**: 스토리가 표시된 횟수
- **reach**: 스토리를 본 고유한 사람의 수
- **exits**: 스토리에서 나간 횟수
- **taps_back**: 뒤로 가기 탭
- **taps_forward**: 앞으로 가기 탭

### 릴스의 성과 데이터 조회

릴스는 가장 부자가 많은 메트릭을 제공합니다:

```
/{REELS_ID}/insights?metric=impressions,reach,plays,saved,shares,likes,comments
```

릴스의 경우 게시글보다 높은 도달률과 참여도를 보이는 경향이 있습니다.

## 9단계: 계정 수준의 Insights 조회

특정 게시글이 아닌, **전체 계정의 성과 데이터**를 조회할 수도 있습니다:

```
/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/insights?metric=profile_views,follower_count,reach
```

**주요 계정 수준 메트릭:**

| 메트릭 | 설명 |
|--------|-----|
| `profile_views` | 프로필이 조회된 횟수 |
| `follower_count` | 현재 팔로워 수 |
| `reach` | 전체 팔로워 중 콘텐츠에 도달한 사람 |
| `impressions` | 전체 콘텐츠가 노출된 횟수 |
| `audience_city` | 도시별 팔로워 분포 |
| `audience_country` | 국가별 팔로워 분포 |
| `audience_gender_age` | 성별/나이별 팔로워 분포 |

**계정 Insights 조회 예시:**

```bash
curl -X GET "https://graph.instagram.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/insights?metric=profile_views,follower_count,reach,impressions&period=day&access_token={YOUR_ACCESS_TOKEN}"
```

**응답 예시:**

```json
{
  "data": [
    {
      "name": "profile_views",
      "period": "day",
      "values": [
        {"value": 523, "end_time": "2026-03-04T23:59:59+0000"}
      ]
    },
    {
      "name": "follower_count",
      "period": "day",
      "values": [
        {"value": 12450, "end_time": "2026-03-04T23:59:59+0000"}
      ]
    },
    {
      "name": "reach",
      "period": "day",
      "values": [
        {"value": 3421, "end_time": "2026-03-04T23:59:59+0000"}
      ]
    }
  ]
}
```

## 10단계: 프로그래밍 코드로 구현하기

이제 실제 프로그래밍 환경에서 API를 사용하는 코드를 작성해봅시다. Python과 JavaScript 예제를 준비했습니다.

### Python 예제

**필요한 라이브러리 설치:**

```bash
pip install requests python-dotenv
```

**기본 설정 (.env 파일):**

```env
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id_here
```

**Python 코드 예제:**

```python
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 기본 설정
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
API_VERSION = 'v18.0'
BASE_URL = f'https://graph.instagram.com/{API_VERSION}'

class InstagramAnalytics:
    def __init__(self, access_token, business_account_id):
        self.access_token = access_token
        self.business_account_id = business_account_id
    
    def get_media_list(self):
        """모든 게시글 목록 조회"""
        url = f"{BASE_URL}/{self.business_account_id}/media"
        params = {
            'fields': 'id,caption,media_type,timestamp,permalink',
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def get_media_insights(self, media_id):
        """특정 게시글의 성과 데이터 조회"""
        url = f"{BASE_URL}/{media_id}/insights"
        params = {
            'metric': 'impressions,reach,saved,engagement,likes,comments',
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        
        # 응답을 읽기 좋은 형식으로 변환
        insights_data = response.json()
        formatted_insights = {}
        
        for item in insights_data.get('data', []):
            metric_name = item.get('name')
            metric_value = item.get('values', [{}])[0].get('value', 0)
            formatted_insights[metric_name] = metric_value
        
        return formatted_insights
    
    def get_account_insights(self, period='day'):
        """계정 수준의 성과 데이터 조회"""
        url = f"{BASE_URL}/{self.business_account_id}/insights"
        params = {
            'metric': 'profile_views,follower_count,reach,impressions',
            'period': period,
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def analyze_all_posts(self):
        """모든 게시글의 성과 데이터를 조회하고 분석"""
        media_list_response = self.get_media_list()
        media_list = media_list_response.get('data', [])
        
        all_analysis = []
        
        for media in media_list:
            media_id = media.get('id')
            caption = media.get('caption', '').replace('\n', ' ')[:50] + '...'
            media_type = media.get('media_type')
            timestamp = media.get('timestamp')
            
            # 각 게시글의 인사이트 조회
            insights = self.get_media_insights(media_id)
            
            analysis = {
                'media_id': media_id,
                'caption': caption,
                'type': media_type,
                'timestamp': timestamp,
                'impressions': insights.get('impressions', 0),
                'reach': insights.get('reach', 0),
                'engagement': insights.get('engagement', 0),
                'likes': insights.get('likes', 0),
                'comments': insights.get('comments', 0),
                'saved': insights.get('saved', 0),
                'engagement_rate': (
                    insights.get('engagement', 0) / 
                    insights.get('reach', 1) * 100 
                    if insights.get('reach', 0) > 0 else 0
                )
            }
            
            all_analysis.append(analysis)
        
        return all_analysis

# 사용 예제
if __name__ == '__main__':
    # InstagramAnalytics 인스턴스 생성
    analytics = InstagramAnalytics(ACCESS_TOKEN, BUSINESS_ACCOUNT_ID)
    
    # 모든 게시글 분석
    print("📊 인스타그램 게시글 분석 시작...\n")
    
    analysis_results = analytics.analyze_all_posts()
    
    # 결과 출력
    for idx, post_data in enumerate(analysis_results, 1):
        print(f"게시글 {idx}")
        print(f"  제목: {post_data['caption']}")
        print(f"  타입: {post_data['type']}")
        print(f"  조회수: {post_data['impressions']:,}")
        print(f"  도달: {post_data['reach']:,}명")
        print(f"  좋아요: {post_data['likes']:,}")
        print(f"  댓글: {post_data['comments']}")
        print(f"  저장: {post_data['saved']}")
        print(f"  참여도: {post_data['engagement']:,} (참여율: {post_data['engagement_rate']:.2f}%)")
        print()
    
    # 계정 수준의 통계
    print("\n📈 계정 전체 통계")
    account_insights = analytics.get_account_insights(period='day')
    print(account_insights)
```

### JavaScript/Node.js 예제

**필요한 패키지 설치:**

```bash
npm install axios dotenv
```

**기본 설정 (.env 파일):**

```env
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id_here
```

**JavaScript 코드 예제:**

```javascript
require('dotenv').config();
const axios = require('axios');

const ACCESS_TOKEN = process.env.INSTAGRAM_ACCESS_TOKEN;
const BUSINESS_ACCOUNT_ID = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;
const API_VERSION = 'v18.0';
const BASE_URL = `https://graph.instagram.com/${API_VERSION}`;

class InstagramAnalytics {
    constructor(accessToken, businessAccountId) {
        this.accessToken = accessToken;
        this.businessAccountId = businessAccountId;
        this.apiClient = axios.create({
            baseURL: BASE_URL,
            timeout: 10000
        });
    }
    
    async getMediaList() {
        try {
            const response = await this.apiClient.get(
                `/${this.businessAccountId}/media`,
                {
                    params: {
                        fields: 'id,caption,media_type,timestamp,permalink',
                        access_token: this.accessToken
                    }
                }
            );
            return response.data;
        } catch (error) {
            console.error('게시글 목록 조회 실패:', error.message);
            return null;
        }
    }
    
    async getMediaInsights(mediaId) {
        try {
            const response = await this.apiClient.get(
                `/${mediaId}/insights`,
                {
                    params: {
                        metric: 'impressions,reach,saved,engagement,likes,comments',
                        access_token: this.accessToken
                    }
                }
            );
            
            // 응답을 정리된 형식으로 변환
            const formattedInsights = {};
            response.data.data.forEach(item => {
                const metricName = item.name;
                const metricValue = item.values[0].value;
                formattedInsights[metricName] = metricValue;
            });
            
            return formattedInsights;
        } catch (error) {
            console.error(`게시글 ${mediaId}의 인사이트 조회 실패:`, error.message);
            return null;
        }
    }
    
    async getAccountInsights(period = 'day') {
        try {
            const response = await this.apiClient.get(
                `/${this.businessAccountId}/insights`,
                {
                    params: {
                        metric: 'profile_views,follower_count,reach,impressions',
                        period: period,
                        access_token: this.accessToken
                    }
                }
            );
            return response.data;
        } catch (error) {
            console.error('계정 인사이트 조회 실패:', error.message);
            return null;
        }
    }
    
    async analyzeAllPosts() {
        const mediaListResponse = await this.getMediaList();
        if (!mediaListResponse) return [];
        
        const mediaList = mediaListResponse.data || [];
        const allAnalysis = [];
        
        for (const media of mediaList) {
            const mediaId = media.id;
            const caption = media.caption.substring(0, 50) + '...';
            const mediaType = media.media_type;
            const timestamp = media.timestamp;
            
            // 각 게시글의 인사이트 조회
            const insights = await this.getMediaInsights(mediaId);
            
            if (insights) {
                const analysis = {
                    media_id: mediaId,
                    caption: caption,
                    type: mediaType,
                    timestamp: timestamp,
                    impressions: insights.impressions || 0,
                    reach: insights.reach || 0,
                    engagement: insights.engagement || 0,
                    likes: insights.likes || 0,
                    comments: insights.comments || 0,
                    saved: insights.saved || 0,
                    engagement_rate: insights.reach > 0 
                        ? (insights.engagement / insights.reach * 100).toFixed(2)
                        : 0
                };
                
                allAnalysis.push(analysis);
            }
        }
        
        return allAnalysis;
    }
}

// 사용 예제
(async () => {
    const analytics = new InstagramAnalytics(ACCESS_TOKEN, BUSINESS_ACCOUNT_ID);
    
    console.log('📊 인스타그램 게시글 분석 시작...\n');
    
    const results = await analytics.analyzeAllPosts();
    
    results.forEach((post, idx) => {
        console.log(`게시글 ${idx + 1}`);
        console.log(`  제목: ${post.caption}`);
        console.log(`  타입: ${post.type}`);
        console.log(`  조회수: ${post.impressions.toLocaleString()}`);
        console.log(`  도달: ${post.reach.toLocaleString()}명`);
        console.log(`  좋아요: ${post.likes.toLocaleString()}`);
        console.log(`  댓글: ${post.comments}`);
        console.log(`  저장: ${post.saved}`);
        console.log(`  참여도: ${post.engagement.toLocaleString()} (참여율: ${post.engagement_rate}%)\n`);
    });
    
    // 계정 수준의 통계
    console.log('\n📈 계정 전체 통계');
    const accountInsights = await analytics.getAccountInsights('day');
    console.log(JSON.stringify(accountInsights, null, 2));
})();
```

## 11단계: 고급 기능 - 데이터 수집 자동화

### 주기적인 데이터 수집

실무에서는 매일 특정 시간에 인스타그램 데이터를 자동으로 수집하고 저장해야 하는 경우가 많습니다. 이를 위해 **스케줄러(Scheduler)**를 사용할 수 있습니다.

**Python APScheduler를 이용한 자동 수집:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
import json
from datetime import datetime

class InstagramDataCollector:
    def __init__(self, access_token, business_account_id):
        self.analytics = InstagramAnalytics(access_token, business_account_id)
        self.scheduler = BackgroundScheduler()
    
    def save_data_to_file(self, data, filename=None):
        """수집한 데이터를 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'instagram_data_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 데이터 저장 완료: {filename}")
    
    def daily_collection_task(self):
        """하루에 한 번 실행될 수집 작업"""
        print(f"🔄 [{datetime.now()}] 데이터 수집 시작...")
        
        # 모든 게시글 분석 데이터 수집
        analysis_results = self.analytics.analyze_all_posts()
        
        # 계정 통계 수집
        account_insights = self.analytics.get_account_insights(period='day')
        
        # 통합 데이터
        collection_data = {
            'timestamp': datetime.now().isoformat(),
            'post_analytics': analysis_results,
            'account_insights': account_insights
        }
        
        # 데이터 저장
        self.save_data_to_file(collection_data)
    
    def start_scheduler(self, hour=9, minute=0):
        """매일 지정된 시간에 데이터 수집 시작"""
        self.scheduler.add_job(
            self.daily_collection_task,
            'cron',
            hour=hour,
            minute=minute,
            id='instagram_daily_collection'
        )
        self.scheduler.start()
        print(f"⏰ 매일 {hour}:{minute:02d}에 데이터 수집이 예약되었습니다.")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        print("⏹ 스케줄러를 중지했습니다.")

# 사용 예제
if __name__ == '__main__':
    collector = InstagramDataCollector(ACCESS_TOKEN, BUSINESS_ACCOUNT_ID)
    
    # 매일 오전 9시에 데이터 수집 시작
    collector.start_scheduler(hour=9, minute=0)
    
    # 프로그램 실행 유지
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        collector.stop_scheduler()
```

### 데이터 베이스에 저장하기

더 큰 규모의 프로젝트에서는 데이터베이스에 저장하는 것이 권장됩니다:

```python
import sqlite3
from datetime import datetime

class InstagramDatabaseManager:
    def __init__(self, db_file='instagram_analytics.db'):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """데이터베이스 테이블 생성"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 게시글 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                caption TEXT,
                media_type TEXT,
                timestamp TEXT
            )
        ''')
        
        # 게시글 메트릭 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                collected_date TEXT,
                impressions INTEGER,
                reach INTEGER,
                engagement INTEGER,
                likes INTEGER,
                comments INTEGER,
                saved INTEGER,
                engagement_rate REAL,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_post_metric(self, post_data):
        """게시글 메트릭을 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 먼저 포스트 정보 저장
        cursor.execute('''
            INSERT OR IGNORE INTO posts (id, caption, media_type, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (post_data['media_id'], post_data['caption'], 
              post_data['type'], post_data['timestamp']))
        
        # 메트릭 정보 저장
        cursor.execute('''
            INSERT INTO post_metrics 
            (post_id, collected_date, impressions, reach, engagement, likes, comments, saved, engagement_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (post_data['media_id'], datetime.now().isoformat(),
              post_data['impressions'], post_data['reach'], post_data['engagement'],
              post_data['likes'], post_data['comments'], post_data['saved'],
              post_data['engagement_rate']))
        
        conn.commit()
        conn.close()
    
    def get_post_metrics_history(self, post_id, days=30):
        """특정 게시글의 최근 메트릭 이력 조회"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT * FROM post_metrics
            WHERE post_id = ?
            AND collected_date > datetime('now', '-{days} days')
            ORDER BY collected_date DESC
        ''', (post_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
```

## 12단계: 일반적인 문제 해결

### 1. 권한 오류 (Permission Error)

**에러 메시지:**
```json
{
  "error": {
    "message": "Requires the following permissions: instagram_basic",
    "type": "OAuthException",
    "code": 200
  }
}
```

**해결 방법:**
- Meta Developers 대시보드에서 앱 설정을 확인합니다.
- **설정** → **권한 및 역할** 또는 **권한**에서 필요한 권한을 추가해야 합니다.
- 부족한 권한: `instagram_basic`, `pages_read_engagement`, `pages_read_user_content`
- 권한을 추가한 후 새 액세스 토큰을 생성합니다.

### 2. 무효한 액세스 토큰

**에러 메시지:**
```json
{
  "error": {
    "message": "Invalid OAuth access token",
    "type": "OAuthException",
    "code": 190
  }
}
```

**해결 방법:**
- 액세스 토큰의 유효기간이 만료되었을 수 있습니다. **User Access Token**은 약 60일 유효합니다.
- 새 토큰을 생성하세요: [Graph API Explorer](https://developers.facebook.com/tools/explorer/)에서 새로 생성
- 프로덕션 환경에서는 **App Access Token** 또는 **Page Access Token**을 사용하는 것이 권장됩니다 (유효기간 무제한).

### 3. 비즈니스 계정이 아님

**에러 메시지:**
```json
{
  "error": {
    "message": "User must have a Business or Creator Account to use Instagram Insights",
    "type": "OAuthException"
  }
}
```

**해결 방법:**
- 개인 인스타그램 계정을 비즈니스/크리에이터 계정으로 전환해야 합니다.
- 인스타그램 앱 → **프로필** → **설정** → **계정** → **계정 유형 및 도구**에서 **비즈니스 계정으로 전환** 선택
- Facebook 페이지와 연동 후 다시 시도

### 4. Rate Limit (요청 제한)

**에러 메시지:**
```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "OAuthException",
    "code": 17
  }
}
```

**해결 방법:**
- Meta API는 시간당 요청 수 제한이 있습니다.
- 일반 개발자: 시간당 최대 200 요청
- 요청 간격을 늘리거나, 배치 요청을 사용합니다:

```python
import time

def rate_limited_request(api_call_func, retry_count=3):
    for attempt in range(retry_count):
        try:
            response = api_call_func()
            return response
        except RateLimitError:
            wait_time = 60 * (2 ** attempt)  # 지수 백오프
            print(f"Rate limit 도달. {wait_time}초 대기...")
            time.sleep(wait_time)
    
    raise Exception("최대 재시도 횟수 초과")
```

## 13단계: 모범 사례 및 최적화 팁

### 1. 토큰 보안

- 절대로 액세스 토큰을 코드에 하드코딩하지 마세요.
- 환경 변수나 `.env` 파일 (`.gitignore`에 포함)을 사용하세요.
- 토큰이 노출되었다면 즉시 Meta Developers에서 토큰을 폐기하세요.

### 2. API 요청 최적화

```python
# ❌ 좋지 않은 예: 각 게시글마다 별도 요청
for post in posts:
    insights = get_post_insights(post.id)

# ✅ 좋은 예: 배치 요청 사용
# (가능한 경우 한 번에 여러 게시글의 정보 조회)
```

### 3. 에러 처리

모든 API 호출에 적절한 에러 처리를 추가하세요:

```python
def safe_api_call(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프
            else:
                raise
        except OAuthException:
            # 인증 오류는 재시도하지 않음
            raise
```

### 4. 데이터 캐싱

API 요청을 줄이기 위해 데이터를 캐싱하는 것이 좋습니다:

```python
from functools import lru_cache
import time

class CachedInstagramAPI:
    def __init__(self, cache_duration=3600):  # 1시간
        self.cache = {}
        self.cache_duration = cache_duration
    
    def get_with_cache(self, key, api_call_func):
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return cached_data
        
        # 캐시가 없거나 만료됨
        data = api_call_func()
        self.cache[key] = (data, time.time())
        
        return data
```

## 결론

인스타그램 API를 통해 게시글의 조회수, 좋아요수, 댓글 수 등의 상세한 메트릭 데이터를 프로그래매틱하게 수집할 수 있습니다. 이 가이드에서 다룬 단계들을 순서대로 따라하면:

1. ✅ Meta 개발자 계정에서 앱을 등록하고
2. ✅ Instagram Graph API 권한을 설정하고
3. ✅ 액세스 토큰을 생성하고
4. ✅ 게시글 목록과 Insights 데이터를 조회하고
5. ✅ Python이나 JavaScript로 실제 코드를 작성할 수 있습니다

이러한 API를 활용하면 인스타그램 성과를 자동으로 추적하고, 가장 인기 있는 콘텐츠를 분석하며, 데이터 기반의 콘텐츠 전략을 수립할 수 있습니다. 추가적으로 필요한 정보는 [Meta Developers 공식 문서](https://developers.facebook.com/docs/instagram-api)에서 확인하시기 바랍니다.

Happy coding! 🚀
```
```

