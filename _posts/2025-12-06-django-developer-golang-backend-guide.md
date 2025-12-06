---
layout: post
title: "Django 개발자를 위한 Golang 백엔드 완벽 가이드 - Echo + GORM으로 CRUD 서버 만들기"
categories: [Backend, Golang]
tags: [golang, go, echo, gorm, django, backend, web-framework, orm, crud, tutorial]
date: 2025-12-06 09:00:00 +0900
---

## 1. Django 개발자, Golang으로 백엔드 서버를 시작하다

### 1.1 왜 Django 개발자가 Golang을 배워야 할까?

Django는 훌륭한 프레임워크입니다. "Batteries-included" 철학으로 ORM, Admin, 인증, 템플릿 엔진까지 모든 것이 갖춰져 있죠. 하지만 다음과 같은 상황에서 Golang을 고려하게 됩니다:

```yaml
Django의 한계:
  성능:
    - Python GIL로 인한 멀티코어 활용 제한
    - 동시 요청 처리 속도 (1000 req/s)
    - 메모리 사용량 (평균 100-200MB/프로세스)
  
  배포:
    - 복잡한 의존성 관리 (virtualenv, requirements.txt)
    - 컨테이너 이미지 크기 (500MB~1GB)
    - 시작 시간 (5-10초)

Golang의 장점:
  성능:
    - 네이티브 동시성 (Goroutine)
    - 동시 요청 처리 속도 (10,000+ req/s)
    - 메모리 효율성 (10-50MB/프로세스)
  
  배포:
    - 단일 바이너리 배포 (의존성 없음)
    - 컨테이너 이미지 크기 (10-50MB)
    - 즉시 시작 (< 1초)
  
  생산성:
    - 강력한 타입 시스템 (컴파일 타임 에러 감지)
    - 명시적 에러 처리 (런타임 예외 최소화)
    - 코드 가독성 (표준 포맷팅)
```

### 1.2 Go 생태계의 현실: Django 같은 프레임워크는 없다

Django 개발자가 가장 먼저 묻는 질문:

> "Go에도 Django처럼 모든 게 다 있는 프레임워크가 있나요?"

**답: 없습니다. 그리고 그게 Go의 철학입니다.**

```python
# Django 방식 (Monolithic)
from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']

# 프레임워크가 모든 걸 제공:
# - ORM, Admin, Auth, Middleware, Template, Form...
```

```go
// Go 방식 (Composable)
type Post struct {
    ID       uint   `gorm:"primaryKey"`
    AuthorID uint
    Title    string
}

// 개발자가 직접 조립:
// - 웹 프레임워크: Gin / Echo / Fiber
// - ORM: GORM / Ent / sqlx
// - 인증: jwt-go / paseto
// - 검증: validator
```

**이게 불편해 보이지만, 실제로는 다음과 같은 장점이 있습니다:**

1. **필요한 것만 선택** - 작은 API 서버에 Django 전체를 올릴 필요 없음
2. **명확한 의존성** - 코드만 봐도 어떤 라이브러리를 쓰는지 명확
3. **유연한 교체** - ORM이 마음에 안 들면 다른 걸로 교체 가능

---

## 2. Go 프레임워크 생태계 - 무엇을 선택할까?

### 2.1 가장 사랑받는 웹 프레임워크 Top 3

Go에서는 "마이크로 프레임워크"가 대세입니다. Django보다는 Flask나 FastAPI와 비슷한 철학입니다.

```bash
# ============================================
# 1위: Gin (가장 인기 많음)
# ============================================
GitHub Stars: 77k+
특징: 
  ✅ 가장 빠른 성능
  ✅ 간결한 API
  ✅ 커뮤니티 최대
  ⚠️  문서화 부족 (중국어 문서 많음)

# Django 비교:
# - Django views.py → Gin router
# - Django middleware → Gin middleware
# - Django request → Gin context


# ============================================
# 2위: Echo (가장 완성도 높음)
# ============================================
GitHub Stars: 29k+
특징:
  ✅ 체계적인 구조
  ✅ 우수한 문서화
  ✅ 강력한 미들웨어
  ✅ 에러 처리 체계적

# Django 비교:
# - Django의 구조화된 접근 방식과 유사
# - 미들웨어, 그룹 라우팅 등 Django 개발자에게 친숙


# ============================================
# 3위: Fiber (가장 빠름)
# ============================================
GitHub Stars: 33k+
특징:
  ✅ Express.js 스타일 (Node 개발자에게 친숙)
  ✅ 최고 성능 (자체 엔진 사용)
  ⚠️  Go 표준 라이브러리 미사용 (생태계 호환성 문제)

# FastAPI와 가장 유사
```

### 2.2 ORM 선택 - Django ORM의 대안

Django의 강력한 ORM에 익숙하다면, Go에서도 ORM을 사용하는 것을 추천합니다.

```go
// ============================================
// 1. GORM - 가장 인기 있는 전통적인 ORM
// ============================================
// GitHub Stars: 36k+

// Django ORM 스타일과 가장 유사
type User struct {
    gorm.Model
    Name  string
    Email string `gorm:"uniqueIndex"`
}

// Django: User.objects.filter(email="test@example.com").first()
db.Where("email = ?", "test@example.com").First(&user)

// Django: User.objects.create(name="John", email="john@example.com")
db.Create(&User{Name: "John", Email: "john@example.com"})

장점:
  ✅ Django ORM과 비슷한 체인 메서드
  ✅ 자동 마이그레이션 (AutoMigrate)
  ✅ 관계(Relation) 쉽게 정의
  ✅ 소프트 삭제 기본 지원

단점:
  ⚠️  타입 안정성 약함 (인터페이스{} 남발)
  ⚠️  복잡한 쿼리는 Raw SQL 필요


// ============================================
// 2. Ent - Facebook의 현대적인 ORM
// ============================================
// GitHub Stars: 15k+

// 그래프 기반 스키마 정의
type User struct {
    ent.Schema
}

func (User) Fields() []ent.Field {
    return []ent.Field{
        field.String("name"),
        field.String("email").Unique(),
    }
}

장점:
  ✅ 강력한 타입 안정성 (코드 생성)
  ✅ 그래프 순회 (복잡한 관계 쿼리)
  ✅ 마이그레이션 자동 생성
  ✅ Django의 select_related / prefetch_related와 유사한 Eager Loading

단점:
  ⚠️  학습 곡선 높음
  ⚠️  코드 생성 단계 필요 (ent generate)


// ============================================
// 3. sqlx - Raw SQL 친화적
// ============================================
// GitHub Stars: 16k+

// Django Raw SQL과 유사하지만 더 안전
type User struct {
    ID    int    `db:"id"`
    Name  string `db:"name"`
    Email string `db:"email"`
}

db.Select(&users, "SELECT * FROM users WHERE email = ?", email)

장점:
  ✅ SQL 완전 제어
  ✅ 성능 최적화 가능
  ✅ 학습 필요 없음 (SQL만 알면 됨)

단점:
  ⚠️  ORM의 편의성 없음
  ⚠️  마이그레이션 직접 관리
```

### 2.3 Django 개발자를 위한 추천 조합

```yaml
초급 (빠른 시작):
  프레임워크: Gin
  ORM: GORM
  이유: 가장 자료 많고, Django와 가장 유사한 경험

중급 (추천! ⭐):
  프레임워크: Echo
  ORM: GORM
  이유: 
    - Echo의 체계적 구조 (Django의 구조화 철학과 유사)
    - GORM의 편의성 (Django ORM 경험 활용)
    - 실무에서 가장 많이 사용하는 조합

고급 (깊이 파고들기):
  프레임워크: Echo
  ORM: Ent
  이유:
    - 타입 안정성 (프로덕션 안정성)
    - 복잡한 관계 쿼리 (대규모 프로젝트)
    - Go의 장점을 최대한 활용

성능 최우선:
  프레임워크: Fiber
  ORM: sqlx (또는 ORM 없이 Raw SQL)
  이유: 최고 성능, 하지만 생산성 trade-off
```

---

## 3. 실전 튜토리얼 - Echo + GORM으로 CRUD 서버 만들기

Django의 복잡한 파일 구조(`settings.py`, `urls.py`, `views.py`, `models.py`) 없이, **단 1개의 파일**(`main.go`)로 완전한 CRUD API를 만들어봅시다.

### 3.1 프로젝트 초기화

```bash
# ============================================
# 1. 프로젝트 폴더 생성
# ============================================
mkdir go-django-crud
cd go-django-crud

# ============================================
# 2. Go 모듈 초기화 (Django의 django-admin startproject와 유사)
# ============================================
go mod init go-django-crud

# ============================================
# 3. 의존성 설치 (Django의 pip install과 유사)
# ============================================
go get github.com/labstack/echo/v4
go get gorm.io/gorm
go get gorm.io/driver/sqlite

# 설치 완료!
# - echo: 웹 프레임워크 (Django의 urls + views)
# - gorm: ORM (Django의 models + ORM)
# - sqlite: 데이터베이스 드라이버 (별도 설치 불필요)
```

### 3.2 전체 코드 (main.go)

Django와 비교하며 주석을 달아두었습니다. 이 코드를 `main.go`에 저장하세요.

```go
package main

import (
	"net/http"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// ============================================
// 1. Model 정의 (Django의 models.py)
// ============================================

/*
Django:
    from django.db import models
    
    class User(models.Model):
        name = models.CharField(max_length=100)
        email = models.EmailField(unique=True)
        created_at = models.DateTimeField(auto_now_add=True)
*/

type User struct {
	gorm.Model        // ID, CreatedAt, UpdatedAt, DeletedAt 자동 포함
	Name       string `json:"name" gorm:"not null"`
	Email      string `json:"email" gorm:"uniqueIndex;not null"`
}

// 전역 DB 변수 (실무에서는 별도 패키지로 분리)
var db *gorm.DB

// ============================================
// 2. 메인 함수 - 서버 초기화 및 라우팅
// ============================================

func main() {
	// ------------------------------------------
	// 데이터베이스 연결 (Django의 settings.py -> DATABASES)
	// ------------------------------------------
	/*
	Django:
	    DATABASES = {
	        'default': {
	            'ENGINE': 'django.db.backends.sqlite3',
	            'NAME': BASE_DIR / 'db.sqlite3',
	        }
	    }
	*/
	
	var err error
	db, err = gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		panic("Failed to connect to database")
	}

	// ------------------------------------------
	// 마이그레이션 (Django의 makemigrations + migrate)
	// ------------------------------------------
	/*
	Django:
	    python manage.py makemigrations
	    python manage.py migrate
	    
	GORM:
	    서버 시작 시 자동으로 테이블 생성/갱신
	    User 구조체를 보고 DB 스키마 동기화
	*/
	
	db.AutoMigrate(&User{})

	// ------------------------------------------
	// Echo 인스턴스 생성 및 미들웨어 설정
	// ------------------------------------------
	/*
	Django:
	    MIDDLEWARE = [
	        'django.middleware.common.CommonMiddleware',
	        'django.middleware.csrf.CsrfViewMiddleware',
	        ...
	    ]
	*/
	
	e := echo.New()

	// 미들웨어 등록
	e.Use(middleware.Logger())  // 로그 출력
	e.Use(middleware.Recover()) // Panic 복구 (Django의 디버그 페이지와 유사)
	e.Use(middleware.CORS())    // CORS 허용

	// ------------------------------------------
	// URL 라우팅 (Django의 urls.py)
	// ------------------------------------------
	/*
	Django urls.py:
	    urlpatterns = [
	        path('users/', views.create_user, name='create_user'),
	        path('users/', views.get_users, name='get_users'),
	        path('users/<int:pk>/', views.get_user, name='get_user'),
	        path('users/<int:pk>/update/', views.update_user),
	        path('users/<int:pk>/delete/', views.delete_user),
	    ]
	*/
	
	// RESTful API 라우팅
	e.POST("/users", createUser)         // Create
	e.GET("/users", getUsers)            // Read List
	e.GET("/users/:id", getUser)         // Read Detail
	e.PUT("/users/:id", updateUser)      // Update
	e.DELETE("/users/:id", deleteUser)   // Delete

	// ------------------------------------------
	// 서버 시작 (Django의 runserver)
	// ------------------------------------------
	/*
	Django:
	    python manage.py runserver 0.0.0.0:8000
	*/
	
	e.Logger.Fatal(e.Start(":8000"))
}

// ============================================
// 3. 핸들러 함수들 (Django의 views.py)
// ============================================

// ------------------------------------------
// Create - 사용자 생성 (POST /users)
// ------------------------------------------
/*
Django views.py:
    from django.views.decorators.http import require_http_methods
    from django.http import JsonResponse
    import json
    
    @require_http_methods(["POST"])
    def create_user(request):
        data = json.loads(request.body)
        user = User.objects.create(
            name=data['name'],
            email=data['email']
        )
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email
        }, status=201)
*/

func createUser(c echo.Context) error {
	// 요청 바디를 User 구조체로 바인딩
	u := new(User)
	if err := c.Bind(u); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request body",
		})
	}

	// 유효성 검증 (Django의 form.is_valid())
	if u.Name == "" || u.Email == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Name and email are required",
		})
	}

	// DB에 저장 (Django의 user.save())
	result := db.Create(u)
	if result.Error != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": result.Error.Error(),
		})
	}

	return c.JSON(http.StatusCreated, u)
}

// ------------------------------------------
// Read List - 사용자 목록 조회 (GET /users)
// ------------------------------------------
/*
Django views.py:
    def get_users(request):
        users = User.objects.all()
        data = [{'id': u.id, 'name': u.name, 'email': u.email} for u in users]
        return JsonResponse(data, safe=False)
*/

func getUsers(c echo.Context) error {
	var users []User

	// User.objects.all() 과 동일
	db.Find(&users)

	return c.JSON(http.StatusOK, users)
}

// ------------------------------------------
// Read Detail - 특정 사용자 조회 (GET /users/:id)
// ------------------------------------------
/*
Django views.py:
    from django.shortcuts import get_object_or_404
    
    def get_user(request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email
        })
*/

func getUser(c echo.Context) error {
	id := c.Param("id") // URL 파라미터 추출
	var user User

	// User.objects.get(id=id) 와 동일
	if result := db.First(&user, id); result.Error != nil {
		return c.JSON(http.StatusNotFound, map[string]string{
			"error": "User not found",
		})
	}

	return c.JSON(http.StatusOK, user)
}

// ------------------------------------------
// Update - 사용자 수정 (PUT /users/:id)
// ------------------------------------------
/*
Django views.py:
    def update_user(request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(request.body)
        
        user.name = data.get('name', user.name)
        user.email = data.get('email', user.email)
        user.save()
        
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email
        })
*/

func updateUser(c echo.Context) error {
	id := c.Param("id")
	var user User

	// 먼저 기존 사용자 조회
	if result := db.First(&user, id); result.Error != nil {
		return c.JSON(http.StatusNotFound, map[string]string{
			"error": "User not found",
		})
	}

	// 요청 데이터 바인딩
	u := new(User)
	if err := c.Bind(u); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request body",
		})
	}

	// 필드 업데이트
	if u.Name != "" {
		user.Name = u.Name
	}
	if u.Email != "" {
		user.Email = u.Email
	}

	// User.objects.filter(id=id).update(...) 와 유사
	db.Save(&user)

	return c.JSON(http.StatusOK, user)
}

// ------------------------------------------
// Delete - 사용자 삭제 (DELETE /users/:id)
// ------------------------------------------
/*
Django views.py:
    def delete_user(request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return JsonResponse({'message': 'User deleted'}, status=204)
*/

func deleteUser(c echo.Context) error {
	id := c.Param("id")

	// User.objects.filter(id=id).delete()
	// GORM은 기본적으로 Soft Delete (DeletedAt 필드만 업데이트)
	result := db.Delete(&User{}, id)
	
	if result.RowsAffected == 0 {
		return c.JSON(http.StatusNotFound, map[string]string{
			"error": "User not found",
		})
	}

	return c.NoContent(http.StatusNoContent)
}
```

### 3.3 실행 및 테스트

```bash
# ============================================
# 1. 서버 실행 (Django의 python manage.py runserver)
# ============================================
go run main.go

# 출력:
#    ____    __
#   / __/___/ /  ___
#  / _// __/ _ \/ _ \
# /___/\__/_//_/\___/ v4.11.3
# High performance, minimalist Go web framework
# https://echo.labstack.com
# ____________________________________O/_______
#                                     O\
# ⇨ http server started on [::]:8000


# ============================================
# 2. API 테스트 (Django shell_plus와 유사)
# ============================================

# POST - 사용자 생성
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Django Developer",
    "email": "django@example.com"
  }'

# 응답:
# {
#   "ID": 1,
#   "CreatedAt": "2025-12-06T09:00:00.123Z",
#   "UpdatedAt": "2025-12-06T09:00:00.123Z",
#   "DeletedAt": null,
#   "name": "Django Developer",
#   "email": "django@example.com"
# }


# GET - 전체 사용자 조회
curl http://localhost:8000/users

# 응답:
# [
#   {
#     "ID": 1,
#     "CreatedAt": "2025-12-06T09:00:00.123Z",
#     "UpdatedAt": "2025-12-06T09:00:00.123Z",
#     "DeletedAt": null,
#     "name": "Django Developer",
#     "email": "django@example.com"
#   }
# ]


# GET - 특정 사용자 조회
curl http://localhost:8000/users/1

# 응답:
# {
#   "ID": 1,
#   "CreatedAt": "2025-12-06T09:00:00.123Z",
#   "UpdatedAt": "2025-12-06T09:00:00.123Z",
#   "DeletedAt": null,
#   "name": "Django Developer",
#   "email": "django@example.com"
# }


# PUT - 사용자 수정
curl -X PUT http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Go Developer",
    "email": "go@example.com"
  }'

# 응답:
# {
#   "ID": 1,
#   "CreatedAt": "2025-12-06T09:00:00.123Z",
#   "UpdatedAt": "2025-12-06T09:05:00.456Z",
#   "DeletedAt": null,
#   "name": "Go Developer",
#   "email": "go@example.com"
# }


# DELETE - 사용자 삭제
curl -X DELETE http://localhost:8000/users/1

# 응답: (204 No Content)


# ============================================
# 3. 데이터베이스 확인
# ============================================

# SQLite DB 파일이 생성됨
ls -lh test.db
# -rw-r--r--  1 user  staff   20K Dec  6 09:00 test.db

# DB 내용 확인 (Django의 python manage.py dbshell)
sqlite3 test.db

sqlite> .tables
users

sqlite> .schema users
CREATE TABLE `users` (
  `id` integer,
  `created_at` datetime,
  `updated_at` datetime,
  `deleted_at` datetime,
  `name` text NOT NULL,
  `email` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE (`email`)
);

sqlite> SELECT * FROM users;
# 1|2025-12-06 09:00:00|2025-12-06 09:05:00||Go Developer|go@example.com

sqlite> .quit
```

---

## 4. Django vs Go - 주요 차이점 심층 분석

### 4.1 프로젝트 구조 비교

```bash
# ============================================
# Django 프로젝트 구조
# ============================================
myproject/
├── manage.py              # 관리 명령어
├── myproject/
│   ├── __init__.py
│   ├── settings.py        # 설정 (200+ 줄)
│   ├── urls.py            # URL 라우팅
│   ├── wsgi.py            # WSGI 설정
│   └── asgi.py            # ASGI 설정
├── users/
│   ├── __init__.py
│   ├── models.py          # 모델 정의
│   ├── views.py           # 비즈니스 로직
│   ├── serializers.py     # DRF 사용 시
│   ├── urls.py            # 앱별 URL
│   ├── admin.py           # Admin 설정
│   ├── tests.py           # 테스트
│   └── migrations/        # 마이그레이션 파일들
│       ├── 0001_initial.py
│       └── ...
├── requirements.txt       # 의존성 (50+ 패키지)
└── db.sqlite3            # 데이터베이스

총 파일 수: 20+ 파일
의존성: Django + 수십 개 패키지
시작 시간: 5-10초


# ============================================
# Go 프로젝트 구조 (초기)
# ============================================
go-project/
├── main.go               # 모든 코드 (100-200줄)
├── go.mod                # 의존성 (5줄)
├── go.sum                # 체크섬
└── test.db              # 데이터베이스

총 파일 수: 3 파일
의존성: Echo + GORM (2개)
시작 시간: < 1초
빌드 결과: 단일 바이너리 (10MB)


# ============================================
# Go 프로젝트 구조 (확장 후)
# ============================================
go-project/
├── main.go               # 진입점
├── config/
│   └── database.go       # DB 설정
├── models/
│   └── user.go           # 모델
├── handlers/
│   └── user.go           # 핸들러 (Django의 views)
├── services/
│   └── user.go           # 비즈니스 로직
├── repositories/
│   └── user.go           # DB 접근 계층
├── middleware/
│   └── auth.go           # 미들웨어
├── go.mod
└── go.sum

총 파일 수: 10 파일 (여전히 간결)
```

### 4.2 ORM 비교 - Django vs GORM

```python
# ============================================
# Django ORM
# ============================================

# 1. 모델 정의
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()


# 2. CRUD 작업
# Create
user = User.objects.create(name="John", email="john@example.com")

# Read
users = User.objects.all()
user = User.objects.get(id=1)
users = User.objects.filter(name__icontains="john")

# Update
User.objects.filter(id=1).update(name="Jane")
# 또는
user = User.objects.get(id=1)
user.name = "Jane"
user.save()

# Delete
User.objects.filter(id=1).delete()
# 또는
user = User.objects.get(id=1)
user.delete()


# 3. 관계 쿼리
# N+1 문제 방지
posts = Post.objects.select_related('author').all()

# Many-to-Many
users = User.objects.prefetch_related('posts').all()


# 4. 집계 (Aggregation)
from django.db.models import Count, Avg

User.objects.aggregate(total=Count('id'))
User.objects.annotate(post_count=Count('posts'))
```

```go
// ============================================
// GORM
// ============================================

// 1. 모델 정의
type User struct {
    gorm.Model               // ID, CreatedAt, UpdatedAt, DeletedAt
    Name       string        `gorm:"size:100;not null"`
    Email      string        `gorm:"uniqueIndex;not null"`
}

type Post struct {
    gorm.Model
    AuthorID   uint
    Author     User          `gorm:"foreignKey:AuthorID"`
    Title      string        `gorm:"size:200;not null"`
    Content    string        `gorm:"type:text"`
}

// TableName 커스터마이징
func (User) TableName() string {
    return "users"
}


// 2. CRUD 작업
// Create
user := User{Name: "John", Email: "john@example.com"}
db.Create(&user)

// Read
var users []User
db.Find(&users)

var user User
db.First(&user, 1)

db.Where("name LIKE ?", "%john%").Find(&users)

// Update
db.Model(&User{}).Where("id = ?", 1).Update("name", "Jane")
// 또는
db.First(&user, 1)
user.Name = "Jane"
db.Save(&user)

// Delete (Soft Delete)
db.Delete(&User{}, 1)
// 완전 삭제
db.Unscoped().Delete(&User{}, 1)


// 3. 관계 쿼리 (N+1 문제 방지)
// Eager Loading (Django의 select_related)
var posts []Post
db.Preload("Author").Find(&posts)

// 여러 관계
db.Preload("Author").Preload("Comments").Find(&posts)


// 4. 집계 (Aggregation)
var count int64
db.Model(&User{}).Count(&count)

type Result struct {
    Name      string
    PostCount int64
}
var results []Result
db.Model(&User{}).
    Select("users.name, COUNT(posts.id) as post_count").
    Joins("LEFT JOIN posts ON posts.author_id = users.id").
    Group("users.id").
    Scan(&results)
```

### 4.3 미들웨어 비교

```python
# ============================================
# Django 미들웨어
# ============================================

# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 커스텀 미들웨어
class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 요청 전 처리
        print(f"Request: {request.method} {request.path}")
        
        response = self.get_response(request)
        
        # 응답 후 처리
        print(f"Response: {response.status_code}")
        return response
```

```go
// ============================================
// Echo 미들웨어
// ============================================

package main

import (
    "fmt"
    "time"
    
    "github.com/labstack/echo/v4"
    "github.com/labstack/echo/v4/middleware"
)

func main() {
    e := echo.New()
    
    // 내장 미들웨어
    e.Use(middleware.Logger())
    e.Use(middleware.Recover())
    e.Use(middleware.CORS())
    e.Use(middleware.Gzip())
    e.Use(middleware.Secure())
    
    // JWT 인증
    e.Use(middleware.JWTWithConfig(middleware.JWTConfig{
        SigningKey: []byte("secret"),
        Skipper: func(c echo.Context) bool {
            // /login 경로는 인증 스킵
            return c.Path() == "/login"
        },
    }))
    
    // 커스텀 미들웨어
    e.Use(loggingMiddleware)
    
    e.Start(":8000")
}

// 커스텀 미들웨어 함수
func loggingMiddleware(next echo.HandlerFunc) echo.HandlerFunc {
    return func(c echo.Context) error {
        // 요청 전 처리
        start := time.Now()
        fmt.Printf("Request: %s %s\n", c.Request().Method, c.Path())
        
        // 다음 핸들러 실행
        err := next(c)
        
        // 응답 후 처리
        fmt.Printf("Response: %d (took %v)\n", 
            c.Response().Status, 
            time.Since(start),
        )
        
        return err
    }
}
```

### 4.4 에러 처리 비교

```python
# ============================================
# Django 에러 처리
# ============================================

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def get_user(request, pk):
    # 암묵적 에러 처리 (404 자동 발생)
    user = get_object_or_404(User, pk=pk)
    
    return JsonResponse({
        'id': user.id,
        'name': user.name,
    })

# 커스텀 예외
from django.core.exceptions import ValidationError

def create_user(request):
    try:
        data = json.loads(request.body)
        
        if not data.get('email'):
            raise ValidationError("Email is required")
        
        user = User.objects.create(**data)
        return JsonResponse({'id': user.id}, status=201)
        
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Internal error'}, status=500)
```

```go
// ============================================
// Go 에러 처리 (명시적)
// ============================================

package main

import (
    "errors"
    "net/http"
    
    "github.com/labstack/echo/v4"
    "gorm.io/gorm"
)

func getUser(c echo.Context) error {
    id := c.Param("id")
    var user User
    
    // 명시적 에러 처리 (Go의 철학)
    result := db.First(&user, id)
    if result.Error != nil {
        if errors.Is(result.Error, gorm.ErrRecordNotFound) {
            return c.JSON(http.StatusNotFound, map[string]string{
                "error": "User not found",
            })
        }
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": result.Error.Error(),
        })
    }
    
    return c.JSON(http.StatusOK, user)
}

func createUser(c echo.Context) error {
    u := new(User)
    
    // 바인딩 에러
    if err := c.Bind(u); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": "Invalid request format",
        })
    }
    
    // 유효성 검증
    if u.Email == "" {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": "Email is required",
        })
    }
    
    // DB 에러
    if err := db.Create(u).Error; err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": err.Error(),
        })
    }
    
    return c.JSON(http.StatusCreated, u)
}

// 커스텀 에러 핸들러 (전역)
func customErrorHandler(err error, c echo.Context) {
    code := http.StatusInternalServerError
    message := "Internal server error"
    
    if he, ok := err.(*echo.HTTPError); ok {
        code = he.Code
        message = he.Message.(string)
    }
    
    c.JSON(code, map[string]interface{}{
        "error": message,
        "path": c.Path(),
    })
}

// main에서 등록
e := echo.New()
e.HTTPErrorHandler = customErrorHandler
```

### 4.5 마이그레이션 비교

```bash
# ============================================
# Django 마이그레이션 (명시적, 버전 관리)
# ============================================

# 1. 모델 변경
# models.py
class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.IntegerField(null=True)  # 새 필드 추가

# 2. 마이그레이션 파일 생성
python manage.py makemigrations
# Migrations for 'users':
#   users/migrations/0002_user_age.py
#     - Add field age to user

# 3. 마이그레이션 적용
python manage.py migrate
# Running migrations:
#   Applying users.0002_user_age... OK

# 4. 롤백 가능
python manage.py migrate users 0001

# 5. SQL 확인
python manage.py sqlmigrate users 0002


장점:
  ✅ 버전 관리 (Git 추적 가능)
  ✅ 롤백 가능
  ✅ 팀 협업 용이
  ✅ 프로덕션 안전성

단점:
  ⚠️  마이그레이션 충돌
  ⚠️  수동 개입 필요한 경우 많음
```

```go
// ============================================
// GORM AutoMigrate (자동, 간편)
// ============================================

// 1. 모델 변경
type User struct {
    gorm.Model
    Name  string
    Email string
    Age   *int  // 새 필드 추가 (포인터로 nullable)
}

// 2. 서버 시작 시 자동 마이그레이션
func main() {
    db, _ := gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
    
    // 자동으로 테이블 생성/수정
    db.AutoMigrate(&User{})
    
    // 서버 시작...
}

// 끝! 별도 명령어 불필요


장점:
  ✅ 간편함 (코드만 수정하면 자동)
  ✅ 개발 속도 빠름
  ✅ 실수 적음

단점:
  ⚠️  롤백 불가
  ⚠️  버전 관리 안됨
  ⚠️  복잡한 마이그레이션 불가 (컬럼 이름 변경 등)
  ⚠️  프로덕션에서는 위험


// ============================================
// 프로덕션용: golang-migrate 사용 (Django 스타일)
// ============================================

// 별도 마이그레이션 도구 사용
go install -tags 'sqlite3' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# 마이그레이션 파일 생성
migrate create -ext sql -dir migrations -seq add_age_to_users

# migrations/000001_add_age_to_users.up.sql
ALTER TABLE users ADD COLUMN age INTEGER;

# migrations/000001_add_age_to_users.down.sql
ALTER TABLE users DROP COLUMN age;

# 마이그레이션 적용
migrate -path migrations -database "sqlite3://test.db" up

# 롤백
migrate -path migrations -database "sqlite3://test.db" down 1
```

---

## 5. 프로젝트 구조화 - Django 개발자를 위한 Clean Architecture

단일 파일(`main.go`)로 시작했지만, 프로젝트가 커지면 Django처럼 파일을 분리해야 합니다.

### 5.1 Django의 App 구조 vs Go의 Package 구조

```bash
# ============================================
# Django 방식 (App 기반)
# ============================================
myproject/
├── users/          # App 단위
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
├── posts/          # 또 다른 App
│   ├── models.py
│   ├── views.py
│   └── ...
└── manage.py

특징:
  - 기능별 App 분리 (users, posts, comments 등)
  - 각 App은 독립적 (재사용 가능)
  - models, views, tests 등 역할별 파일 분리


# ============================================
# Go 방식 (Layer 기반 - Clean Architecture)
# ============================================
go-project/
├── main.go                    # 진입점
├── models/                    # Domain Layer (Django의 models.py)
│   ├── user.go
│   └── post.go
├── handlers/                  # Presentation Layer (Django의 views.py)
│   ├── user_handler.go
│   └── post_handler.go
├── services/                  # Business Logic Layer
│   ├── user_service.go
│   └── post_service.go
├── repositories/              # Data Access Layer (Django의 ORM 쿼리)
│   ├── user_repository.go
│   └── post_repository.go
├── config/                    # Configuration
│   └── database.go
└── middleware/
    └── auth.go

특징:
  - 계층별 분리 (Handler → Service → Repository)
  - 의존성 방향: Handler → Service → Repository → Model
  - 테스트 용이 (각 계층 독립적)
```

### 5.2 실전 구조화 예시

이제 단일 파일(`main.go`)을 계층별로 분리해봅시다.

```go
// ============================================
// models/user.go - Domain Layer
// ============================================
package models

import "gorm.io/gorm"

type User struct {
	gorm.Model
	Name  string `json:"name" gorm:"not null"`
	Email string `json:"email" gorm:"uniqueIndex;not null"`
}


// ============================================
// repositories/user_repository.go - Data Access Layer
// ============================================
package repositories

import (
	"go-project/models"
	"gorm.io/gorm"
)

type UserRepository interface {
	Create(user *models.User) error
	FindAll() ([]models.User, error)
	FindByID(id uint) (*models.User, error)
	Update(user *models.User) error
	Delete(id uint) error
}

type userRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) UserRepository {
	return &userRepository{db: db}
}

func (r *userRepository) Create(user *models.User) error {
	return r.db.Create(user).Error
}

func (r *userRepository) FindAll() ([]models.User, error) {
	var users []models.User
	err := r.db.Find(&users).Error
	return users, err
}

func (r *userRepository) FindByID(id uint) (*models.User, error) {
	var user models.User
	err := r.db.First(&user, id).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *userRepository) Update(user *models.User) error {
	return r.db.Save(user).Error
}

func (r *userRepository) Delete(id uint) error {
	return r.db.Delete(&models.User{}, id).Error
}


// ============================================
// services/user_service.go - Business Logic Layer
// ============================================
package services

import (
	"errors"
	"go-project/models"
	"go-project/repositories"
)

type UserService interface {
	CreateUser(name, email string) (*models.User, error)
	GetAllUsers() ([]models.User, error)
	GetUserByID(id uint) (*models.User, error)
	UpdateUser(id uint, name, email string) (*models.User, error)
	DeleteUser(id uint) error
}

type userService struct {
	repo repositories.UserRepository
}

func NewUserService(repo repositories.UserRepository) UserService {
	return &userService{repo: repo}
}

func (s *userService) CreateUser(name, email string) (*models.User, error) {
	// 유효성 검증
	if name == "" || email == "" {
		return nil, errors.New("name and email are required")
	}

	user := &models.User{
		Name:  name,
		Email: email,
	}

	if err := s.repo.Create(user); err != nil {
		return nil, err
	}

	return user, nil
}

func (s *userService) GetAllUsers() ([]models.User, error) {
	return s.repo.FindAll()
}

func (s *userService) GetUserByID(id uint) (*models.User, error) {
	return s.repo.FindByID(id)
}

func (s *userService) UpdateUser(id uint, name, email string) (*models.User, error) {
	user, err := s.repo.FindByID(id)
	if err != nil {
		return nil, err
	}

	if name != "" {
		user.Name = name
	}
	if email != "" {
		user.Email = email
	}

	if err := s.repo.Update(user); err != nil {
		return nil, err
	}

	return user, nil
}

func (s *userService) DeleteUser(id uint) error {
	return s.repo.Delete(id)
}


// ============================================
// handlers/user_handler.go - Presentation Layer
// ============================================
package handlers

import (
	"net/http"
	"strconv"

	"go-project/services"
	"github.com/labstack/echo/v4"
)

type UserHandler struct {
	service services.UserService
}

func NewUserHandler(service services.UserService) *UserHandler {
	return &UserHandler{service: service}
}

type CreateUserRequest struct {
	Name  string `json:"name"`
	Email string `json:"email"`
}

func (h *UserHandler) Create(c echo.Context) error {
	req := new(CreateUserRequest)
	if err := c.Bind(req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request",
		})
	}

	user, err := h.service.CreateUser(req.Name, req.Email)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": err.Error(),
		})
	}

	return c.JSON(http.StatusCreated, user)
}

func (h *UserHandler) GetAll(c echo.Context) error {
	users, err := h.service.GetAllUsers()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": err.Error(),
		})
	}

	return c.JSON(http.StatusOK, users)
}

func (h *UserHandler) GetByID(c echo.Context) error {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 32)

	user, err := h.service.GetUserByID(uint(id))
	if err != nil {
		return c.JSON(http.StatusNotFound, map[string]string{
			"error": "User not found",
		})
	}

	return c.JSON(http.StatusOK, user)
}

func (h *UserHandler) Update(c echo.Context) error {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 32)

	req := new(CreateUserRequest)
	if err := c.Bind(req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request",
		})
	}

	user, err := h.service.UpdateUser(uint(id), req.Name, req.Email)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": err.Error(),
		})
	}

	return c.JSON(http.StatusOK, user)
}

func (h *UserHandler) Delete(c echo.Context) error {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 32)

	if err := h.service.DeleteUser(uint(id)); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": err.Error(),
		})
	}

	return c.NoContent(http.StatusNoContent)
}


// ============================================
// config/database.go - Configuration
// ============================================
package config

import (
	"go-project/models"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func InitDB() (*gorm.DB, error) {
	db, err := gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	// Auto Migration
	db.AutoMigrate(&models.User{})

	return db, nil
}


// ============================================
// main.go - Entry Point (의존성 주입)
// ============================================
package main

import (
	"log"

	"go-project/config"
	"go-project/handlers"
	"go-project/repositories"
	"go-project/services"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	// DB 초기화
	db, err := config.InitDB()
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// 의존성 주입 (Dependency Injection)
	userRepo := repositories.NewUserRepository(db)
	userService := services.NewUserService(userRepo)
	userHandler := handlers.NewUserHandler(userService)

	// Echo 설정
	e := echo.New()
	e.Use(middleware.Logger())
	e.Use(middleware.Recover())
	e.Use(middleware.CORS())

	// 라우팅
	api := e.Group("/api")
	{
		users := api.Group("/users")
		users.POST("", userHandler.Create)
		users.GET("", userHandler.GetAll)
		users.GET("/:id", userHandler.GetByID)
		users.PUT("/:id", userHandler.Update)
		users.DELETE("/:id", userHandler.Delete)
	}

	// 서버 시작
	e.Logger.Fatal(e.Start(":8000"))
}
```

**이 구조의 장점 (Django 개발자 관점):**

```yaml
테스트 용이성:
  Django:
    - views.py 테스트 시 전체 프레임워크 로드 필요
    - DB 의존성 (TestCase 사용)
  
  Go:
    - 각 계층 독립적 테스트 (Mock 활용)
    - Service만 테스트 (DB 없이)

의존성 관리:
  Django:
    - settings.py에서 전역 설정
    - Circular import 문제 자주 발생
  
  Go:
    - 명시적 의존성 주입
    - 컴파일 타임에 순환 의존성 감지

비즈니스 로직 분리:
  Django:
    - views.py에 로직 섞임 (fat views 문제)
    - 재사용 어려움
  
  Go:
    - Service 계층에 로직 집중
    - HTTP와 무관하게 재사용 가능
```

---

## 6. 인증 (Authentication) - Django vs Go

### 6.1 Django의 세션 기반 인증

```python
# ============================================
# Django 방식 (Session + Cookie)
# ============================================

# settings.py
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.sessions',
    ...
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    ...
]

# views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def login_view(request):
    username = request.POST['username']
    password = request.POST['password']
    
    user = authenticate(username=username, password=password)
    if user is not None:
        login(request, user)  # 세션 생성
        return JsonResponse({'message': 'Login success'})
    
    return JsonResponse({'error': 'Invalid credentials'}, status=401)

@login_required  # 데코레이터로 인증 확인
def protected_view(request):
    return JsonResponse({'user': request.user.username})

def logout_view(request):
    logout(request)  # 세션 삭제
    return JsonResponse({'message': 'Logout success'})
```

### 6.2 Go의 JWT 기반 인증 (Stateless)

```go
// ============================================
// Go + JWT 방식 (Stateless)
// ============================================

package main

import (
	"net/http"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"golang.org/x/crypto/bcrypt"
)

// JWT Secret Key
var jwtSecret = []byte("your-secret-key")

// JWT Claims 구조체
type JWTClaims struct {
	UserID uint   `json:"user_id"`
	Email  string `json:"email"`
	jwt.RegisteredClaims
}

// 로그인 요청
type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// 회원가입
func signup(c echo.Context) error {
	req := new(LoginRequest)
	if err := c.Bind(req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request",
		})
	}

	// 비밀번호 해싱 (Django의 make_password)
	hashedPassword, err := bcrypt.GenerateFromPassword(
		[]byte(req.Password),
		bcrypt.DefaultCost,
	)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "Failed to hash password",
		})
	}

	// 사용자 생성 (실제로는 Service 계층 사용)
	user := &User{
		Email:    req.Email,
		Password: string(hashedPassword),
	}
	db.Create(user)

	return c.JSON(http.StatusCreated, map[string]interface{}{
		"id":    user.ID,
		"email": user.Email,
	})
}

// 로그인 (JWT 토큰 발급)
func login(c echo.Context) error {
	req := new(LoginRequest)
	if err := c.Bind(req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{
			"error": "Invalid request",
		})
	}

	// 사용자 조회
	var user User
	if err := db.Where("email = ?", req.Email).First(&user).Error; err != nil {
		return c.JSON(http.StatusUnauthorized, map[string]string{
			"error": "Invalid credentials",
		})
	}

	// 비밀번호 검증 (Django의 check_password)
	if err := bcrypt.CompareHashAndPassword(
		[]byte(user.Password),
		[]byte(req.Password),
	); err != nil {
		return c.JSON(http.StatusUnauthorized, map[string]string{
			"error": "Invalid credentials",
		})
	}

	// JWT 토큰 생성
	claims := &JWTClaims{
		UserID: user.ID,
		Email:  user.Email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(jwtSecret)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "Failed to generate token",
		})
	}

	return c.JSON(http.StatusOK, map[string]string{
		"token": tokenString,
	})
}

// 보호된 엔드포인트 (Django의 @login_required)
func protectedHandler(c echo.Context) error {
	// JWT 미들웨어가 검증한 사용자 정보
	user := c.Get("user").(*jwt.Token)
	claims := user.Claims.(*JWTClaims)

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message": "Protected resource",
		"user_id": claims.UserID,
		"email":   claims.Email,
	})
}

// main에서 JWT 미들웨어 설정
func main() {
	e := echo.New()

	// 공개 라우트
	e.POST("/signup", signup)
	e.POST("/login", login)

	// 보호된 라우트 (JWT 필수)
	protected := e.Group("/api")
	protected.Use(middleware.JWTWithConfig(middleware.JWTConfig{
		SigningKey:  jwtSecret,
		TokenLookup: "header:Authorization",
		AuthScheme:  "Bearer",
		Claims:      &JWTClaims{},
	}))

	protected.GET("/profile", protectedHandler)
	protected.GET("/users", getUsers)

	e.Start(":8000")
}
```

**클라이언트에서 사용:**

```bash
# 1. 회원가입
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'

# 2. 로그인 (토큰 받기)
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'

# 응답:
# {"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}

# 3. 보호된 리소스 접근 (토큰 사용)
curl http://localhost:8000/api/profile \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 응답:
# {"message":"Protected resource","user_id":1,"email":"user@example.com"}
```

---

## 7. 배포 - Django vs Go의 압도적 차이

### 7.1 Django 배포 (복잡)

```bash
# ============================================
# Django 배포 과정
# ============================================

# 1. 의존성 파일 생성
pip freeze > requirements.txt
# Django==4.2.0
# djangorestframework==3.14.0
# psycopg2-binary==2.9.9
# gunicorn==21.2.0
# ... (50+ 패키지)

# 2. Dockerfile 작성
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]

# 이미지 크기: 500MB ~ 1GB

# 3. 빌드 및 실행
docker build -t my-django-app .
docker run -p 8000:8000 my-django-app

# 시작 시간: 5-10초
# 메모리: 150-250MB


# ============================================
# 프로덕션 배포 (더 복잡)
# ============================================

# Nginx + Gunicorn 조합 필요
# Static 파일 서빙 (collectstatic)
# 환경변수 관리
# DB 마이그레이션 별도 실행

# docker-compose.yml
services:
  web:
    build: .
    command: gunicorn myproject.wsgi:application
    volumes:
      - static_volume:/app/staticfiles
    depends_on:
      - db
  
  nginx:
    image: nginx
    volumes:
      - static_volume:/staticfiles
    ports:
      - "80:80"
  
  db:
    image: postgres:15
```

### 7.2 Go 배포 (단순함의 극치)

```bash
# ============================================
# Go 배포 과정
# ============================================

# 1. 의존성? go.mod에 자동 관리됨 (파일 10줄)

# 2. Dockerfile 작성 (Multi-stage Build)
# Stage 1: 빌드
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server .

# Stage 2: 실행 (최소 이미지)
FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/server .
EXPOSE 8000
CMD ["./server"]

# 최종 이미지 크기: 10-15MB (Django의 1/50!)


# 3. 빌드 및 실행
docker build -t my-go-app .
docker run -p 8000:8000 my-go-app

# 시작 시간: < 1초
# 메모리: 10-30MB (Django의 1/10!)


# ============================================
# 더 간단한 배포: 바이너리만 복사
# ============================================

# 로컬에서 빌드
GOOS=linux GOARCH=amd64 go build -o server

# 서버에 업로드
scp server user@server:/app/

# 실행
ssh user@server
cd /app
./server

# 끝! 의존성 설치, 런타임 설치 필요 없음!
```

**배포 비교 요약:**

```yaml
Django:
  이미지 크기: 500MB - 1GB
  시작 시간: 5-10초
  메모리 사용: 150-250MB
  배포 복잡도: ★★★★☆
  의존성 관리: requirements.txt (50+ 패키지)
  
Go:
  이미지 크기: 10-15MB (50배 작음!)
  시작 시간: < 1초 (10배 빠름!)
  메모리 사용: 10-30MB (8배 적음!)
  배포 복잡도: ★☆☆☆☆
  의존성 관리: go.mod (자동)
  
추가 장점 (Go):
  ✅ 단일 바이너리 (컨테이너 불필요)
  ✅ Cross-compile (Mac에서 Linux 빌드 가능)
  ✅ 즉시 시작 (Cold start 없음)
  ✅ 수평 확장 용이 (Stateless)
```

---

## 8. Django 개발자를 위한 Go 학습 로드맵

### 8.1 4주 학습 계획

```yaml
Week 1 - Go 기초:
  Day 1-2: 문법 기초
    - 변수, 함수, 구조체
    - 포인터 (Python에 없는 개념)
    - 슬라이스, 맵
  
  Day 3-4: 동시성 (Goroutine)
    - goroutine vs Thread
    - channel (Django Celery와 비교)
  
  Day 5-7: 실습
    - CLI 도구 만들기
    - 파일 읽기/쓰기
    - JSON 파싱

Week 2 - 웹 프레임워크:
  Day 1-3: Echo 프레임워크
    - 라우팅, 미들웨어
    - 요청/응답 처리
    - 에러 핸들링
  
  Day 4-5: GORM
    - 모델 정의
    - CRUD 작업
    - 관계 (Foreign Key, Many-to-Many)
  
  Day 6-7: 실습
    - TODO API 만들기 (Django와 비교)

Week 3 - 고급 기능:
  Day 1-2: 인증/인가
    - JWT 구현
    - Middleware 인증
  
  Day 3-4: 프로젝트 구조화
    - Clean Architecture
    - 의존성 주입
  
  Day 5-7: 실습
    - 블로그 API (Django 프로젝트를 Go로 재구현)

Week 4 - 배포 및 최적화:
  Day 1-2: 테스트
    - Unit Test
    - Integration Test
    - Mock 활용
  
  Day 3-4: Docker 배포
    - Multi-stage Build
    - 컨테이너 최적화
  
  Day 5-7: 실전 프로젝트
    - 마이크로서비스 API
    - Kubernetes 배포 (선택)
```

### 8.2 추천 학습 자료

```bash
# ============================================
# 공식 문서
# ============================================
https://go.dev/tour/           # 인터랙티브 튜토리얼
https://gobyexample.com/       # 예제 중심 학습


# ============================================
# 웹 프레임워크
# ============================================
https://echo.labstack.com/     # Echo 공식 문서
https://gorm.io/               # GORM 공식 문서


# ============================================
# 프로젝트 구조
# ============================================
https://github.com/golang-standards/project-layout
# Go 프로젝트 표준 구조


# ============================================
# 실전 예제
# ============================================
https://github.com/gothinkster/golang-gin-realworld-example-app
# Django의 RealWorld와 동일한 사양의 Go 구현
```

### 8.3 Django 개발자가 자주 하는 실수

```go
// ============================================
// 실수 1: Nil Pointer Dereference
// ============================================

// ❌ 잘못된 코드
var user *User
fmt.Println(user.Name)  // Panic! (Django는 None.name → AttributeError)

// ✅ 올바른 코드
var user *User
if user != nil {
    fmt.Println(user.Name)
}


// ============================================
// 실수 2: 에러 무시
// ============================================

// ❌ Django 습관 (예외 무시)
user, _ := service.GetUser(id)  // 에러 무시!
return c.JSON(200, user)

// ✅ Go 방식 (명시적 처리)
user, err := service.GetUser(id)
if err != nil {
    return c.JSON(404, map[string]string{"error": "Not found"})
}
return c.JSON(200, user)


// ============================================
// 실수 3: Goroutine 남발
// ============================================

// ❌ 의미 없는 goroutine
func handler(c echo.Context) error {
    go func() {
        // 결과를 못 받음!
        result := doSomething()
    }()
    return c.JSON(200, "OK")  // result 없이 응답
}

// ✅ 필요할 때만 사용
func handler(c echo.Context) error {
    result := doSomething()  // 동기로 충분
    return c.JSON(200, result)
}


// ============================================
// 실수 4: 슬라이스 참조 공유
// ============================================

// ❌ Django 리스트처럼 사용
original := []int{1, 2, 3}
copied := original  // 참조 복사 (Django는 값 복사)
copied[0] = 999
fmt.Println(original)  // [999, 2, 3] - 원본도 변경됨!

// ✅ 복사본 생성
original := []int{1, 2, 3}
copied := make([]int, len(original))
copy(copied, original)
copied[0] = 999
fmt.Println(original)  // [1, 2, 3] - 원본 유지
```

---

## 9. 마무리 및 결론

### 9.1 Django vs Go - 언제 무엇을 선택할까?

```yaml
Django를 선택해야 할 때:
  ✅ Admin 페이지 필요 (자동 생성)
  ✅ 빠른 프로토타이핑 (Batteries-included)
  ✅ 팀이 Python에 익숙
  ✅ ORM의 강력함 필요 (복잡한 쿼리)
  ✅ 템플릿 엔진 필요 (SSR)
  
  사례:
    - CMS, 관리자 도구
    - MVP, 스타트업 초기
    - 데이터 분석 + 웹 (Pandas 연동)

Go를 선택해야 할 때:
  ✅ 고성능 필요 (10,000+ req/s)
  ✅ 마이크로서비스 아키텍처
  ✅ 낮은 메모리 사용량 (비용 절감)
  ✅ 빠른 배포 (단일 바이너리)
  ✅ 동시성 처리 (WebSocket, 실시간)
  
  사례:
    - API 서버 (모바일 백엔드)
    - 마이크로서비스
    - 실시간 시스템 (채팅, 게임)
    - DevOps 도구 (CLI, 에이전트)

혼합 사용:
  - Django: Admin, CMS
  - Go: 고성능 API, 마이크로서비스
  예: Instagram (Django 웹 + Go API)
```

### 9.2 다음 단계

```bash
# ============================================
# 1. 프로젝트로 배우기 (Django 프로젝트를 Go로!)
# ============================================

# 예시: Django 블로그를 Go로 재구현
- 사용자 인증 (JWT)
- 게시물 CRUD
- 댓글 시스템
- 파일 업로드 (이미지)
- 페이지네이션
- 검색 (Full-text)


# ============================================
# 2. 고급 주제 학습
# ============================================

- Microservices (gRPC)
- Message Queue (RabbitMQ, Kafka)
- Caching (Redis)
- Monitoring (Prometheus)
- Tracing (Jaeger)


# ============================================
# 3. 오픈소스 기여
# ============================================

https://github.com/labstack/echo
https://github.com/gin-gonic/gin
https://github.com/go-gorm/gorm

# Django Rest Framework 경험 → Echo/Gin 기여
```

### 9.3 최종 정리

**Django 개발자가 Go를 배우면 얻는 것:**

1. **성능 인사이트** - 왜 Django가 느린지, 어떻게 최적화할지 이해
2. **시스템 프로그래밍** - 메모리, 동시성, 네트워크에 대한 깊은 이해
3. **배포 자유도** - 컨테이너 없이도 배포 가능
4. **경력 확장** - 클라우드 네이티브 (K8s, 마이크로서비스) 진입

**코드 한 줄의 차이:**

```python
# Django (암묵적, 편리함)
user = User.objects.get(id=1)  # 에러 시 자동 처리

# Go (명시적, 안정성)
user, err := repo.FindByID(1)  # 에러를 명시적으로 처리
if err != nil {
    return handleError(err)
}
```

이 차이가 **"편리함"**과 **"안정성"**의 철학 차이입니다.

**Django는 개발자를 편하게 하고, Go는 시스템을 안정하게 합니다.**

이제 `go run main.go`를 실행해보세요. Django 개발자로서의 경험이 Go에서도 빛을 발할 것입니다! 🚀

