---
layout: post
title: "Django 사용자 승인 시스템 구현 가이드: 승인대기/승인완료/정지 상태 관리"
date: 2025-07-30 10:00:00 +0900
categories: [Django, Python, Authentication, User Management]
tags: [Django, User, Authentication, Approval, Status, Admin, Permission, Security, Custom User Model]
---

사용자 가입 후 관리자의 승인이 필요한 시스템을 구축해야 할 때가 있습니다. 특히 기업 내부 시스템이나 제한된 서비스에서는 무분별한 가입을 방지하고 사용자를 체계적으로 관리하기 위해 승인 시스템이 필수적입니다. 이 글에서는 Django에서 사용자 상태를 **승인대기, 승인완료, 정지** 3단계로 관리하는 완전한 시스템을 구현해보겠습니다.

## 📚 사용자 승인 시스템 개요

### 왜 사용자 승인 시스템이 필요한가?

**일반적인 사용 사례:**
- 기업 내부 시스템 (직원만 접근 가능)
- 회원제 커뮤니티 (품질 관리)
- B2B 플랫폼 (사업자 검증 필요)
- 베타 서비스 (제한된 사용자 대상)

**사용자 상태별 정의:**
- **승인대기 (PENDING)**: 가입 신청했지만 관리자 승인 대기 중
- **승인완료 (APPROVED)**: 관리자가 승인하여 정상 이용 가능
- **정지 (SUSPENDED)**: 관리자가 이용을 제한한 상태

## 🏗️ 사용자 모델 설계

### Custom User Model 확장

Django의 기본 User 모델을 확장하여 승인 상태를 관리합니다.

```python
# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', '승인대기'
        APPROVED = 'approved', '승인완료'
        SUSPENDED = 'suspended', '정지'
    
    # 승인 상태 필드
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name='승인 상태'
    )
    
    # 승인 관련 날짜 추적
    approval_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='승인 날짜'
    )
    
    suspension_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='정지 날짜'
    )
    
    # 승인/정지 사유
    approval_reason = models.TextField(
        blank=True, 
        verbose_name='승인/정지 사유'
    )
    
    # 승인을 처리한 관리자
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        verbose_name='승인자'
    )
    
    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
    
    def __str__(self):
        return f"{self.username} ({self.get_approval_status_display()})"
    
    def is_approved(self):
        """승인된 사용자인지 확인"""
        return self.approval_status == self.ApprovalStatus.APPROVED
    
    def is_pending(self):
        """승인 대기 중인지 확인"""
        return self.approval_status == self.ApprovalStatus.PENDING
    
    def is_suspended(self):
        """정지된 사용자인지 확인"""
        return self.approval_status == self.ApprovalStatus.SUSPENDED
    
    def approve(self, approved_by_user, reason=""):
        """사용자 승인 처리"""
        self.approval_status = self.ApprovalStatus.APPROVED
        self.approval_date = timezone.now()
        self.approved_by = approved_by_user
        self.approval_reason = reason
        self.is_active = True  # Django 기본 활성화 상태도 True로 설정
        self.save()
    
    def suspend(self, suspended_by_user, reason=""):
        """사용자 정지 처리"""
        self.approval_status = self.ApprovalStatus.SUSPENDED
        self.suspension_date = timezone.now()
        self.approved_by = suspended_by_user
        self.approval_reason = reason
        self.is_active = False  # Django 기본 활성화 상태를 False로 설정
        self.save()
    
    def reset_to_pending(self):
        """승인 대기 상태로 초기화"""
        self.approval_status = self.ApprovalStatus.PENDING
        self.approval_date = None
        self.suspension_date = None
        self.approval_reason = ""
        self.approved_by = None
        self.is_active = False
        self.save()
```

### settings.py 설정

```python
# settings.py
AUTH_USER_MODEL = 'your_app.User'  # your_app을 실제 앱 이름으로 변경

# 이메일 설정 (승인 알림용)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

## 🔐 인증 백엔드 커스터마이징

승인된 사용자만 로그인할 수 있도록 인증 백엔드를 커스터마이징합니다.

```python
# authentication.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class ApprovalRequiredBackend(ModelBackend):
    """승인된 사용자만 로그인 가능한 인증 백엔드"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 기본 인증 수행
        user = super().authenticate(request, username, password, **kwargs)
        
        if user is None:
            return None
        
        # 승인된 사용자만 로그인 허용
        if not user.is_approved():
            return None
        
        return user
    
    def user_can_authenticate(self, user):
        """승인된 사용자만 인증 가능"""
        return user.is_approved() and super().user_can_authenticate(user)
```

```python
# settings.py에 백엔드 추가
AUTHENTICATION_BACKENDS = [
    'your_app.authentication.ApprovalRequiredBackend',  # 커스텀 백엔드
    'django.contrib.auth.backends.ModelBackend',        # 기본 백엔드 (관리자용)
]
```

## 📝 회원가입 및 로그인 뷰 구현

### 회원가입 폼

```python
# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # 가입 시 승인대기 상태로 설정
        user.approval_status = User.ApprovalStatus.PENDING
        user.is_active = False  # 승인 전까지는 비활성화
        
        if commit:
            user.save()
            
        return user
```

### 회원가입 뷰

```python
# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserRegistrationForm

def register(request):
    """회원가입 처리"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # 관리자에게 새 사용자 가입 알림 이메일 발송
            send_approval_notification_to_admin(user)
            
            messages.success(
                request, 
                '회원가입이 완료되었습니다. 관리자 승인 후 로그인이 가능합니다.'
            )
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def send_approval_notification_to_admin(user):
    """관리자에게 승인 요청 알림 발송"""
    subject = f'새 사용자 승인 요청: {user.username}'
    message = f"""
    새로운 사용자가 가입을 신청했습니다.
    
    사용자명: {user.username}
    이름: {user.get_full_name()}
    이메일: {user.email}
    가입일: {user.date_joined}
    
    관리자 페이지에서 승인 처리해주세요.
    """
    
    # 관리자 이메일 목록 (settings에서 설정)
    admin_emails = getattr(settings, 'ADMIN_EMAILS', [settings.DEFAULT_FROM_EMAIL])
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        admin_emails,
        fail_silently=True,
    )
```

### 커스텀 로그인 뷰

```python
# views.py
from django.contrib.auth.views import LoginView
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomLoginView(LoginView):
    """커스텀 로그인 뷰"""
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        
        # 승인 상태별 메시지 처리
        if user.is_pending():
            messages.warning(
                self.request,
                '아직 관리자 승인이 완료되지 않았습니다. 승인 완료 후 다시 시도해주세요.'
            )
            return redirect('login')
        elif user.is_suspended():
            messages.error(
                self.request,
                '계정이 정지되었습니다. 관리자에게 문의하세요.'
            )
            return redirect('login')
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # 로그인 실패 시 사용자 상태 확인
        username = form.cleaned_data.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                if user.is_pending():
                    messages.warning(
                        self.request,
                        '아직 관리자 승인이 완료되지 않았습니다.'
                    )
                elif user.is_suspended():
                    messages.error(
                        self.request,
                        '계정이 정지되었습니다. 관리자에게 문의하세요.'
                    )
            except User.DoesNotExist:
                pass
        
        return super().form_invalid(form)
```

## 🛡️ 미들웨어로 승인 상태 체크

로그인 후에도 지속적으로 사용자 승인 상태를 확인하는 미들웨어를 구현합니다.

```python
# middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class UserApprovalMiddleware:
    """사용자 승인 상태를 확인하는 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 승인 체크를 제외할 URL 패턴
        self.exempt_urls = [
            reverse('login'),
            reverse('logout'),
            reverse('register'),
            '/admin/',  # 관리자 페이지는 제외
        ]
    
    def __call__(self, request):
        # 로그인된 사용자의 승인 상태 확인
        if (request.user.is_authenticated and 
            not request.user.is_staff and  # 관리자는 제외
            not any(request.path.startswith(url) for url in self.exempt_urls)):
            
            if request.user.is_suspended():
                logout(request)
                messages.error(
                    request,
                    '계정이 정지되었습니다. 관리자에게 문의하세요.'
                )
                return redirect('login')
            
            elif request.user.is_pending():
                logout(request)
                messages.warning(
                    request,
                    '아직 관리자 승인이 완료되지 않았습니다.'
                )
                return redirect('login')
        
        response = self.get_response(request)
        return response
```

```python
# settings.py에 미들웨어 추가
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'your_app.middleware.UserApprovalMiddleware',  # 추가
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

## 🔧 Django Admin 커스터마이징

관리자가 쉽게 사용자 승인을 관리할 수 있도록 Django Admin을 커스터마이징합니다.

```python
# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'approval_status_badge', 'approval_date', 'approved_by',
        'date_joined', 'approval_actions'
    )
    
    list_filter = (
        'approval_status', 'date_joined', 'approval_date',
        'is_staff', 'is_active'
    )
    
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    ordering = ('-date_joined',)
    
    # 기본 필드셋에 승인 관련 필드 추가
    fieldsets = BaseUserAdmin.fieldsets + (
        ('승인 정보', {
            'fields': (
                'approval_status', 'approval_date', 'suspension_date',
                'approval_reason', 'approved_by'
            )
        }),
    )
    
    readonly_fields = ('approval_date', 'suspension_date', 'approved_by')
    
    def approval_status_badge(self, obj):
        """승인 상태를 뱃지로 표시"""
        colors = {
            'pending': '#ffc107',    # 노란색
            'approved': '#28a745',   # 초록색
            'suspended': '#dc3545',  # 빨간색
        }
        color = colors.get(obj.approval_status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_badge.short_description = '승인 상태'
    
    def approval_actions(self, obj):
        """승인 액션 버튼"""
        if obj.is_pending():
            return format_html(
                '<a class="button" href="{}">승인</a> '
                '<a class="button" href="{}">거부</a>',
                f'approve/{obj.pk}/',
                f'suspend/{obj.pk}/'
            )
        elif obj.is_approved():
            return format_html(
                '<a class="button" href="{}">정지</a>',
                f'suspend/{obj.pk}/'
            )
        elif obj.is_suspended():
            return format_html(
                '<a class="button" href="{}">승인</a>',
                f'approve/{obj.pk}/'
            )
        return '-'
    approval_actions.short_description = '액션'
    
    def get_urls(self):
        """커스텀 URL 추가"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'approve/<int:user_id>/',
                self.admin_site.admin_view(self.approve_user),
                name='user_approve',
            ),
            path(
                'suspend/<int:user_id>/',
                self.admin_site.admin_view(self.suspend_user),
                name='user_suspend',
            ),
        ]
        return custom_urls + urls
    
    def approve_user(self, request, user_id):
        """사용자 승인 처리"""
        user = get_object_or_404(User, pk=user_id)
        user.approve(request.user, "관리자에 의한 승인")
        
        # 사용자에게 승인 알림 이메일 발송
        self.send_approval_email(user, approved=True)
        
        messages.success(request, f'{user.username} 사용자가 승인되었습니다.')
        return redirect('../')
    
    def suspend_user(self, request, user_id):
        """사용자 정지 처리"""
        user = get_object_or_404(User, pk=user_id)
        user.suspend(request.user, "관리자에 의한 정지")
        
        # 사용자에게 정지 알림 이메일 발송
        self.send_approval_email(user, approved=False)
        
        messages.warning(request, f'{user.username} 사용자가 정지되었습니다.')
        return redirect('../')
    
    def send_approval_email(self, user, approved=True):
        """승인/정지 알림 이메일 발송"""
        if approved:
            subject = '계정이 승인되었습니다'
            message = f"""
            안녕하세요 {user.get_full_name()}님,
            
            계정 승인이 완료되었습니다.
            이제 로그인하여 서비스를 이용하실 수 있습니다.
            
            감사합니다.
            """
        else:
            subject = '계정이 정지되었습니다'
            message = f"""
            안녕하세요 {user.get_full_name()}님,
            
            계정이 정지되었습니다.
            문의사항이 있으시면 관리자에게 연락해주세요.
            
            감사합니다.
            """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )

# 승인 대기 사용자만 보는 필터 추가
class PendingUsersFilter(admin.SimpleListFilter):
    title = '승인 상태'
    parameter_name = 'approval_filter'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', '승인 대기'),
            ('approved', '승인 완료'),
            ('suspended', '정지'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(approval_status=User.ApprovalStatus.PENDING)
        elif self.value() == 'approved':
            return queryset.filter(approval_status=User.ApprovalStatus.APPROVED)
        elif self.value() == 'suspended':
            return queryset.filter(approval_status=User.ApprovalStatus.SUSPENDED)
        return queryset

# UserAdmin에 필터 추가
UserAdmin.list_filter = UserAdmin.list_filter + (PendingUsersFilter,)
```

## 📧 이메일 알림 시스템

승인 관련 이벤트에 대한 이메일 알림을 구현합니다.

```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

@receiver(post_save, sender=User)
def user_approval_status_changed(sender, instance, created, **kwargs):
    """사용자 승인 상태 변경 시 알림"""
    
    if created and instance.is_pending():
        # 새 사용자 가입 시 관리자에게 알림
        send_new_user_notification(instance)
    
    elif not created:
        # 기존 사용자 상태 변경 시 해당 사용자에게 알림
        if instance.is_approved():
            send_approval_notification(instance)
        elif instance.is_suspended():
            send_suspension_notification(instance)

def send_new_user_notification(user):
    """새 사용자 가입 알림 (관리자에게)"""
    subject = f'새 사용자 승인 요청: {user.username}'
    message = f"""
    새로운 사용자가 가입을 신청했습니다.
    
    사용자명: {user.username}
    이름: {user.get_full_name()}
    이메일: {user.email}
    가입일: {user.date_joined}
    
    관리자 페이지에서 승인 처리해주세요.
    """
    
    admin_emails = getattr(settings, 'ADMIN_EMAILS', [settings.DEFAULT_FROM_EMAIL])
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        admin_emails,
        fail_silently=True,
    )

def send_approval_notification(user):
    """승인 알림 (사용자에게)"""
    subject = '계정이 승인되었습니다'
    message = f"""
    안녕하세요 {user.get_full_name()}님,
    
    계정 승인이 완료되었습니다.
    이제 로그인하여 서비스를 이용하실 수 있습니다.
    
    승인일: {user.approval_date}
    승인자: {user.approved_by}
    
    감사합니다.
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )

def send_suspension_notification(user):
    """정지 알림 (사용자에게)"""
    subject = '계정이 정지되었습니다'
    message = f"""
    안녕하세요 {user.get_full_name()}님,
    
    계정이 정지되었습니다.
    
    정지일: {user.suspension_date}
    정지 사유: {user.approval_reason}
    
    문의사항이 있으시면 관리자에게 연락해주세요.
    
    감사합니다.
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
```

```python
# apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'your_app'
    
    def ready(self):
        import your_app.signals  # 시그널 등록
```

## 🎨 템플릿 구현

### 회원가입 템플릿

```html
<!-- templates/registration/register.html -->
{% extends 'base.html' %}
{% load widget_tweaks %}

{% block title %}회원가입{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3 class="text-center">회원가입</h3>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        
                        <div class="mb-3">
                            <label for="{{ form.username.id_for_label }}" class="form-label">
                                사용자명
                            </label>
                            {{ form.username|add_class:"form-control" }}
                            {% if form.username.errors %}
                                <div class="text-danger">{{ form.username.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.first_name.id_for_label }}" class="form-label">
                                        이름
                                    </label>
                                    {{ form.first_name|add_class:"form-control" }}
                                    {% if form.first_name.errors %}
                                        <div class="text-danger">{{ form.first_name.errors }}</div>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.last_name.id_for_label }}" class="form-label">
                                        성
                                    </label>
                                    {{ form.last_name|add_class:"form-control" }}
                                    {% if form.last_name.errors %}
                                        <div class="text-danger">{{ form.last_name.errors }}</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.email.id_for_label }}" class="form-label">
                                이메일
                            </label>
                            {{ form.email|add_class:"form-control" }}
                            {% if form.email.errors %}
                                <div class="text-danger">{{ form.email.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.password1.id_for_label }}" class="form-label">
                                비밀번호
                            </label>
                            {{ form.password1|add_class:"form-control" }}
                            {% if form.password1.errors %}
                                <div class="text-danger">{{ form.password1.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.password2.id_for_label }}" class="form-label">
                                비밀번호 확인
                            </label>
                            {{ form.password2|add_class:"form-control" }}
                            {% if form.password2.errors %}
                                <div class="text-danger">{{ form.password2.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i>
                            가입 신청 후 관리자 승인을 받아야 로그인이 가능합니다.
                        </div>
                        
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">
                                회원가입 신청
                            </button>
                        </div>
                    </form>
                    
                    <div class="text-center mt-3">
                        <a href="{% url 'login' %}">이미 계정이 있으신가요? 로그인</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 로그인 템플릿

```html
<!-- templates/registration/login.html -->
{% extends 'base.html' %}
{% load widget_tweaks %}

{% block title %}로그인{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h3 class="text-center">로그인</h3>
                </div>
                <div class="card-body">
                    {% if messages %}
                        {% for message in messages %}
                            <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                    
                    <form method="post">
                        {% csrf_token %}
                        
                        <div class="mb-3">
                            <label for="{{ form.username.id_for_label }}" class="form-label">
                                사용자명
                            </label>
                            {{ form.username|add_class:"form-control" }}
                            {% if form.username.errors %}
                                <div class="text-danger">{{ form.username.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.password.id_for_label }}" class="form-label">
                                비밀번호
                            </label>
                            {{ form.password|add_class:"form-control" }}
                            {% if form.password.errors %}
                                <div class="text-danger">{{ form.password.errors }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">
                                로그인
                            </button>
                        </div>
                    </form>
                    
                    <div class="text-center mt-3">
                        <a href="{% url 'register' %}">계정이 없으신가요? 회원가입</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 📊 관리 대시보드 구현

관리자가 사용자 승인 현황을 한눈에 볼 수 있는 대시보드를 구현합니다.

```python
# views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def approval_dashboard(request):
    """승인 관리 대시보드"""
    User = get_user_model()
    
    # 통계 데이터
    stats = {
        'total_users': User.objects.count(),
        'pending_users': User.objects.filter(
            approval_status=User.ApprovalStatus.PENDING
        ).count(),
        'approved_users': User.objects.filter(
            approval_status=User.ApprovalStatus.APPROVED
        ).count(),
        'suspended_users': User.objects.filter(
            approval_status=User.ApprovalStatus.SUSPENDED
        ).count(),
    }
    
    # 최근 가입자 (7일)
    recent_signups = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7)
    ).order_by('-date_joined')[:10]
    
    # 승인 대기 중인 사용자
    pending_users = User.objects.filter(
        approval_status=User.ApprovalStatus.PENDING
    ).order_by('date_joined')
    
    # 월별 가입자 통계
    monthly_stats = User.objects.extra(
        select={'month': "DATE_FORMAT(date_joined, '%%Y-%%m')"}
    ).values('month').annotate(
        total=Count('id'),
        pending=Count('id', filter=Q(approval_status=User.ApprovalStatus.PENDING)),
        approved=Count('id', filter=Q(approval_status=User.ApprovalStatus.APPROVED)),
        suspended=Count('id', filter=Q(approval_status=User.ApprovalStatus.SUSPENDED)),
    ).order_by('-month')[:12]
    
    context = {
        'stats': stats,
        'recent_signups': recent_signups,
        'pending_users': pending_users,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'admin/approval_dashboard.html', context)
```

```html
<!-- templates/admin/approval_dashboard.html -->
{% extends 'admin/base_site.html' %}
{% load humanize %}

{% block title %}사용자 승인 관리 대시보드{% endblock %}

{% block content %}
<div class="dashboard">
    <h1>사용자 승인 관리 대시보드</h1>
    
    <!-- 통계 카드 -->
    <div class="row">
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h5>전체 사용자</h5>
                    <h2>{{ stats.total_users|intcomma }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <h5>승인 대기</h5>
                    <h2>{{ stats.pending_users|intcomma }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5>승인 완료</h5>
                    <h2>{{ stats.approved_users|intcomma }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-danger text-white">
                <div class="card-body">
                    <h5>정지</h5>
                    <h2>{{ stats.suspended_users|intcomma }}</h2>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 승인 대기 사용자 목록 -->
    <div class="row mt-4">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>승인 대기 사용자</h5>
                </div>
                <div class="card-body">
                    {% if pending_users %}
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>사용자명</th>
                                        <th>이름</th>
                                        <th>이메일</th>
                                        <th>가입일</th>
                                        <th>액션</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for user in pending_users %}
                                    <tr>
                                        <td>{{ user.username }}</td>
                                        <td>{{ user.get_full_name }}</td>
                                        <td>{{ user.email }}</td>
                                        <td>{{ user.date_joined|date:"Y-m-d H:i" }}</td>
                                        <td>
                                            <a href="{% url 'admin:user_approve' user.pk %}" 
                                               class="btn btn-sm btn-success">승인</a>
                                            <a href="{% url 'admin:user_suspend' user.pk %}" 
                                               class="btn btn-sm btn-danger">거부</a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    {% else %}
                        <p>승인 대기 중인 사용자가 없습니다.</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- 최근 가입자 -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5>최근 가입자 (7일)</h5>
                </div>
                <div class="card-body">
                    {% if recent_signups %}
                        <ul class="list-group list-group-flush">
                            {% for user in recent_signups %}
                            <li class="list-group-item d-flex justify-content-between">
                                <div>
                                    <strong>{{ user.username }}</strong><br>
                                    <small class="text-muted">{{ user.date_joined|timesince }} ago</small>
                                </div>
                                <span class="badge bg-{{ user.approval_status|yesno:'success,warning,danger' }}">
                                    {{ user.get_approval_status_display }}
                                </span>
                            </li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p>최근 가입자가 없습니다.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 🧪 테스트 코드 작성

사용자 승인 시스템의 테스트 코드를 작성합니다.

```python
# tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail

User = get_user_model()

class UserApprovalSystemTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_user_registration_sets_pending_status(self):
        """회원가입 시 승인대기 상태로 설정되는지 테스트"""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        
        user = User.objects.get(username='testuser')
        self.assertEqual(user.approval_status, User.ApprovalStatus.PENDING)
        self.assertFalse(user.is_active)
    
    def test_pending_user_cannot_login(self):
        """승인대기 사용자는 로그인할 수 없음을 테스트"""
        user = User.objects.create_user(
            username='pendinguser',
            email='pending@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.PENDING
        )
        
        response = self.client.post(reverse('login'), {
            'username': 'pendinguser',
            'password': 'testpass123',
        })
        
        # 로그인이 실패해야 함
        self.assertContains(response, '승인')
    
    def test_approved_user_can_login(self):
        """승인된 사용자는 로그인할 수 있음을 테스트"""
        user = User.objects.create_user(
            username='approveduser',
            email='approved@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.APPROVED,
            is_active=True
        )
        
        response = self.client.post(reverse('login'), {
            'username': 'approveduser',
            'password': 'testpass123',
        })
        
        # 로그인 성공 후 리다이렉트
        self.assertEqual(response.status_code, 302)
    
    def test_suspended_user_cannot_login(self):
        """정지된 사용자는 로그인할 수 없음을 테스트"""
        user = User.objects.create_user(
            username='suspendeduser',
            email='suspended@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.SUSPENDED
        )
        
        response = self.client.post(reverse('login'), {
            'username': 'suspendeduser',
            'password': 'testpass123',
        })
        
        # 로그인이 실패해야 함
        self.assertContains(response, '정지')
    
    def test_user_approval_process(self):
        """사용자 승인 프로세스 테스트"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.PENDING
        )
        
        # 승인 처리
        user.approve(self.admin_user, "승인 테스트")
        
        self.assertEqual(user.approval_status, User.ApprovalStatus.APPROVED)
        self.assertTrue(user.is_active)
        self.assertEqual(user.approved_by, self.admin_user)
        self.assertIsNotNone(user.approval_date)
    
    def test_user_suspension_process(self):
        """사용자 정지 프로세스 테스트"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.APPROVED,
            is_active=True
        )
        
        # 정지 처리
        user.suspend(self.admin_user, "정지 테스트")
        
        self.assertEqual(user.approval_status, User.ApprovalStatus.SUSPENDED)
        self.assertFalse(user.is_active)
        self.assertEqual(user.approved_by, self.admin_user)
        self.assertIsNotNone(user.suspension_date)
    
    def test_email_notification_on_registration(self):
        """회원가입 시 관리자에게 이메일 알림 테스트"""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        
        # 이메일이 발송되었는지 확인
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('새 사용자 승인 요청', mail.outbox[0].subject)
    
    def test_admin_approval_view(self):
        """관리자 승인 뷰 테스트"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            approval_status=User.ApprovalStatus.PENDING
        )
        
        # 관리자로 로그인
        self.client.login(username='admin', password='testpass123')
        
        # 승인 처리
        response = self.client.get(f'/admin/your_app/user/approve/{user.pk}/')
        
        user.refresh_from_db()
        self.assertEqual(user.approval_status, User.ApprovalStatus.APPROVED)
        self.assertEqual(response.status_code, 302)  # 리다이렉트
```

## 🚀 마이그레이션 및 배포

마지막으로 마이그레이션을 생성하고 시스템을 배포합니다.

```bash
# 마이그레이션 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser

# 정적 파일 수집
python manage.py collectstatic
```

## 📝 사용법 정리

### 관리자 워크플로우
1. Django Admin에 로그인
2. 사용자 목록에서 승인 대기 상태 확인
3. 각 사용자별로 승인/거부 결정
4. 필요시 승인된 사용자를 정지 처리

### 사용자 워크플로우
1. 회원가입 폼 작성 제출
2. 승인 대기 메시지 확인
3. 관리자 승인 완료 이메일 수신
4. 로그인하여 서비스 이용

## 🛡️ 보안 고려사항

**추가 보안 강화 방법:**

```python
# 추가 보안 설정
ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # 이메일 인증 필수
LOGIN_ATTEMPT_LIMIT = 5  # 로그인 시도 제한
ACCOUNT_LOCKOUT_TIME = 3600  # 계정 잠금 시간 (초)

# 비밀번호 정책 강화
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

## 🎯 마무리

Django 사용자 승인 시스템을 구현하면서 다음과 같은 핵심 기능들을 완성했습니다:

**✅ 구현된 기능들:**
- 사용자 상태별 관리 (승인대기/승인완료/정지)
- 커스텀 인증 백엔드로 승인된 사용자만 로그인 허용
- Django Admin 커스터마이징으로 쉬운 승인 관리
- 이메일 알림 시스템으로 자동화된 소통
- 미들웨어를 통한 실시간 상태 체크
- 포괄적인 테스트 코드

이 시스템을 통해 관리자는 사용자를 체계적으로 관리할 수 있고, 사용자는 명확한 가입 프로세스를 경험할 수 있습니다. 특히 기업 내부 시스템이나 회원제 서비스에서 유용하게 활용할 수 있는 견고한 기반을 마련했습니다.

**다음 단계로 고려할 사항:**
- 사용자 그룹별 승인 권한 세분화
- 승인 요청 시 추가 정보 수집 폼
- 사용자 활동 로그 및 감사 추적
- API를 통한 승인 시스템 확장

Django의 강력한 인증 시스템과 Admin 인터페이스를 활용하면 이처럼 완성도 높은 사용자 관리 시스템을 구축할 수 있습니다. 여러분의 프로젝트에 맞게 커스터마이징하여 활용해보세요!
