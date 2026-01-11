---
layout: post
title: "앱인토스 게임 등록 완벽 가이드: 게임물관리위원회 등급심사부터 출시까지"
date: 2026-01-10 10:00:00 +0900
categories: [Game Development, Mobile, Toss]
tags: [앱인토스, Apps in Toss, 게임물관리위원회, 게임등급심사, 토스, 미니앱, 게임출시, GRAC]
image: "/assets/img/posts/2026-01-10-apps-in-toss-game-registration-guide.webp"
---

토스의 미니앱 플랫폼인 '앱인토스(Apps in Toss)'에 게임을 등록하고 출시하기 위해서는 게임물관리위원회의 등급심사를 받고 여러 출시 기준을 충족해야 합니다. 이 글에서는 게임 등급심사 신청부터 앱인토스 등록까지 전 과정을 상세히 알아보겠습니다.

## 📋 목차

1. [게임물관리위원회 등급심사란?](#게임물관리위원회-등급심사란)
2. [등급심사 신청 절차](#등급심사-신청-절차)
3. [앱인토스 게임 등록 준비사항](#앱인토스-게임-등록-준비사항)
4. [앱인토스 출시 체크리스트](#앱인토스-출시-체크리스트)
5. [주요 검수 항목 상세](#주요-검수-항목-상세)
6. [출시 후 관리](#출시-후-관리)

## 🎮 게임물관리위원회 등급심사란?

### 등급심사의 필요성

대한민국에서 게임을 서비스하기 위해서는 게임물관리위원회(GRAC: Game Rating and Administration Committee)에서 등급심사를 받아야 합니다. 앱인토스 역시 예외가 아니며, 게임 미니앱 출시 시 등급분류 증명이 필수입니다.

### 게임 등급 분류

- **전체 이용가**: 모든 연령 이용 가능
- **12세 이용가**: 12세 미만 이용 불가
- **15세 이용가**: 15세 미만 이용 불가
- **청소년 이용불가**: 18세 미만 이용 불가

### 등급 결정 요소

- **폭력성**: 게임 내 폭력 표현 수위
- **선정성**: 성적 묘사나 표현의 정도
- **언어의 부적절성**: 욕설, 비속어 사용 여부
- **범죄 및 약물**: 범죄 행위나 약물 관련 표현
- **사행성**: 게임의 사행성 요소 포함 여부

## 📝 등급심사 신청 절차

### 1단계: 게임물관리위원회 회원가입

**공식 홈페이지**: [https://www.grac.or.kr/](https://www.grac.or.kr/)

1. 게임물관리위원회 홈페이지 접속
2. 회원가입 (사업자 등록증 필요)
3. 로그인 후 등급분류 신청 메뉴 선택

### 2단계: 등급분류 신청서 작성

**필요 서류**:
- 사업자 등록증 사본
- 게임 소개서 (게임 내용, 플레이 방식, 스토리 등)
- 게임 화면 캡처본 (주요 장면 10~20장)
- 게임 영상 (게임플레이 전 과정, 10~30분)
- 게임 실행 파일 또는 테스트 계정

**작성 항목**:
```markdown
1. 게임물 기본정보
   - 게임 제목
   - 장르
   - 플랫폼 (모바일 웹)
   - 배급사/개발사 정보

2. 게임 내용 설명
   - 게임 줄거리
   - 게임 방식
   - 주요 캐릭터
   - 특수 기능 (인앱 결제, 광고 등)

3. 등급분류 자가진단
   - 폭력성
   - 선정성
   - 언어의 부적절성
   - 기타 유해 요소
```

### 3단계: 게임 제출 및 심사

**제출 방법**:
- 온라인 제출: 게임 다운로드 링크 제공
- 테스트 환경: 접속 가능한 URL 및 테스트 계정 제공

**심사 기간**:
- 일반 심사: 영업일 기준 5~7일
- 긴급 심사: 추가 비용으로 단축 가능 (1~3일)

**심사 비용** (2026년 기준):
- 소규모 게임물: 약 50,000원~100,000원
- 중대형 게임물: 약 200,000원~500,000원
- 연령등급에 따라 차등 적용

### 4단계: 등급분류 결과 수령

**결과 확인**:
- 게임물관리위원회 홈페이지에서 확인
- 등급분류 결과서 다운로드
- 등급분류번호 부여 (예: CC-NP-123456-789)

**등급표시 의무**:
- 게임 시작 화면에 등급 표시 필수
- 앱인토스 콘솔에 등급분류번호 입력

## 🚀 앱인토스 게임 등록 준비사항

### 1. 콘솔 설정 완료

**필수 사전 작업**:
1. [앱인토스 콘솔](https://console-apps-in-toss.toss.im/) 가입
2. 사업자 인증 완료
3. 대표관리자 신청 승인
4. 앱 정보 등록

**앱 기본 정보 입력**:
```yaml
앱 이름: 게임 제목
카테고리: 게임
연령 등급: 게임물관리위원회에서 받은 등급
등급분류번호: GRAC 등급분류번호
앱 설명: 게임 소개 (100자 이상)
대표 이미지: 512x512px 아이콘
스크린샷: 최소 3장 이상
```

### 2. 연령 등급 정보 입력

앱인토스는 콘솔에 입력한 연령 등급 정보를 기반으로 자동으로 등급 표시를 합니다.

**주의사항**:
- 연령 등급은 미니앱 런칭 환경에서만 노출됩니다
- 샌드박스나 QR 코드 테스트 환경에서는 미표시
- 토스 앱 버전 5.240.0 이상에서 지원

**참고 자료**:
- [게임 등급분류 블로그 아티클](https://toss.im/apps-in-toss/blog/game_rating_classification)
- [게임물관리위원회 문의](https://www.grac.or.kr/)

## ✅ 앱인토스 출시 체크리스트

### 필수 준수 사항

출시 검토에서 반려되지 않으려면 다음 항목들을 반드시 확인해야 합니다.

#### 정책 및 가이드라인
- ✅ [다크패턴 방지 정책](https://developers-apps-in-toss.toss.im/design/consumer-ux-guide.html) 준수
- ✅ [미니앱 브랜딩 가이드](https://developers-apps-in-toss.toss.im/design/miniapp-branding-guide.html) 준수
- ✅ 불법성, 선정성 콘텐츠 배제
- ✅ 자사 앱/웹 유도 금지

### 1. 풀스크린 구현 ⭐

게임의 몰입도 향상을 위해 **모든 게임 미니앱은 풀스크린 필수**입니다.

**구현 요구사항**:
```javascript
// viewport 설정
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">

// 체크리스트
✓ 게임 콘텐츠가 디바이스 전체 화면 점유
✓ 상단/하단 빈 영역 없음
✓ 웹뷰 여백, 반투명 영역 없음
✓ 해상도 저하나 컴포넌트 깨짐 없음
✓ iOS Dynamic Island, 노치, 카메라 홀 고려
✓ 기기 회전 시 레터박스(검은 여백) 미발생
✓ UI 깨짐, 스크롤 오류, 입력 불가 영역 없음
```

### 2. 내비게이션 바 ⭐

**구성 요소**:

| 위치 | 요소 | 필수여부 | 설명 |
|------|------|----------|------|
| 좌측 | 뒤로가기 버튼 | 선택 | 화면별 커스텀 가능 |
| 중앙 | 타이틀 | 선택 | 게임 제목 표시 |
| 우측 | 제휴사 기능 버튼 | 선택 | 모노 아이콘 1개만 가능 |
| 우측 | 더보기 버튼 (⋯) | **필수** | 신고하기, 공유하기 등 |
| 우측 | 닫기 버튼 (X) | **필수** | 게임 종료 |

**종료 확인 모달 필수**:
```javascript
// 종료 확인 모달
{
  title: "게임을 종료할까요?",
  buttons: [
    { text: "취소", style: "default" },
    { text: "종료하기", style: "brand" }
  ]
}
```

**주의사항**:
- X 버튼이 게임 UI와 겹치지 않도록 확인
- 기종별 테스트 필수
- 내비게이션 바 설정: [가이드 문서](https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/NavigationBar.html)

### 3. 사운드 관리

**구현 요구사항**:
```javascript
// 사운드 On/Off 기능 제공
const soundSettings = {
  backgroundMusic: true,
  soundEffects: true,
  haptic: true
};

// 체크리스트
✓ 배경음/효과음 개별 On/Off 가능
✓ 디바이스 무음 모드 연동
✓ 백그라운드 전환 시 사운드 정지
✓ 포그라운드 복귀 시 사운드 재개
```

### 4. 확대/축소 제어

**기본 정책**: 핀치줌(확대/축소) 비활성화

```html
<!-- 핀치줌 막기 -->
<meta name="viewport" content="initial-scale=1, maximum-scale=1, user-scalable=no">
```

**예외**: 틀린 그림 찾기 등 필수 기능인 경우에만 제한적 허용

### 5. 접근성 (Accessibility)

**필수 확인사항**:
- ✅ 텍스트/버튼 명도 대비(contrast) 충분
- ✅ 버튼, 조작 UI 터치 영역 확보 (최소 44x44pt)
- ✅ 화면 전환, 애니메이션 속도 적절 (현기증 방지)
- ✅ 스크린 리더 지원 (VoiceOver, TalkBack)
- ✅ 주요 콘텐츠 읽기 순서 적절

**참고**: [접근성 가이드](https://frontend-fundamentals.com/a11y/)

## 🔍 주요 검수 항목 상세

### 1. 서비스 이용 및 동작

**필수 테스트 항목**:
```markdown
□ 앱 정보의 나이 제한과 서비스 내용 일치
□ 설정된 세로/가로 모드 정상 작동
□ 스크롤과 인터렉션 원활 (응답 시간 2초 이하)
□ 모든 컴포넌트 정상 작동
□ 좌측 스와이프, 안드로이드 뒤로가기 버튼 종료 방지
□ 게임 주요 기능 정상 작동 (스코어, 스테이지 등)
□ 데이터 저장/복원 정상 (기기 변경, 앱 재설치 후)
□ 광고 3회 이상 시청 후 정상 작동
□ 게임 진행 불가 버그 없음
```

### 2. 데이터 및 메모리 사용량 ⚠️

**최적화 필수사항**:

```javascript
// 메모리 누수 방지
function cleanupGame() {
  // 타이머 정리
  clearInterval(gameTimer);
  clearTimeout(animationTimeout);
  
  // 이벤트 리스너 제거
  canvas.removeEventListener('click', handleClick);
  
  // 객체 참조 해제
  gameObjects = null;
  sprites = null;
}

// 리소스 최적화
const optimizationChecklist = [
  '이미지 압축 (WebP 포맷 권장)',
  '영상 스트리밍 활용',
  '해상도 기기별 최적화',
  '불필요한 리소스 지연 로딩',
  '메모리 프로파일링 실시'
];
```

**모니터링 도구**:
- Chrome DevTools (메모리 프로파일러)
- Xcode Instruments
- Android Studio Profiler

### 3. 앱 사용 권한

**권한 관리**:
```javascript
// 필요 권한 명시
const requiredPermissions = {
  camera: false,      // 카메라 (선택)
  microphone: false,  // 마이크 (선택)
  storage: true,      // 저장공간 (게임 데이터)
  notification: true  // 알림 (선택)
};

// 체크리스트
✓ 콘솔에서 권한 확인
✓ 권한 정상 작동 테스트
✓ 권한 미동의 시에도 기본 기능 작동
```

### 4. 보안

**보안 검수사항**:
- ✅ HTTPS 필수 사용
- ✅ 민감 정보 암호화
- ✅ API 키 노출 방지
- ✅ XSS, CSRF 방어
- ✅ 안전한 인증/인가 처리

**반려 사유**: 보안 취약점 발견 시 즉시 반려 (자세한 사유는 이메일/콘솔 확인)

### 5. 인앱 광고 💰

**광고 SDK 연동 시 필수사항**:

```javascript
// 광고 사전 로드 (Preload)
async function preloadAd() {
  try {
    await adSDK.load('your-ad-unit-id');
    console.log('광고 로드 완료');
  } catch (error) {
    console.error('광고 로드 실패:', error);
  }
}

// 광고 표시 및 이벤트 처리
async function showAd() {
  try {
    const result = await adSDK.show();
    
    // 이벤트 핸들링
    if (result.completed) {
      // 리워드 지급
      giveReward();
    } else if (result.skipped) {
      // 중도 종료 - 보상 미지급
      console.log('광고 중도 종료');
    }
    
    // 광고 종료 후 배경음 재개
    resumeBackgroundMusic();
    
  } catch (error) {
    console.error('광고 표시 실패:', error);
  }
}

// 체크리스트
✓ 광고 사전 로드 구현
✓ 리워드 광고 - 완료 시에만 보상 지급
✓ SDK 이벤트 정상 수신
✓ 광고 종료 후 배경음 자동 재개
✓ 화면 정상 복귀 (랜딩)
✓ 테스트 광고 ID 제거 확인
```

### 6. 인앱 결제 💳

**디지털 재화 판매 필수사항**:

```javascript
// 결제 플로우
async function purchaseItem(itemId) {
  try {
    // 1. 배경음 중지
    pauseBackgroundMusic();
    
    // 2. 결제 실행
    const result = await iapSDK.purchase(itemId);
    
    if (result.success) {
      // 3. 아이템 지급
      await giveItem(itemId);
      
      // 4. 결제 내역 저장
      await savePurchaseHistory(result);
      
      showMessage('구매가 완료되었습니다.');
    } else {
      // 결제 실패 처리
      showError(`결제 실패: ${result.error}`);
    }
    
  } catch (error) {
    console.error('결제 오류:', error);
    showError('결제 중 오류가 발생했습니다.');
  }
}

// 체크리스트
✓ 결제 시작 시 배경음 자동 중지
✓ 미니앱 가격 = 스토어(App Store/Play Store) 가격
✓ 결제 완료/실패/취소 정상 처리
✓ 실패 시 명확한 오류 메시지
✓ 결제 내역 확인 화면 제공
✓ 기기 변경/앱 재설치 후 구매 데이터 유지
✓ 구독 상품 미사용 (현재 미지원)
```

### 7. 토스 로그인 🔐

**구현 요구사항**:

```javascript
// 토스 로그인 플로우
async function initTossLogin() {
  try {
    // 1. 인트로 페이지에서 서비스 소개
    showIntroPage();
    
    // 2. 약관 동의 요청
    const consent = await tossLogin.requestConsent({
      termsOfService: 'https://example.com/terms',
      privacyPolicy: 'https://example.com/privacy'
    });
    
    if (consent.agreed) {
      // 3. 로그인 진행
      const user = await tossLogin.login();
      
      // 4. 게임 데이터 로드
      await loadUserData(user.id);
      
      // 5. 게임 시작
      startGame();
    }
    
  } catch (error) {
    console.error('로그인 오류:', error);
  }
}

// 체크리스트
✓ 콘솔 등록 약관 정상 연결
✓ 약관 동의 후 로그인 정상 진행
✓ 로그인 상태 페이지 이동 시 유지
✓ 토스 앱에서 로그인 해제 시 데이터 초기화
✓ 닫기 버튼 동작 적절
  - 인트로 페이지: 미니앱 닫힘
  - 서비스 중간: 이전 화면 복귀
✓ 서비스 가치 이해 후 로그인 요청
```

### 8. 게임 프로필 & 리더보드 🏆

**구현 주의사항**:

```javascript
// 올바른 순서
async function initGame() {
  // 1. 게임 프로필 생성
  await createGameProfile();
  
  // 2. 리더보드 호출 (프로필 생성 후)
  const leaderboard = await getLeaderboard();
}

// 체크리스트
✓ 프로필 생성 전 리더보드 호출 방지
✓ 리더보드 화면 정상 노출
✓ 게임 결과 실시간 반영
```

### 9. 공유 리워드 📤

**친구 초대 기능**:

```javascript
// 공유 리워드 플로우
async function shareAndReward() {
  try {
    // 1. 공유 실행
    const result = await shareSDK.share({
      title: '재미있는 게임 같이 해요!',
      description: '친구 초대하면 보상을 드려요',
      imageUrl: 'https://example.com/share-image.png'
    });
    
    if (result.completed) {
      // 2. 초대자 보상 지급
      await giveReward(result.inviterId);
    } else if (result.canceled) {
      // 3. 취소 시 게임 화면 복귀
      returnToGame();
    }
    
    // 4. 초대 가능 친구 없을 시 UI 미노출
    if (result.noMoreFriends) {
      hideShareButton();
    }
    
  } catch (error) {
    console.error('공유 오류:', error);
  }
}
```

### 10. 프로모션 🎁

**준수사항**:
- ✅ [프로모션 검토 가이드](https://developers-apps-in-toss.toss.im/promotion/console.html) 확인
- ❌ 현금성/환금성 이벤트 금지
- ❌ 게임 아이템→현금화 금지
- ❌ 포인트→토스포인트 전환 금지
- ❌ 사행성/투기성 이벤트 금지

## 🚦 출시 프로세스

### 1단계: 개발 완료
```markdown
✓ 게임 개발 완료
✓ 모든 기능 정상 작동 확인
✓ 디버깅 완료
```

### 2단계: 게임물관리위원회 등급심사
```markdown
✓ GRAC 등급심사 신청
✓ 등급분류 결과 수령
✓ 등급분류번호 확보
```

### 3단계: 앱인토스 콘솔 설정
```markdown
✓ 앱 정보 등록
✓ 등급분류번호 입력
✓ 앱 번들 업로드
✓ 권한 설정
```

### 4단계: 자체 검수
```markdown
✓ 출시 체크리스트 모두 확인
✓ 다양한 기종 테스트
✓ 네트워크 환경 테스트
✓ 메모리/데이터 사용량 확인
```

### 5단계: 앱 출시 검토 신청
```markdown
✓ 콘솔에서 "출시 검토 신청" 클릭
✓ 검수팀 검토 대기 (영업일 5~7일)
```

### 6단계: 검수 결과 확인
```markdown
✓ 승인 → 즉시 출시
✓ 반려 → 사유 확인 후 수정 재신청
```

## 📊 출시 후 관리

### 모니터링 항목

**1. 사용자 지표**:
```yaml
- 일 활성 사용자 (DAU)
- 월 활성 사용자 (MAU)
- 평균 플레이 시간
- 이탈률
- 재방문율
```

**2. 기술 지표**:
```yaml
- 오류율
- 크래시율
- 평균 로딩 시간
- API 응답 시간
- 메모리 사용량
```

**3. 비즈니스 지표**:
```yaml
- 광고 수익 (eCPM)
- 인앱 결제 수익
- 전환율 (CVR)
- 평균 결제 금액 (ARPPU)
```

### 업데이트 프로세스

**버전 업데이트 시**:
```markdown
1. 변경사항 정리
2. 자체 테스트
3. 콘솔에서 새 버전 업로드
4. 업데이트 검토 신청
5. 승인 후 배포
```

**등급 변경 사유 발생 시**:
```markdown
1. GRAC 재심사 신청
2. 새 등급분류번호 발급
3. 앱인토스 콘솔 업데이트
4. 재검수 진행
```

## 💡 출시 성공을 위한 팁

### 1. 철저한 사전 준비
- 출시 체크리스트를 개발 초기부터 고려
- 다양한 기종에서 충분한 테스트
- 메모리 최적화에 특히 신경쓰기

### 2. 빠른 피드백 대응
- 사용자 리뷰 모니터링
- 오류 로그 실시간 체크
- 핫픽스 신속 배포

### 3. 지속적인 개선
- A/B 테스트로 UX 최적화
- 데이터 기반 의사결정
- 정기적인 콘텐츠 업데이트

### 4. 커뮤니케이션
- 사용자 공지사항 적극 활용
- 이벤트로 재방문 유도
- 소셜 미디어 운영

## 📚 참고 자료

### 공식 문서
- [앱인토스 개발자 센터](https://developers-apps-in-toss.toss.im/)
- [게임 출시 가이드](https://developers-apps-in-toss.toss.im/checklist/app-game.html)
- [게임물관리위원회](https://www.grac.or.kr/)
- [게임 등급분류 블로그](https://toss.im/apps-in-toss/blog/game_rating_classification)

### 개발 가이드
- [내비게이션 바 설정](https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/NavigationBar.html)
- [접근성 가이드](https://frontend-fundamentals.com/a11y/)
- [다크패턴 방지 정책](https://developers-apps-in-toss.toss.im/design/consumer-ux-guide.html)
- [미니앱 브랜딩 가이드](https://developers-apps-in-toss.toss.im/design/miniapp-branding-guide.html)

## 🎯 마무리

앱인토스에 게임을 출시하는 과정은 복잡해 보일 수 있지만, 체계적으로 준비하면 충분히 성공적으로 런칭할 수 있습니다.

**핵심 포인트 요약**:

1. **게임물관리위원회 등급심사**는 필수 과정입니다
2. **풀스크린, 내비게이션 바**는 기본 중의 기본입니다
3. **메모리 최적화**는 검수의 핵심 항목입니다
4. **다양한 기종 테스트**는 반려를 막는 가장 확실한 방법입니다
5. **출시 체크리스트**를 하나하나 체크하며 진행하세요

토스의 수많은 사용자에게 여러분의 게임을 선보일 준비가 되셨나요? 이 가이드가 성공적인 앱인토스 게임 출시에 도움이 되길 바랍니다! 🚀

---

**관련 포스트**:
- [토스 미니앱 개발 시작하기](#)
- [앱인토스 인앱 광고 최적화 가이드](#)
- [모바일 게임 성능 최적화 베스트 프랙티스](#)

**문의 및 지원**:
- 앱인토스 개발자 센터: [support@toss.im](mailto:support@toss.im)
- 게임물관리위원회: 1566-5663