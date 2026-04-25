---
title: "🛒 Django Ninja로 쇼핑몰 API 구축하기: 기초편"
date: 2025-10-21 09:00:00 +0900
categories: [Backend, Django]
tags: [Django-Ninja, 쇼핑몰, API개발, Python, 전자상거래]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-21-django-ninja-shopping-mall-basic.webp"
---

## 🎯 Django Ninja로 만드는 현대적 쇼핑몰 API

전자상거래가 일상이 된 2025년, 온라인 쇼핑몰 개발은 모든 개발자가 한 번쯤 도전해보고 싶은 프로젝트입니다. 

오늘은 **Django Ninja**를 사용해서 **실제 운영 가능한 쇼핑몰 API**를 처음부터 구축해보겠습니다. Django의 안정성과 생산성, 그리고 FastAPI 스타일의 현대적 문법을 결합한 Django Ninja로 어떻게 효율적으로 쇼핑몰을 만들 수 있는지 알아보겠습니다.

> 💡 **학습 목표**: 상품 관리, 장바구니, 주문 처리, 결제 연동까지 실제 쇼핑몰의 핵심 기능을 API로 구현해봅니다.

---

## 📚 목차
1. [🏗️ 프로젝트 초기 설정](#-프로젝트-초기-설정)
2. [👤 사용자 모델 및 인증](#-사용자-모델-및-인증)
3. [📦 상품 관리 시스템](#-상품-관리-시스템)
4. [🛒 장바구니 기능](#-장바구니-기능)
5. [💳 주문 및 결제 시스템](#-주문-및-결제-시스템)
6. [🔍 검색 및 필터링](#-검색-및-필터링)
7. [📊 관리자 대시보드](#-관리자-대시보드)
8. [🚀 배포 준비](#-배포-준비)

---

## 🏗️ 프로젝트 초기 설정

### 환경 설정 및 의존성 설치

```bash
# 프로젝트 초기화
mkdir django-ninja-shop && cd django-ninja-shop
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필요한 패키지 설치
pip install django django-ninja pillow python-decouple psycopg2-binary
pip install django-cors-headers django-extensions ipython

# Django 프로젝트 생성
django-admin startproject shop_project .
cd shop_project

# 앱 생성
python manage.py startapp accounts
python manage.py startapp products  
python manage.py startapp cart
python manage.py startapp orders
python manage.py startapp api
```

### Django 설정 구성

```python
# settings.py
import os
from decouple import config

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'corsheaders',
    'django_extensions',
    
    # Local apps
    'accounts',
    'products',
    'cart',
    'orders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 데이터베이스 설정 (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='ninja_shop'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# 미디어 파일 설정
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS 설정 (프론트엔드 연동용)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 개발 서버
    "http://localhost:8080",  # Vue 개발 서버
]

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'shop.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

```python
# .env 파일 생성
DB_NAME=ninja_shop
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

첫 번째 섹션부터 시작했습니다. 계속 진행할까요?

## 👤 사용자 모델 및 인증

### 확장된 사용자 모델 구성

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """확장된 사용자 모델"""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 이메일로 로그인
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class UserProfile(models.Model):
    """사용자 프로필 정보"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # 배송 정보
    default_address = models.TextField(blank=True)
    default_postal_code = models.CharField(max_length=10, blank=True)
    default_city = models.CharField(max_length=50, blank=True)
    
    # 마케팅 동의
    marketing_consent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.email} Profile"

class Address(models.Model):
    """사용자 배송 주소"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)  # 받는 사람
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def save(self, *args, **kwargs):
        # 기본 주소는 하나만 설정
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.city}"
```

```python
# settings.py에 사용자 모델 등록
AUTH_USER_MODEL = 'accounts.User'
```

### Django Ninja 인증 스키마

```python
# accounts/schemas.py
from ninja import Schema
from typing import Optional
from datetime import datetime, date

class UserRegistrationSchema(Schema):
    """회원가입 스키마"""
    username: str
    email: str
    password: str
    password_confirm: str
    phone_number: Optional[str] = None
    birth_date: Optional[date] = None
    marketing_consent: bool = False

class UserLoginSchema(Schema):
    """로그인 스키마"""
    email: str
    password: str

class UserProfileSchema(Schema):
    """사용자 프로필 응답 스키마"""
    id: int
    username: str
    email: str
    phone_number: Optional[str]
    birth_date: Optional[date]
    created_at: datetime
    
    # 프로필 정보
    bio: Optional[str] = None
    default_address: Optional[str] = None
    default_city: Optional[str] = None
    marketing_consent: bool

class AddressSchema(Schema):
    """주소 스키마"""
    id: Optional[int] = None
    name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    postal_code: str
    is_default: bool = False

class AddressCreateSchema(Schema):
    """주소 생성 스키마"""
    name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    postal_code: str
    is_default: bool = False
```

### 인증 API 구현

```python
# accounts/api.py
from ninja import Router
from ninja.security import django_auth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.db import transaction
from typing import List

from .models import User, UserProfile, Address
from .schemas import (
    UserRegistrationSchema, UserLoginSchema, UserProfileSchema,
    AddressSchema, AddressCreateSchema
)

router = Router()

@router.post("/register", response=UserProfileSchema)
def register(request, payload: UserRegistrationSchema):
    """회원가입"""
    
    # 비밀번호 확인
    if payload.password != payload.password_confirm:
        return {"error": "비밀번호가 일치하지 않습니다."}, 400
    
    # 이메일 중복 확인
    if User.objects.filter(email=payload.email).exists():
        return {"error": "이미 사용 중인 이메일입니다."}, 400
    
    # 사용자명 중복 확인
    if User.objects.filter(username=payload.username).exists():
        return {"error": "이미 사용 중인 사용자명입니다."}, 400
    
    try:
        with transaction.atomic():
            # 사용자 생성
            user = User.objects.create(
                username=payload.username,
                email=payload.email,
                password=make_password(payload.password),
                phone_number=payload.phone_number,
                birth_date=payload.birth_date
            )
            
            # 프로필 생성
            UserProfile.objects.create(
                user=user,
                marketing_consent=payload.marketing_consent
            )
            
            return UserProfileSchema(
                id=user.id,
                username=user.username,
                email=user.email,
                phone_number=user.phone_number,
                birth_date=user.birth_date,
                created_at=user.created_at,
                bio=user.profile.bio,
                default_address=user.profile.default_address,
                default_city=user.profile.default_city,
                marketing_consent=user.profile.marketing_consent
            )
            
    except Exception as e:
        return {"error": "회원가입 중 오류가 발생했습니다."}, 500

@router.post("/login")
def login_user(request, payload: UserLoginSchema):
    """로그인"""
    user = authenticate(request, username=payload.email, password=payload.password)
    
    if user is not None:
        if user.is_active:
            login(request, user)
            return {
                "message": "로그인 성공",
                "user": UserProfileSchema(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    phone_number=user.phone_number,
                    birth_date=user.birth_date,
                    created_at=user.created_at,
                    bio=user.profile.bio if hasattr(user, 'profile') else None,
                    default_address=user.profile.default_address if hasattr(user, 'profile') else None,
                    default_city=user.profile.default_city if hasattr(user, 'profile') else None,
                    marketing_consent=user.profile.marketing_consent if hasattr(user, 'profile') else False
                )
            }
        else:
            return {"error": "비활성화된 계정입니다."}, 400
    else:
        return {"error": "이메일 또는 비밀번호가 올바르지 않습니다."}, 401

@router.post("/logout", auth=django_auth)
def logout_user(request):
    """로그아웃"""
    logout(request)
    return {"message": "로그아웃되었습니다."}

@router.get("/profile", response=UserProfileSchema, auth=django_auth)
def get_profile(request):
    """프로필 조회"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    return UserProfileSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        birth_date=user.birth_date,
        created_at=user.created_at,
        bio=profile.bio if profile else None,
        default_address=profile.default_address if profile else None,
        default_city=profile.default_city if profile else None,
        marketing_consent=profile.marketing_consent if profile else False
    )

@router.get("/addresses", response=List[AddressSchema], auth=django_auth)
def get_addresses(request):
    """주소 목록 조회"""
    addresses = Address.objects.filter(user=request.user)
    return [
        AddressSchema(
            id=addr.id,
            name=addr.name,
            phone=addr.phone,
            address_line1=addr.address_line1,
            address_line2=addr.address_line2,
            city=addr.city,
            postal_code=addr.postal_code,
            is_default=addr.is_default
        )
        for addr in addresses
    ]

@router.post("/addresses", response=AddressSchema, auth=django_auth)
def create_address(request, payload: AddressCreateSchema):
    """새 주소 추가"""
    address = Address.objects.create(
        user=request.user,
        name=payload.name,
        phone=payload.phone,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        postal_code=payload.postal_code,
        is_default=payload.is_default
    )
    
    return AddressSchema(
        id=address.id,
        name=address.name,
        phone=address.phone,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        city=address.city,
        postal_code=address.postal_code,
        is_default=address.is_default
    )

@router.delete("/addresses/{address_id}", auth=django_auth)
def delete_address(request, address_id: int):
    """주소 삭제"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    return {"message": "주소가 삭제되었습니다."}
```

## 📦 상품 관리 시스템

### 상품 모델 설계

```python
# products/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()

class Category(models.Model):
    """상품 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Brand(models.Model):
    """브랜드"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """상품"""
    class Status(models.TextChoices):
        DRAFT = 'draft', '임시저장'
        ACTIVE = 'active', '판매중'
        INACTIVE = 'inactive', '판매중지'
        OUT_OF_STOCK = 'out_of_stock', '품절'
    
    # 기본 정보
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    description = models.TextField()
    short_description = models.CharField(max_length=255)
    
    # 분류
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products', null=True, blank=True)
    
    # 가격 정보
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 할인 전 가격
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 원가
    
    # 재고 관리
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=5)
    track_stock = models.BooleanField(default=True)
    
    # 배송 정보
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # kg
    shipping_required = models.BooleanField(default=True)
    
    # 상태 및 메타 정보
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)  # 추천 상품
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['featured']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_in_stock(self):
        """재고 있는지 확인"""
        if not self.track_stock:
            return True
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        """재고 부족 여부"""
        if not self.track_stock:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def discount_percentage(self):
        """할인율 계산"""
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100, 1)
        return 0

class ProductImage(models.Model):
    """상품 이미지"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['sort_order']
    
    def save(self, *args, **kwargs):
        # 첫 번째 이미지를 자동으로 primary로 설정
        if self.is_primary:
            ProductImage.objects.filter(product=self.product).update(is_primary=False)
        elif not ProductImage.objects.filter(product=self.product, is_primary=True).exists():
            self.is_primary = True
        super().save(*args, **kwargs)

class ProductReview(models.Model):
    """상품 리뷰"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)  # 구매 확인된 리뷰
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user']  # 한 사용자당 하나의 리뷰만
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.rating}stars by {self.user.username}"
```

계속해서 상품 API를 구현하겠습니다. 다음 섹션으로 넘어갈까요?

### 상품 API 구현

```python
# products/schemas.py
from ninja import Schema
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class CategorySchema(Schema):
    id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool

class BrandSchema(Schema):
    id: int
    name: str
    slug: str
    description: Optional[str]

class ProductImageSchema(Schema):
    id: int
    image: str
    alt_text: Optional[str]
    is_primary: bool

class ProductListSchema(Schema):
    """상품 목록용 간단한 스키마"""
    id: int
    name: str
    slug: str
    price: Decimal
    compare_price: Optional[Decimal]
    discount_percentage: int
    primary_image: Optional[str]
    category: CategorySchema
    brand: Optional[BrandSchema]
    status: str
    featured: bool
    is_in_stock: bool

class ProductDetailSchema(Schema):
    """상품 상세 정보"""
    id: int
    name: str
    slug: str
    sku: str
    description: str
    short_description: str
    price: Decimal
    compare_price: Optional[Decimal]
    discount_percentage: int
    stock_quantity: int
    is_in_stock: bool
    is_low_stock: bool
    weight: Optional[Decimal]
    shipping_required: bool
    status: str
    featured: bool
    meta_title: Optional[str]
    meta_description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # 관계 데이터
    category: CategorySchema
    brand: Optional[BrandSchema]
    images: List[ProductImageSchema]

class ProductCreateSchema(Schema):
    name: str
    description: str
    short_description: str
    category_id: int
    brand_id: Optional[int] = None
    price: Decimal
    compare_price: Optional[Decimal] = None
    stock_quantity: int = 0
    weight: Optional[Decimal] = None
    shipping_required: bool = True
    featured: bool = False
```

```python
# products/api.py
from ninja import Router, Query
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from typing import List, Optional

from .models import Product, Category, Brand, ProductReview
from .schemas import ProductListSchema, ProductDetailSchema, CategorySchema, BrandSchema

router = Router()

@router.get("/categories", response=List[CategorySchema])
def list_categories(request):
    """카테고리 목록"""
    return Category.objects.filter(is_active=True)

@router.get("/brands", response=List[BrandSchema])
def list_brands(request):
    """브랜드 목록"""
    return Brand.objects.filter(is_active=True)

@router.get("/products", response=List[ProductListSchema])
@paginate
def list_products(
    request,
    category: Optional[str] = Query(None, description="카테고리 슬러그"),
    brand: Optional[str] = Query(None, description="브랜드 슬러그"),
    search: Optional[str] = Query(None, description="검색어"),
    min_price: Optional[float] = Query(None, description="최소 가격"),
    max_price: Optional[float] = Query(None, description="최대 가격"),
    featured: Optional[bool] = Query(None, description="추천 상품만"),
    sort_by: str = Query("created_at", description="정렬 기준: price, -price, created_at, -created_at, name")
):
    """상품 목록 조회"""
    
    queryset = Product.objects.filter(status='active').select_related(
        'category', 'brand'
    ).prefetch_related('images')
    
    # 필터링
    if category:
        queryset = queryset.filter(category__slug=category)
    
    if brand:
        queryset = queryset.filter(brand__slug=brand)
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(short_description__icontains=search)
        )
    
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    
    if max_price:
        queryset = queryset.filter(price__lte=max_price)
    
    if featured is not None:
        queryset = queryset.filter(featured=featured)
    
    # 정렬
    valid_sort_fields = ['price', '-price', 'created_at', '-created_at', 'name', '-name']
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    
    # 응답 데이터 구성
    products = []
    for product in queryset:
        primary_image = product.images.filter(is_primary=True).first()
        
        products.append(ProductListSchema(
            id=product.id,
            name=product.name,
            slug=product.slug,
            price=product.price,
            compare_price=product.compare_price,
            discount_percentage=product.discount_percentage,
            primary_image=primary_image.image.url if primary_image else None,
            category=CategorySchema(
                id=product.category.id,
                name=product.category.name,
                slug=product.category.slug,
                description=product.category.description,
                is_active=product.category.is_active
            ),
            brand=BrandSchema(
                id=product.brand.id,
                name=product.brand.name,
                slug=product.brand.slug,
                description=product.brand.description
            ) if product.brand else None,
            status=product.status,
            featured=product.featured,
            is_in_stock=product.is_in_stock
        ))
    
    return products

@router.get("/products/{slug}", response=ProductDetailSchema)
def get_product(request, slug: str):
    """상품 상세 정보"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('images'),
        slug=slug,
        status='active'
    )
    
    return ProductDetailSchema(
        id=product.id,
        name=product.name,
        slug=product.slug,
        sku=product.sku,
        description=product.description,
        short_description=product.short_description,
        price=product.price,
        compare_price=product.compare_price,
        discount_percentage=product.discount_percentage,
        stock_quantity=product.stock_quantity,
        is_in_stock=product.is_in_stock,
        is_low_stock=product.is_low_stock,
        weight=product.weight,
        shipping_required=product.shipping_required,
        status=product.status,
        featured=product.featured,
        meta_title=product.meta_title,
        meta_description=product.meta_description,
        created_at=product.created_at,
        updated_at=product.updated_at,
        category=CategorySchema(
            id=product.category.id,
            name=product.category.name,
            slug=product.category.slug,
            description=product.category.description,
            is_active=product.category.is_active
        ),
        brand=BrandSchema(
            id=product.brand.id,
            name=product.brand.name,
            slug=product.brand.slug,
            description=product.brand.description
        ) if product.brand else None,
        images=[
            ProductImageSchema(
                id=img.id,
                image=img.image.url,
                alt_text=img.alt_text,
                is_primary=img.is_primary
            )
            for img in product.images.all()
        ]
    )

@router.get("/products/{product_id}/reviews")
def get_product_reviews(request, product_id: int):
    """상품 리뷰 목록"""
    product = get_object_or_404(Product, id=product_id)
    
    reviews = ProductReview.objects.filter(product=product).select_related('user')
    
    # 리뷰 통계
    review_stats = reviews.aggregate(
        average_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    # 평점별 분포
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[f'rating_{i}'] = reviews.filter(rating=i).count()
    
    return {
        "stats": review_stats,
        "distribution": rating_distribution,
        "reviews": [
            {
                "id": review.id,
                "user": review.user.username,
                "rating": review.rating,
                "title": review.title,
                "content": review.content,
                "is_verified_purchase": review.is_verified_purchase,
                "created_at": review.created_at
            }
            for review in reviews[:10]  # 최신 10개만
        ]
    }
```

## 🛒 장바구니 기능

### 장바구니 모델

```python
# cart/models.py
from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from decimal import Decimal

User = get_user_model()

class Cart(models.Model):
    """장바구니"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # 비로그인 사용자용
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.email if self.user else self.session_key}"
    
    @property
    def total_items(self):
        """총 상품 개수"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_amount(self):
        """총 금액"""
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    """장바구니 아이템"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_price(self):
        """아이템 총 가격"""
        return self.product.price * self.quantity
    
    def save(self, *args, **kwargs):
        # 재고 확인
        if self.product.track_stock and self.quantity > self.product.stock_quantity:
            raise ValueError("재고가 부족합니다.")
        super().save(*args, **kwargs)
```

### 장바구니 API

```python
# cart/schemas.py
from ninja import Schema
from typing import List
from decimal import Decimal

class CartItemSchema(Schema):
    id: int
    product_id: int
    product_name: str
    product_price: Decimal
    product_image: str = None
    quantity: int
    total_price: Decimal

class CartSchema(Schema):
    id: int
    items: List[CartItemSchema]
    total_items: int
    total_amount: Decimal

class AddToCartSchema(Schema):
    product_id: int
    quantity: int = 1

class UpdateCartItemSchema(Schema):
    quantity: int
```

```python
# cart/api.py
from ninja import Router
from ninja.security import django_auth
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Cart, CartItem
from .schemas import CartSchema, CartItemSchema, AddToCartSchema, UpdateCartItemSchema
from products.models import Product

router = Router()

def get_or_create_cart(request):
    """장바구니 가져오기 또는 생성"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # 세션 기반 장바구니 (비로그인 사용자)
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    return cart

@router.get("/cart", response=CartSchema)
def get_cart(request):
    """장바구니 조회"""
    cart = get_or_create_cart(request)
    
    items = []
    for item in cart.items.select_related('product').prefetch_related('product__images'):
        primary_image = item.product.images.filter(is_primary=True).first()
        
        items.append(CartItemSchema(
            id=item.id,
            product_id=item.product.id,
            product_name=item.product.name,
            product_price=item.product.price,
            product_image=primary_image.image.url if primary_image else None,
            quantity=item.quantity,
            total_price=item.total_price
        ))
    
    return CartSchema(
        id=cart.id,
        items=items,
        total_items=cart.total_items,
        total_amount=cart.total_amount
    )

@router.post("/cart/add", response=CartItemSchema)
def add_to_cart(request, payload: AddToCartSchema):
    """장바구니에 상품 추가"""
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=payload.product_id, status='active')
    
    # 재고 확인
    if product.track_stock and payload.quantity > product.stock_quantity:
        return {"error": "재고가 부족합니다."}, 400
    
    try:
        with transaction.atomic():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': payload.quantity}
            )
            
            if not created:
                # 기존 아이템이 있으면 수량 증가
                new_quantity = cart_item.quantity + payload.quantity
                if product.track_stock and new_quantity > product.stock_quantity:
                    return {"error": "재고가 부족합니다."}, 400
                cart_item.quantity = new_quantity
                cart_item.save()
            
            primary_image = product.images.filter(is_primary=True).first()
            
            return CartItemSchema(
                id=cart_item.id,
                product_id=product.id,
                product_name=product.name,
                product_price=product.price,
                product_image=primary_image.image.url if primary_image else None,
                quantity=cart_item.quantity,
                total_price=cart_item.total_price
            )
            
    except ValueError as e:
        return {"error": str(e)}, 400

@router.put("/cart/items/{item_id}", response=CartItemSchema)
def update_cart_item(request, item_id: int, payload: UpdateCartItemSchema):
    """장바구니 아이템 수량 수정"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    if payload.quantity <= 0:
        cart_item.delete()
        return {"message": "상품이 장바구니에서 제거되었습니다."}
    
    # 재고 확인
    if cart_item.product.track_stock and payload.quantity > cart_item.product.stock_quantity:
        return {"error": "재고가 부족합니다."}, 400
    
    cart_item.quantity = payload.quantity
    cart_item.save()
    
    primary_image = cart_item.product.images.filter(is_primary=True).first()
    
    return CartItemSchema(
        id=cart_item.id,
        product_id=cart_item.product.id,
        product_name=cart_item.product.name,
        product_price=cart_item.product.price,
        product_image=primary_image.image.url if primary_image else None,
        quantity=cart_item.quantity,
        total_price=cart_item.total_price
    )

@router.delete("/cart/items/{item_id}")
def remove_from_cart(request, item_id: int):
    """장바구니에서 상품 제거"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    return {"message": "상품이 장바구니에서 제거되었습니다."}

@router.delete("/cart/clear")
def clear_cart(request):
    """장바구니 비우기"""
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    return {"message": "장바구니가 비워졌습니다."}
```

다음 섹션에서 주문 및 결제 시스템을 구현하겠습니다. 계속 진행할까요?

## 💳 주문 및 결제 시스템

### 주문 모델 설계

```python
# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from accounts.models import Address
from decimal import Decimal
import uuid

User = get_user_model()

class Order(models.Model):
    """주문"""
    class Status(models.TextChoices):
        PENDING = 'pending', '결제 대기'
        PAID = 'paid', '결제 완료'
        PROCESSING = 'processing', '처리 중'
        SHIPPED = 'shipped', '배송 중'
        DELIVERED = 'delivered', '배송 완료'
        CANCELLED = 'cancelled', '취소됨'
        REFUNDED = 'refunded', '환불됨'
    
    # 주문 기본 정보
    order_number = models.CharField(max_length=32, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 금액 정보
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # 상품 총액
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 배송 정보
    shipping_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=50)
    shipping_postal_code = models.CharField(max_length=10)
    
    # 추가 정보
    notes = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"

class OrderItem(models.Model):
    """주문 상품"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # 주문 당시의 상품 정보 (가격 변동에 대비)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

class Payment(models.Model):
    """결제 정보"""
    class Method(models.TextChoices):
        CARD = 'card', '신용카드'
        BANK_TRANSFER = 'bank_transfer', '계좌이체'
        VIRTUAL_ACCOUNT = 'virtual_account', '가상계좌'
        MOBILE = 'mobile', '휴대폰'
    
    class Status(models.TextChoices):
        PENDING = 'pending', '결제 대기'
        SUCCESS = 'success', '결제 완료'
        FAILED = 'failed', '결제 실패'
        CANCELLED = 'cancelled', '결제 취소'
        REFUNDED = 'refunded', '환불 완료'
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 결제 금액
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 결제 게이트웨이 정보
    transaction_id = models.CharField(max_length=100, blank=True)  # PG사 거래 ID
    pg_provider = models.CharField(max_length=50, blank=True)  # 결제 제공업체
    
    # 타임스탬프
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment for {self.order.order_number}"
```

### 주문 API 구현

```python
# orders/schemas.py
from ninja import Schema
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class OrderItemSchema(Schema):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal

class OrderSchema(Schema):
    id: int
    order_number: str
    status: str
    subtotal: Decimal
    shipping_cost: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    
    shipping_name: str
    shipping_phone: str
    shipping_address_line1: str
    shipping_address_line2: Optional[str]
    shipping_city: str
    shipping_postal_code: str
    
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    items: List[OrderItemSchema]

class CreateOrderSchema(Schema):
    address_id: int
    payment_method: str
    notes: Optional[str] = None

class PaymentSchema(Schema):
    id: int
    payment_method: str
    status: str
    amount: Decimal
    transaction_id: Optional[str]
    pg_provider: Optional[str]
    paid_at: Optional[datetime]
```

```python
# orders/api.py
from ninja import Router
from ninja.security import django_auth
from django.shortcuts import get_object_or_404
from django.db import transaction
from typing import List
from decimal import Decimal

from .models import Order, OrderItem, Payment
from .schemas import OrderSchema, CreateOrderSchema, OrderItemSchema
from cart.models import Cart
from accounts.models import Address

router = Router()

@router.get("/orders", response=List[OrderSchema], auth=django_auth)
def list_orders(request):
    """사용자 주문 목록"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    
    result = []
    for order in orders:
        result.append(OrderSchema(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            subtotal=order.subtotal,
            shipping_cost=order.shipping_cost,
            tax_amount=order.tax_amount,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            shipping_name=order.shipping_name,
            shipping_phone=order.shipping_phone,
            shipping_address_line1=order.shipping_address_line1,
            shipping_address_line2=order.shipping_address_line2,
            shipping_city=order.shipping_city,
            shipping_postal_code=order.shipping_postal_code,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                OrderItemSchema(
                    id=item.id,
                    product_id=item.product.id,
                    product_name=item.product_name,
                    product_sku=item.product_sku,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    total_price=item.total_price
                )
                for item in order.items.all()
            ]
        ))
    
    return result

@router.post("/orders", response=OrderSchema, auth=django_auth)
def create_order(request, payload: CreateOrderSchema):
    """주문 생성"""
    
    # 장바구니 확인
    try:
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            return {"error": "장바구니가 비어있습니다."}, 400
    except Cart.DoesNotExist:
        return {"error": "장바구니를 찾을 수 없습니다."}, 400
    
    # 배송 주소 확인
    address = get_object_or_404(Address, id=payload.address_id, user=request.user)
    
    try:
        with transaction.atomic():
            # 재고 확인 및 차감
            cart_items = cart.items.select_related('product')
            subtotal = Decimal('0')
            
            for cart_item in cart_items:
                product = cart_item.product
                if product.track_stock and cart_item.quantity > product.stock_quantity:
                    return {"error": f"{product.name}의 재고가 부족합니다."}, 400
                
                subtotal += cart_item.total_price
            
            # 배송비 계산 (간단한 예시)
            shipping_cost = Decimal('3000') if subtotal < 50000 else Decimal('0')
            
            # 세금 계산 (10%)
            tax_amount = subtotal * Decimal('0.1')
            
            total_amount = subtotal + shipping_cost + tax_amount
            
            # 주문 생성
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax_amount=tax_amount,
                total_amount=total_amount,
                shipping_name=address.name,
                shipping_phone=address.phone,
                shipping_address_line1=address.address_line1,
                shipping_address_line2=address.address_line2,
                shipping_city=address.city,
                shipping_postal_code=address.postal_code,
                notes=payload.notes or ''
            )
            
            # 주문 상품 생성 및 재고 차감
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_sku=cart_item.product.sku,
                    unit_price=cart_item.product.price,
                    quantity=cart_item.quantity,
                    total_price=cart_item.total_price
                )
                
                # 재고 차감
                if cart_item.product.track_stock:
                    cart_item.product.stock_quantity -= cart_item.quantity
                    cart_item.product.save()
            
            # 결제 정보 생성
            Payment.objects.create(
                order=order,
                payment_method=payload.payment_method,
                amount=total_amount
            )
            
            # 장바구니 비우기
            cart.items.all().delete()
            
            return OrderSchema(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                subtotal=order.subtotal,
                shipping_cost=order.shipping_cost,
                tax_amount=order.tax_amount,
                discount_amount=order.discount_amount,
                total_amount=order.total_amount,
                shipping_name=order.shipping_name,
                shipping_phone=order.shipping_phone,
                shipping_address_line1=order.shipping_address_line1,
                shipping_address_line2=order.shipping_address_line2,
                shipping_city=order.shipping_city,
                shipping_postal_code=order.shipping_postal_code,
                notes=order.notes,
                created_at=order.created_at,
                updated_at=order.updated_at,
                items=[
                    OrderItemSchema(
                        id=item.id,
                        product_id=item.product.id,
                        product_name=item.product_name,
                        product_sku=item.product_sku,
                        unit_price=item.unit_price,
                        quantity=item.quantity,
                        total_price=item.total_price
                    )
                    for item in order.items.all()
                ]
            )
            
    except Exception as e:
        return {"error": "주문 생성 중 오류가 발생했습니다."}, 500

@router.get("/orders/{order_id}", response=OrderSchema, auth=django_auth)
def get_order(request, order_id: int):
    """주문 상세 조회"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        id=order_id,
        user=request.user
    )
    
    return OrderSchema(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total_amount=order.total_amount,
        shipping_name=order.shipping_name,
        shipping_phone=order.shipping_phone,
        shipping_address_line1=order.shipping_address_line1,
        shipping_address_line2=order.shipping_address_line2,
        shipping_city=order.shipping_city,
        shipping_postal_code=order.shipping_postal_code,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemSchema(
                id=item.id,
                product_id=item.product.id,
                product_name=item.product_name,
                product_sku=item.product_sku,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total_price=item.total_price
            )
            for item in order.items.all()
        ]
    )

@router.post("/orders/{order_id}/cancel", auth=django_auth)
def cancel_order(request, order_id: int):
    """주문 취소"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['pending', 'paid']:
        return {"error": "취소할 수 없는 주문 상태입니다."}, 400
    
    with transaction.atomic():
        # 재고 복구
        for item in order.items.all():
            if item.product.track_stock:
                item.product.stock_quantity += item.quantity
                item.product.save()
        
        # 주문 상태 변경
        order.status = 'cancelled'
        order.save()
        
        # 결제 취소 처리
        if hasattr(order, 'payment'):
            order.payment.status = 'cancelled'
            order.payment.save()
    
    return {"message": "주문이 취소되었습니다."}
```

## 🔍 검색 및 필터링

```python
# products/search.py
from django.db.models import Q, Count
from .models import Product, Category

class ProductSearchService:
    """상품 검색 서비스"""
    
    @staticmethod
    def search_products(query, filters=None):
        """고급 상품 검색"""
        queryset = Product.objects.filter(status='active')
        
        if query:
            # 기본 텍스트 검색
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(brand__name__icontains=query)
            )
        
        if filters:
            # 카테고리 필터
            if filters.get('category_ids'):
                queryset = queryset.filter(category_id__in=filters['category_ids'])
            
            # 브랜드 필터
            if filters.get('brand_ids'):
                queryset = queryset.filter(brand_id__in=filters['brand_ids'])
            
            # 가격 범위 필터
            if filters.get('min_price'):
                queryset = queryset.filter(price__gte=filters['min_price'])
            if filters.get('max_price'):
                queryset = queryset.filter(price__lte=filters['max_price'])
            
            # 재고 있는 상품만
            if filters.get('in_stock'):
                queryset = queryset.filter(
                    Q(track_stock=False) | Q(stock_quantity__gt=0)
                )
            
            # 할인 상품만
            if filters.get('on_sale'):
                queryset = queryset.filter(compare_price__gt=models.F('price'))
        
        return queryset.distinct()
    
    @staticmethod
    def get_search_suggestions(query, limit=5):
        """검색 자동완성"""
        if len(query) < 2:
            return []
        
        # 상품명에서 검색
        products = Product.objects.filter(
            name__icontains=query,
            status='active'
        ).values_list('name', flat=True)[:limit]
        
        # 카테고리에서 검색
        categories = Category.objects.filter(
            name__icontains=query,
            is_active=True
        ).values_list('name', flat=True)[:limit]
        
        suggestions = list(products) + list(categories)
        return suggestions[:limit]
```

## 📊 관리자 대시보드

```python
# api/admin_api.py
from ninja import Router
from ninja.security import django_auth
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta

from products.models import Product
from orders.models import Order
from accounts.models import User

router = Router()

@router.get("/admin/dashboard", auth=django_auth)
def admin_dashboard(request):
    """관리자 대시보드"""
    if not request.user.is_staff:
        return {"error": "권한이 없습니다."}, 403
    
    # 기간 설정 (최근 30일)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # 주요 지표
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        status__in=['paid', 'processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='active').count()
    
    total_users = User.objects.count()
    new_users_30d = User.objects.filter(created_at__gte=thirty_days_ago).count()
    
    # 최근 주문
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # 인기 상품 (최근 30일)
    popular_products = Product.objects.filter(
        orderitem__order__created_at__gte=thirty_days_ago
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:5]
    
    return {
        "stats": {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "total_products": total_products,
            "active_products": active_products,
            "total_users": total_users,
            "new_users_30d": new_users_30d
        },
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "user_email": order.user.email,
                "total_amount": float(order.total_amount),
                "status": order.status,
                "created_at": order.created_at
            }
            for order in recent_orders
        ],
        "popular_products": [
            {
                "id": product.id,
                "name": product.name,
                "order_count": product.order_count,
                "price": float(product.price)
            }
            for product in popular_products
        ]
    }
```

## 🚀 배포 준비

### 메인 API 라우터 설정

```python
# api/api.py
from ninja import NinjaAPI
from accounts.api import router as accounts_router
from products.api import router as products_router
from cart.api import router as cart_router
from orders.api import router as orders_router
from .admin_api import router as admin_router

api = NinjaAPI(
    title="Django Ninja Shopping Mall API",
    description="Django Ninja로 구축한 쇼핑몰 API",
    version="1.0.0"
)

# 라우터 등록
api.add_router("/auth", accounts_router)
api.add_router("/", products_router)
api.add_router("/", cart_router)
api.add_router("/", orders_router)
api.add_router("/", admin_router)

@api.get("/health")
def health_check(request):
    """헬스체크"""
    return {"status": "healthy", "message": "Django Ninja Shopping Mall API"}
```

```python
# shop_project/urls.py
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from api.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 생성 및 적용
python manage.py makemigrations accounts
python manage.py makemigrations products
python manage.py makemigrations cart
python manage.py makemigrations orders

python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser

# 개발 서버 실행
python manage.py runserver
```

### API 테스트

```bash
# API 문서 확인
# http://localhost:8000/api/docs

# 기본 API 테스트
curl -X GET "http://localhost:8000/api/health"
curl -X GET "http://localhost:8000/api/products"
curl -X GET "http://localhost:8000/api/categories"
```

## 🎉 마무리

Django Ninja로 쇼핑몰 API의 기초 구조를 완성했습니다! 

### ✅ 구현된 기능들

- **👤 사용자 인증**: 회원가입, 로그인, 프로필 관리, 주소 관리
- **📦 상품 관리**: 카테고리, 브랜드, 상품 CRUD, 이미지 관리
- **🛒 장바구니**: 상품 추가/수정/삭제, 재고 확인
- **💳 주문 시스템**: 주문 생성, 결제 연동, 주문 관리
- **🔍 검색**: 상품 검색, 필터링, 자동완성
- **📊 관리자**: 대시보드, 통계, 주문 관리

### 🚀 확장 가능한 포인트

1. **결제 게이트웨이**: 토스페이먼츠, 이니시스 등 실제 PG 연동
2. **쿠폰 시스템**: 할인 쿠폰, 적립금 기능
3. **리뷰 시스템**: 상품 리뷰, 평점 기능 확장
4. **알림 시스템**: 이메일, SMS, 푸시 알림
5. **재고 관리**: 자동 재고 알림, 발주 시스템
6. **배송 추적**: 택배사 API 연동
7. **추천 시스템**: AI 기반 상품 추천

Django Ninja의 강력한 기능과 Django의 안정성을 결합하여 확장 가능하고 유지보수가 쉬운 쇼핑몰 API를 구축할 수 있었습니다.

다음 편에서는 **실제 결제 연동과 고급 기능들**을 다뤄보겠습니다!

---

> 💬 **궁금한 점이나 개선 아이디어가 있으시다면** 댓글로 공유해주세요!  
> 🔔 **고급편과 실전 배포 가이드**를 받아보고 싶다면 구독해주세요!

**관련 포스트:**
- [Django Ninja vs FastAPI 심화 비교](#)
- [Django 쇼핑몰 결제 시스템 구축하기](#)  
- [Django 성능 최적화 완벽 가이드](#)