---
layout: post
title: "안드로이드 앱 처음 만들어서 구글 플레이스토어에 출시하기 — 2026 완전 가이드"
date: 2026-05-25
categories: [android, mobile]
tags: [android, kotlin, jetpack-compose, google-play, app-publishing]
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-05-25-android-app-google-play-store-beginner-guide.webp"
---

# 안드로이드 앱 처음 만들어서 구글 플레이스토어에 출시하기 — 2026 완전 가이드

"앱 하나 만들어서 플레이스토어에 올려보고 싶은데, 뭐부터 해야 하지?"

이 글은 **안드로이드 앱을 한 번도 만들어 본 적 없는 사람**이 **개발 환경 설치 → 앱 코딩 → 서명 → 스토어 등록 → 심사 통과**까지 한 사이클을 끝내는 데 필요한 모든 과정을 정리합니다. 2026년 기준으로 변경된 정책(클로즈드 테스트 의무화, API 레벨 35 타겟 등)도 반영했습니다.

---

## 전체 로드맵 한눈에 보기

```text
[1] 개발 환경 준비              ← Android Studio 설치, 에뮬레이터 세팅
      ↓
[2] 첫 앱 만들기                ← Kotlin + Jetpack Compose "Hello World"
      ↓
[3] 기능 개발 & 디자인           ← 화면 추가, 데이터 저장, API 연동
      ↓
[4] 릴리즈 빌드 & 앱 서명        ← keystore 생성, AAB 빌드
      ↓
[5] 개발자 계정 등록             ← $25 결제, 신원 인증
      ↓
[6] 스토어 리스팅 작성           ← 스크린샷, 설명, 개인정보처리방침
      ↓
[7] 클로즈드 테스트 (14일)       ← 12명 테스터, 14일 연속 유지
      ↓
[8] 프로덕션 신청 & 심사         ← 3~7 영업일
      ↓
[9] 출시 완료 🎉
```

각 단계를 하나씩 풀어보겠습니다.

---

## 1단계: 개발 환경 준비

### 1.1 Android Studio 설치

Android Studio는 구글이 공식 지원하는 안드로이드 개발 IDE입니다.

1. [developer.android.com/studio](https://developer.android.com/studio)에서 최신 버전 다운로드
2. 설치 마법사를 따라 진행 — **Android SDK**, **Android Emulator**, **Android SDK Build-Tools**가 함께 설치됨
3. 설치 완료 후 **SDK Manager**에서 **Android 15 (API 35)** SDK가 설치되어 있는지 확인

> **PC 사양 참고**: RAM 16GB 이상 권장. 8GB에서도 돌아가지만 에뮬레이터와 IDE를 동시에 띄우면 상당히 느립니다.

### 1.2 에뮬레이터 생성

**Device Manager**(AVD Manager)에서 가상 디바이스를 만듭니다.

1. **Phone → Pixel 8** 등 최신 디바이스 프로필 선택
2. 시스템 이미지: **API 35 (Android 15)** 다운로드 후 선택
3. **Finish** → 재생 버튼으로 부팅 확인

실물 폰이 있다면 USB 케이블 연결 + **개발자 옵션 → USB 디버깅** 활성화로 실기기 테스트도 가능합니다.

---

## 2단계: 첫 앱 만들기 — Hello World

2026년 안드로이드 개발의 표준은 **Kotlin + Jetpack Compose**입니다. 예전처럼 XML 레이아웃을 작성하지 않고, **Kotlin 코드만으로 UI를 선언적으로 구성**합니다.

### 2.1 프로젝트 생성

1. Android Studio → **New Project**
2. 템플릿: **Phone and Tablet → Empty Activity** (Compose 기본 템플릿)
3. 설정:
   - **Name**: `MyFirstApp`
   - **Package name**: `com.yourname.myfirstapp` (나중에 변경 불가하니 신중히)
   - **Language**: Kotlin (유일한 선택지)
   - **Minimum SDK**: API 24 (Android 7.0 — 2026년 기준 전 세계 기기 97%+ 커버)
4. **Finish**

### 2.2 기본 코드 구조

생성된 `MainActivity.kt`를 열면 이런 코드가 있습니다:

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MyFirstAppTheme {
                Greeting("World")
            }
        }
    }
}

@Composable
fun Greeting(name: String) {
    Text(text = "Hello $name!")
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    MyFirstAppTheme {
        Greeting("World")
    }
}
```

**핵심 개념 3가지**:

| 개념 | 설명 |
|------|------|
| `setContent { }` | 액티비티가 표시할 UI를 Compose로 정의하는 진입점 |
| `@Composable` | "이 함수는 UI를 그리는 함수입니다"라는 표시. Compose 함수끼리만 호출 가능 |
| `@Preview` | 에뮬레이터 없이 Android Studio 안에서 미리보기 렌더링 |

▶ 버튼(또는 Shift+F10)을 누르면 에뮬레이터에 "Hello World!"가 표시됩니다.

### 2.3 XML이 없다?

맞습니다. Compose 프로젝트에는 `res/layout/activity_main.xml`이 없습니다. UI 전체를 Kotlin 코드로 작성합니다. 2026년에 새로 시작한다면 **Compose 방식만 배우면 됩니다**. 구글의 공식 문서, 튜토리얼, 최신 라이브러리가 모두 Compose 기준으로 작성되고 있습니다.

---

## 3단계: 기능 개발 — 간단한 앱 예시

"Hello World"에서 한 발짝 나아가, **버튼을 누르면 카운터가 올라가는 앱**을 만들어 봅시다.

```kotlin
@Composable
fun CounterScreen() {
    var count by remember { mutableIntStateOf(0) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "$count",
            fontSize = 64.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = { count++ }) {
            Text("눌러주세요", fontSize = 20.sp)
        }
    }
}
```

**`remember`**: 화면이 다시 그려져도(recomposition) 값을 유지. Compose의 상태 관리 핵심입니다.

### 실전에서 자주 쓰는 추가 기능

| 기능 | 라이브러리 / 방법 |
|------|-------------------|
| 화면 이동(내비게이션) | `androidx.navigation:navigation-compose` |
| 네트워크 API 호출 | `Retrofit` + `kotlinx.serialization` |
| 로컬 데이터 저장 | `Room` (SQLite ORM) 또는 `DataStore` (키-값) |
| 이미지 로딩 | `Coil` (`coil-compose`) |
| 의존성 주입 | `Hilt` 또는 `Koin` |
| 비동기 처리 | Kotlin `Coroutines` + `Flow` |

이 라이브러리들을 하나씩 붙여가며 앱을 키워나갈 수 있습니다.

### 프로젝트 구조 권장 패턴

```text
app/src/main/java/com/yourname/myfirstapp/
├── MainActivity.kt
├── ui/
│   ├── theme/
│   │   ├── Color.kt
│   │   ├── Theme.kt
│   │   └── Type.kt
│   └── screens/
│       ├── HomeScreen.kt
│       └── DetailScreen.kt
├── data/
│   ├── repository/
│   └── model/
└── network/
    └── ApiService.kt
```

---

## 4단계: 릴리즈 빌드 & 앱 서명

개발이 끝나면 구글 플레이에 올릴 **서명된 AAB(Android App Bundle)** 파일을 만들어야 합니다.

### 4.1 Keystore 생성

Keystore는 앱의 **디지털 신분증**입니다. 잃어버리면 그 앱은 영원히 업데이트할 수 없으니 반드시 백업하세요.

**Android Studio에서 생성하는 방법**:
1. **Build → Generate Signed Bundle / APK**
2. **Android App Bundle** 선택 → Next
3. **Create new** → Keystore 정보 입력:
   - **Key store path**: 안전한 위치에 `.jks` 파일 저장
   - **Password**: 강력한 비밀번호
   - **Key alias**: `upload` (권장)
   - **Key password**: keystore 비밀번호와 동일해도 됨
   - **이름, 조직 등**: 아무거나 입력 가능
4. **Next → release** 빌드 타입 선택 → **Create**

**커맨드라인으로 생성하는 방법**:

```bash
keytool -genkey -v -keystore my-release-key.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias upload
```

### 4.2 릴리즈 빌드 설정

`app/build.gradle.kts`에서 릴리즈 빌드 타입을 확인합니다:

```kotlin
android {
    // 2026년 기준 필수: API 35 타겟
    compileSdk = 35

    defaultConfig {
        applicationId = "com.yourname.myfirstapp"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file("path/to/my-release-key.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: ""
            keyAlias = "upload"
            keyPassword = System.getenv("KEY_PASSWORD") ?: ""
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

> **targetSdk = 35 필수**: 2026년 기준, 신규 앱과 업데이트 모두 **Android 15 (API 35)** 이상을 타겟해야 합니다. 이보다 낮으면 Play Console에서 업로드를 거부합니다.

### 4.3 AAB 파일 생성

```bash
./gradlew bundleRelease
```

빌드 성공 시 `app/build/outputs/bundle/release/app-release.aab` 파일이 생성됩니다.

> **AAB vs APK**: 2021년 8월부터 신규 앱은 반드시 **AAB** 형식으로 업로드해야 합니다. AAB를 올리면 구글이 각 기기에 최적화된 APK를 자동 생성해 배포하므로, 앱 용량이 평균 15~20% 줄어듭니다.

### 4.4 Play App Signing

Play Console에 처음 AAB를 업로드하면 **Play App Signing**에 자동 등록됩니다:

- **Upload key** (내가 가진 keystore): AAB를 서명해서 올리는 데 사용
- **App signing key** (구글이 관리): 실제 사용자에게 배포되는 APK를 서명

Upload key를 분실해도 구글에 재설정을 요청할 수 있습니다. 하지만 **keystore 원본은 반드시 별도 백업**하세요.

---

## 5단계: Google Play 개발자 계정 등록

### 5.1 계정 생성

1. [play.google.com/console](https://play.google.com/console) 접속
2. Google 계정으로 로그인
3. **개발자 배포 계약** 동의
4. **등록비 $25** 결제 (일회성, 평생 유효)
5. **계정 유형** 선택:
   - **개인**: 신분증 인증 필요, **클로즈드 테스트 의무**
   - **조직**: 사업자 인증 필요, 클로즈드 테스트 면제

> **중요**: 2023년 11월 13일 이후 생성된 개인 계정은 **클로즈드 테스트 통과 전까지 프로덕션 출시가 불가능**합니다. 이 정책이 개인 개발자에게 가장 큰 허들이 됩니다.

### 5.2 신원 인증

- **개인 계정**: 정부 발급 신분증(주민등록증, 여권 등) + 신용/체크카드
- **조직 계정**: DUNS 번호 또는 사업자 등록 서류
- 인증 처리: 보통 24~48시간

---

## 6단계: 스토어 리스팅 작성

Play Console에서 앱을 생성하면 **대시보드**가 출시 전 필수 항목을 체크리스트로 안내합니다.

### 6.1 필수 텍스트

| 항목 | 규격 | 팁 |
|------|------|-----|
| **앱 이름** | 최대 30자 | 검색 키워드 포함, 간결하게 |
| **짧은 설명** | 최대 80자 | 플레이스토어 검색 결과에 노출 |
| **상세 설명** | 최대 4,000자 | 핵심 기능 → 사용법 → 차별점 순서 |

### 6.2 필수 그래픽 에셋

| 에셋 | 규격 | 비고 |
|------|------|------|
| **앱 아이콘** | 512×512px, PNG 32비트 | `mipmap` 아이콘과 별개 |
| **대표 그래픽** (Feature Graphic) | 1024×500px, JPEG 또는 24비트 PNG (투명 불가) | **필수** — 없으면 출시 불가 |
| **스크린샷** | 최소 2장, 최대 8장 / 기기 유형별 | JPEG 또는 24비트 PNG, 가로·세로 320~3840px |

> **스크린샷 팁**: 에뮬레이터에서 앱 실행 → Android Studio의 **캡처 버튼** (카메라 아이콘)으로 바로 찍을 수 있습니다. Figma나 Canva로 프레임+텍스트 설명을 씌우면 훨씬 전문적으로 보입니다.

### 6.3 필수 설정

| 항목 | 내용 |
|------|------|
| **개인정보처리방침 URL** | 사용자 데이터를 수집하지 않아도 넣어두는 게 안전. GitHub Pages에 간단한 페이지를 만들어 링크 |
| **데이터 안전 섹션** | 앱이 수집하는 데이터 유형·목적·공유 여부 선언 |
| **콘텐츠 등급** | 설문 응답 → 자동 등급 부여 (전체이용가, 12세 등) |
| **타겟 연령** | 아동 대상이 아니면 "13세 이상" 선택이 무난 |
| **광고 포함 여부** | 광고가 있으면 반드시 "포함"으로 선언 |

### 개인정보처리방침 간단히 만들기

앱이 어떤 개인정보도 수집하지 않는다면 아래처럼 한 페이지면 충분합니다:

```markdown
# 개인정보처리방침

본 앱은 사용자의 개인정보를 수집, 저장, 전송하지 않습니다.
문의: your-email@example.com
최종 수정: 2026-05-25
```

GitHub Pages, Notion Public 페이지, Google Sites 등에 올리고 URL을 복사하면 됩니다.

---

## 7단계: 클로즈드 테스트 (개인 계정 필수)

2026년 기준 가장 많은 사람이 막히는 단계입니다.

### 7.1 요구사항

| 조건 | 상세 |
|------|------|
| 테스터 수 | **최소 12명** (과거 20명에서 완화) |
| 테스트 기간 | **14일 연속** |
| 옵트인 상태 | 14일 내내 12명 이상이 **연속으로** 옵트인 유지 |
| 계정 유형 | **2023년 11월 이후 생성된 개인 계정**만 해당 |

### 7.2 진행 순서

**1) AAB 업로드**

Play Console → **Testing → Closed testing** → **Create new track** → 릴리즈 생성 → AAB 업로드

**2) 테스터 목록 등록**

- **이메일 주소 목록**: 테스터들의 Google 계정 이메일을 직접 추가
- 또는 **Google 그룹스** 활용: 그룹 메일을 하나 만들어 등록하면 관리가 편함

**3) 테스트 링크 배포**

테스트 트랙이 활성화되면 **옵트인 URL**이 생성됩니다. 이 링크를 테스터에게 전달하면:
1. 테스터가 링크를 클릭 → "테스터로 참여" 수락
2. 플레이스토어에서 앱 설치 가능해짐
3. 설치 + 실제 사용이 이루어져야 "참여 중"으로 인정

**4) 14일 대기**

Play Console → **Testing → Closed testing → Testers** 탭에서 매일 옵트인 수를 확인합니다.

### 7.3 생존 팁

- **15~18명으로 시작하세요**: 테스터 이탈 버퍼. 12명 딱 맞추면 한 명만 빠져도 카운트 리셋됩니다.
- **테스트 중 빌드를 업데이트하지 마세요**: 새 AAB를 올리면 테스터가 업데이트해야 하고, 이 과정에서 카운트가 흔들릴 수 있습니다.
- **가짜 계정 사용 금지**: 구글은 에뮬레이터 신호, VPN, 최근 생성 계정을 감지해 조용히 제외합니다.
- **주변 지인에게 부탁**: 가족, 친구, 동료에게 "플레이스토어에서 앱 설치하고 14일만 놔둬줘"라고 부탁하는 게 가장 현실적입니다.

> **조직 계정이면 면제**: 사업자등록증이 있다면 조직 계정으로 등록하면 이 단계를 건너뛸 수 있습니다.

---

## 8단계: 프로덕션 신청 & 심사

### 8.1 프로덕션 접근 신청

14일 클로즈드 테스트 완료 후 Play Console 대시보드에 **"Apply for production access"** 버튼이 활성화됩니다.

설문에서 묻는 것들:
- 테스트 중 받은 피드백과 수정 내용
- 앱의 주요 기능 설명
- 프로덕션 준비 상태

### 8.2 릴리즈 생성

**Production → Create new release** → AAB 업로드(테스트 때와 같은 파일 또는 최종 수정본) → 릴리즈 노트 작성 → **Send for review**

### 8.3 심사 기간

| 상황 | 예상 소요 |
|------|-----------|
| 첫 앱 제출 | 3~7 영업일 (최대 2주) |
| 기존 앱 업데이트 | 24~72시간 |
| 민감 카테고리 (금융, 건강, VPN 등) | 최대 2주+ |

### 8.4 흔한 리젝(거부) 사유와 대응

| 사유 | 해결 |
|------|------|
| 개인정보처리방침 URL 누락 | 간단한 페이지라도 반드시 등록 |
| 앱 실행 시 크래시 | 구글이 자동화 테스트를 돌림. 릴리즈 빌드로 직접 테스트 필수 |
| targetSdk가 35 미만 | `build.gradle.kts`에서 `targetSdk = 35` 확인 |
| 권한이 기능과 불일치 | `AndroidManifest.xml`에서 불필요한 권한 제거 |
| 스토어 설명이 실제 앱과 다름 | 스크린샷·설명이 실제 앱 기능을 정확히 반영하도록 |
| 디버그 로그/테스트 코드 잔존 | `isMinifyEnabled = true`로 빌드 + `Log.d()` 정리 |

---

## 9단계: 출시 후 — 이게 끝이 아닙니다

### 9.1 모니터링

Play Console에서 확인할 수 있는 지표:

- **ANR(Application Not Responding) 비율**: 0.47% 이하 유지 권장
- **크래시 비율**: 1.09% 이하 유지 권장
- **사용자 리뷰**: 초기 리뷰는 검색 순위에 큰 영향
- **설치/삭제 추이**: 어디서 유입되는지 파악

### 9.2 업데이트 배포

1. `versionCode` 증가 (1 → 2)
2. `versionName` 변경 ("1.0.0" → "1.1.0")
3. 새 AAB 빌드 → Production에 새 릴리즈 생성 → 심사(24~72시간)

### 9.3 단계적 배포 (Staged Rollout)

처음에 사용자의 20%에게만 배포 → 크래시 없으면 50% → 100%로 늘려갈 수 있습니다. 실수를 해도 전체 사용자가 영향받지 않으므로, **업데이트 시 항상 단계적 배포를 권장**합니다.

---

## 전체 비용 정리

| 항목 | 금액 | 비고 |
|------|------|------|
| Google Play 개발자 등록 | **$25 (일회성)** | 평생 유효, 앱 개수 무제한 |
| Android Studio | 무료 | |
| 에뮬레이터 | 무료 | 실물 폰 없어도 됨 |
| 유료 앱 / 인앱 결제 수수료 | 연 $1M까지 **15%**, 초과분 **30%** | 무료 앱이면 해당 없음 |
| 실물 테스트 기기 | 선택 | 중고 폰이면 5~10만원 |

사실상 **$25만 있으면 시작**할 수 있습니다.

---

## 전체 타임라인 (현실적 추정)

| 단계 | 소요 시간 |
|------|-----------|
| 환경 설치 | 반나절 |
| 간단한 앱 개발 | 1~4주 (복잡도에 따라) |
| 릴리즈 빌드 | 1일 |
| 개발자 계정 인증 | 1~2일 |
| 스토어 리스팅 작성 | 1~2일 |
| 클로즈드 테스트 | **14일** (최소, 카운트 리셋 없을 때) |
| 심사 | 3~7 영업일 |
| **합계** | 약 **5~8주** |

가장 오래 걸리는 건 앱 개발 자체와 14일 클로즈드 테스트입니다. 테스터 확보를 **개발과 병행**하면 시간을 아낄 수 있습니다.

---

## 도움 되는 공식 자료

| 자료 | 링크 |
|------|------|
| Jetpack Compose 공식 튜토리얼 | [developer.android.com/develop/ui/compose/tutorial](https://developer.android.com/develop/ui/compose/tutorial) |
| Compose 샘플 앱 모음 | [github.com/android/compose-samples](https://github.com/android/compose-samples) |
| 앱 서명 가이드 | [developer.android.com/studio/publish/app-signing](https://developer.android.com/studio/publish/app-signing) |
| Play Console 시작 가이드 | [support.google.com/googleplay/android-developer/answer/6112435](https://support.google.com/googleplay/android-developer/answer/6112435) |
| 클로즈드 테스트 요구사항 | [support.google.com/googleplay/android-developer/answer/14151465](https://support.google.com/googleplay/android-developer/answer/14151465) |
| 스토어 리스팅 에셋 가이드 | [support.google.com/googleplay/android-developer/answer/9866151](https://support.google.com/googleplay/android-developer/answer/9866151) |
| API 레벨 요구사항 | [support.google.com/googleplay/android-developer/answer/11926878](https://support.google.com/googleplay/android-developer/answer/11926878) |

---

## 정리

안드로이드 앱을 만들어서 플레이스토어에 올리는 과정은 **생각보다 기술적이지 않습니다**. 진짜 장벽은 코딩이 아니라 **서명 키 관리**, **클로즈드 테스트 14일 기다림**, **스토어 리스팅 꼼꼼히 채우기** 같은 행정적 단계입니다.

순서를 다시 정리하면:

1. Android Studio 설치 → Kotlin + Compose로 앱 제작
2. `targetSdk = 35`, AAB 빌드, keystore **백업 필수**
3. Play Console $25 등록 → 리스팅 작성 (스크린샷, 설명, 개인정보처리방침)
4. 클로즈드 테스트 12명 × 14일 (개인 계정) → 프로덕션 신청
5. 심사 통과 → 출시

한 번 이 사이클을 돌려보면, 두 번째 앱부터는 훨씬 빠르게 진행할 수 있습니다.
