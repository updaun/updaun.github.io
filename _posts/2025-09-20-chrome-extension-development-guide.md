---
layout: post
title: "Chrome Extension 개발 완벽 가이드: 기획부터 배포까지"
date: 2025-09-20 14:00:00 +0900
categories: [Web Development, Browser Extension]
tags: [chrome extension, javascript, manifest, web api, browser automation]
description: "Chrome Extension 개발의 전체 과정을 단계별로 설명하는 실무 중심 가이드. 기획부터 개발, 테스트, 배포까지 모든 과정을 다룹니다."
author: "updaun"
image: "/assets/img/posts/2025-09-20-chrome-extension-development-guide.webp"
---

## 개요

Chrome Extension은 브라우저 기능을 확장하여 사용자에게 추가적인 편의성을 제공하는 강력한 도구입니다. 이 포스트에서는 Chrome Extension 개발의 전체 과정을 실무 중심으로 설명하겠습니다.

## 1. Chrome Extension 기본 개념

### 1.1 Extension의 구조

Chrome Extension은 여러 컴포넌트로 구성됩니다:

- **Manifest 파일**: Extension의 메타데이터 정의
- **Background Scripts**: 백그라운드에서 실행되는 스크립트
- **Content Scripts**: 웹페이지에 삽입되는 스크립트
- **Popup**: Extension 아이콘 클릭 시 표시되는 UI
- **Options Page**: 설정 페이지

### 1.2 Manifest 버전

Chrome Extension은 Manifest V2와 V3 두 버전이 있습니다:

- **Manifest V2**: 2023년 이후 지원 중단
- **Manifest V3**: 현재 권장 버전 (2021년 도입)

## 2. 개발 환경 설정

### 2.1 기본 프로젝트 구조

```
chrome-extension/
├── manifest.json
├── background.js
├── content.js
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── options/
│   ├── options.html
│   ├── options.js
│   └── options.css
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── styles/
    └── content.css
```

### 2.2 Manifest.json 작성

```json
{
  "manifest_version": 3,
  "name": "My Chrome Extension",
  "version": "1.0.0",
  "description": "Extension description",
  "permissions": [
    "storage",
    "activeTab",
    "scripting"
  ],
  "host_permissions": [
    "https://*/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://*/*"],
      "js": ["content.js"],
      "css": ["styles/content.css"]
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "options_page": "options/options.html",
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

## 3. 실제 Extension 개발 예시

### 3.1 웹페이지 정보 수집 Extension

웹페이지의 제목과 URL을 수집하는 간단한 Extension을 만들어보겠습니다.

#### Background Script (background.js)

```javascript
// Service Worker로 동작하는 백그라운드 스크립트
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// 탭 업데이트 이벤트 리스너
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    // 페이지 로드 완료 시 처리
    chrome.storage.local.set({
      [`tab_${tabId}`]: {
        title: tab.title,
        url: tab.url,
        timestamp: Date.now()
      }
    });
  }
});

// 메시지 리스너
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageInfo') {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      if (tabs[0]) {
        sendResponse({
          title: tabs[0].title,
          url: tabs[0].url
        });
      }
    });
    return true; // 비동기 응답을 위해 true 반환
  }
});
```

#### Content Script (content.js)

```javascript
// 웹페이지에 삽입되는 스크립트
class PageAnalyzer {
  constructor() {
    this.init();
  }

  init() {
    this.injectStyles();
    this.addEventListeners();
    this.sendPageData();
  }

  injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .extension-highlight {
        background-color: yellow !important;
        border: 2px solid orange !important;
      }
    `;
    document.head.appendChild(style);
  }

  addEventListeners() {
    // 더블클릭으로 요소 하이라이트
    document.addEventListener('dblclick', (e) => {
      e.target.classList.toggle('extension-highlight');
    });

    // 키보드 단축키 (Ctrl+Shift+E)
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'E') {
        this.collectPageInfo();
      }
    });
  }

  sendPageData() {
    const pageData = {
      title: document.title,
      url: window.location.href,
      metaDescription: this.getMetaDescription(),
      headings: this.getHeadings(),
      links: this.getLinks(),
      images: this.getImages()
    };

    chrome.runtime.sendMessage({
      action: 'pageDataCollected',
      data: pageData
    });
  }

  getMetaDescription() {
    const metaDesc = document.querySelector('meta[name="description"]');
    return metaDesc ? metaDesc.content : '';
  }

  getHeadings() {
    const headings = [];
    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
      headings.push({
        tag: h.tagName.toLowerCase(),
        text: h.textContent.trim()
      });
    });
    return headings;
  }

  getLinks() {
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
      links.push({
        href: a.href,
        text: a.textContent.trim()
      });
    });
    return links.slice(0, 50); // 최대 50개만
  }

  getImages() {
    const images = [];
    document.querySelectorAll('img[src]').forEach(img => {
      images.push({
        src: img.src,
        alt: img.alt || ''
      });
    });
    return images.slice(0, 20); // 최대 20개만
  }

  collectPageInfo() {
    const info = {
      pageTitle: document.title,
      selectedText: window.getSelection().toString(),
      pageUrl: window.location.href,
      timestamp: new Date().toISOString()
    };

    chrome.runtime.sendMessage({
      action: 'showNotification',
      data: info
    });
  }
}

// 페이지 로드 시 초기화
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new PageAnalyzer();
  });
} else {
  new PageAnalyzer();
}
```

#### Popup Interface (popup/popup.html)

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>Page Analyzer</h1>
    </header>
    
    <main>
      <section class="page-info">
        <h2>Current Page</h2>
        <div class="info-item">
          <label>Title:</label>
          <span id="pageTitle">Loading...</span>
        </div>
        <div class="info-item">
          <label>URL:</label>
          <span id="pageUrl">Loading...</span>
        </div>
      </section>

      <section class="actions">
        <button id="analyzeBtn" class="btn-primary">Analyze Page</button>
        <button id="exportBtn" class="btn-secondary">Export Data</button>
        <button id="settingsBtn" class="btn-secondary">Settings</button>
      </section>

      <section class="results" id="results" style="display: none;">
        <h2>Analysis Results</h2>
        <div id="resultContent"></div>
      </section>
    </main>
  </div>

  <script src="popup.js"></script>
</body>
</html>
```

#### Popup Script (popup/popup.js)

```javascript
class PopupController {
  constructor() {
    this.init();
  }

  async init() {
    await this.loadPageInfo();
    this.bindEvents();
  }

  async loadPageInfo() {
    try {
      const response = await this.sendMessage({action: 'getPageInfo'});
      
      document.getElementById('pageTitle').textContent = response.title || 'Unknown';
      document.getElementById('pageUrl').textContent = response.url || 'Unknown';
    } catch (error) {
      console.error('Failed to load page info:', error);
    }
  }

  bindEvents() {
    document.getElementById('analyzeBtn').addEventListener('click', () => {
      this.analyzePage();
    });

    document.getElementById('exportBtn').addEventListener('click', () => {
      this.exportData();
    });

    document.getElementById('settingsBtn').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
  }

  async analyzePage() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.textContent = 'Analyzing...';
    analyzeBtn.disabled = true;

    try {
      // Content script에 분석 요청
      const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
      
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: this.injectAnalysisScript
      });

      this.displayResults(results[0].result);
    } catch (error) {
      console.error('Analysis failed:', error);
      this.showError('Analysis failed. Please try again.');
    } finally {
      analyzeBtn.textContent = 'Analyze Page';
      analyzeBtn.disabled = false;
    }
  }

  injectAnalysisScript() {
    // 페이지에서 실행될 분석 스크립트
    return {
      headingCount: document.querySelectorAll('h1, h2, h3, h4, h5, h6').length,
      linkCount: document.querySelectorAll('a[href]').length,
      imageCount: document.querySelectorAll('img').length,
      wordCount: document.body.innerText.split(/\s+/).length,
      hasMetaDescription: !!document.querySelector('meta[name="description"]'),
      title: document.title
    };
  }

  displayResults(data) {
    const resultsSection = document.getElementById('results');
    const resultContent = document.getElementById('resultContent');

    resultContent.innerHTML = `
      <div class="result-item">
        <strong>Headings:</strong> ${data.headingCount}
      </div>
      <div class="result-item">
        <strong>Links:</strong> ${data.linkCount}
      </div>
      <div class="result-item">
        <strong>Images:</strong> ${data.imageCount}
      </div>
      <div class="result-item">
        <strong>Word Count:</strong> ${data.wordCount}
      </div>
      <div class="result-item">
        <strong>Meta Description:</strong> ${data.hasMetaDescription ? 'Yes' : 'No'}
      </div>
    `;

    resultsSection.style.display = 'block';
  }

  async exportData() {
    try {
      const data = await chrome.storage.local.get(null);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json'
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'extension-data.json';
      a.click();
      
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      this.showError('Export failed. Please try again.');
    }
  }

  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.querySelector('.container').appendChild(errorDiv);

    setTimeout(() => {
      errorDiv.remove();
    }, 3000);
  }

  sendMessage(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          resolve(response);
        }
      });
    });
  }
}

// 팝업 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  new PopupController();
});
```

#### Popup Styles (popup/popup.css)

```css
body {
  width: 350px;
  margin: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f5f5f5;
}

.container {
  padding: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px 20px;
  border-radius: 8px 8px 0 0;
}

header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

main {
  padding: 20px;
}

.page-info {
  margin-bottom: 20px;
}

.page-info h2 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.info-item {
  margin-bottom: 8px;
  font-size: 12px;
}

.info-item label {
  font-weight: 600;
  color: #666;
  display: inline-block;
  width: 40px;
}

.info-item span {
  color: #333;
  word-break: break-all;
}

.actions {
  margin-bottom: 20px;
}

.actions button {
  width: 100%;
  margin-bottom: 8px;
  padding: 10px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f8f9fa;
  color: #666;
  border: 1px solid #dee2e6;
}

.btn-secondary:hover {
  background: #e9ecef;
}

.results {
  border-top: 1px solid #eee;
  padding-top: 15px;
}

.results h2 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.result-item {
  margin-bottom: 6px;
  font-size: 12px;
  padding: 4px 0;
}

.result-item strong {
  color: #667eea;
  display: inline-block;
  width: 100px;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 12px;
  border: 1px solid #f5c6cb;
}
```

## 4. 고급 기능 구현

### 4.1 Storage API 활용

```javascript
// 데이터 저장
chrome.storage.sync.set({
  userPreferences: {
    theme: 'dark',
    autoAnalyze: true,
    notifications: false
  }
});

// 데이터 읽기
chrome.storage.sync.get(['userPreferences'], (result) => {
  const prefs = result.userPreferences || {};
  console.log('User preferences:', prefs);
});

// 변경 사항 감지
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'sync' && changes.userPreferences) {
    console.log('Preferences updated:', changes.userPreferences.newValue);
  }
});
```

### 4.2 Context Menu 추가

```javascript
// Background script에서 컨텍스트 메뉴 생성
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'analyzeElement',
    title: 'Analyze Element',
    contexts: ['all']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'analyzeElement') {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: analyzeClickedElement
    });
  }
});

function analyzeClickedElement() {
  const element = document.elementFromPoint(
    window.lastContextMenuX || 0,
    window.lastContextMenuY || 0
  );
  
  if (element) {
    console.log('Element analysis:', {
      tagName: element.tagName,
      className: element.className,
      id: element.id,
      textContent: element.textContent.substring(0, 100)
    });
  }
}
```

### 4.3 웹 요청 가로채기

```javascript
// Background script에서 웹 요청 모니터링
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    console.log('Request intercepted:', details.url);
    
    // 특정 조건에 따라 요청 차단
    if (details.url.includes('blocked-domain.com')) {
      return { cancel: true };
    }
  },
  { urls: ['<all_urls>'] },
  ['blocking']
);

// 응답 헤더 수정
chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    const headers = details.responseHeaders || [];
    
    // CORS 헤더 추가
    headers.push({
      name: 'Access-Control-Allow-Origin',
      value: '*'
    });
    
    return { responseHeaders: headers };
  },
  { urls: ['<all_urls>'] },
  ['blocking', 'responseHeaders']
);
```

## 5. 테스트 및 디버깅

### 5.1 개발자 모드에서 로드

1. Chrome에서 `chrome://extensions/` 접속
2. 개발자 모드 활성화
3. "압축해제된 확장 프로그램을 로드합니다" 클릭
4. Extension 폴더 선택

### 5.2 디버깅 도구

```javascript
// Background script 디버깅
console.log('Background script loaded');

// Popup 디버깅 (Popup 우클릭 > 검사)
console.log('Popup opened');

// Content script 디버깅 (웹페이지 개발자 도구에서 확인)
console.log('Content script injected');

// 에러 처리
chrome.runtime.onError.addListener((error) => {
  console.error('Runtime error:', error);
});
```

### 5.3 자동화된 테스트

```javascript
// Jest를 이용한 유닛 테스트 예시
describe('Extension Utils', () => {
  test('should extract page title correctly', () => {
    document.title = 'Test Page';
    const analyzer = new PageAnalyzer();
    expect(analyzer.getPageTitle()).toBe('Test Page');
  });

  test('should count headings correctly', () => {
    document.body.innerHTML = '<h1>Title</h1><h2>Subtitle</h2>';
    const analyzer = new PageAnalyzer();
    expect(analyzer.getHeadings()).toHaveLength(2);
  });
});

// Puppeteer를 이용한 E2E 테스트
const puppeteer = require('puppeteer');

describe('Extension E2E Tests', () => {
  let browser, page;

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: false,
      args: [
        '--load-extension=./dist',
        '--disable-extensions-except=./dist'
      ]
    });
    page = await browser.newPage();
  });

  test('should open popup correctly', async () => {
    await page.goto('chrome://extensions/');
    // Extension 팝업 테스트 로직
  });

  afterAll(async () => {
    await browser.close();
  });
});
```

## 6. 배포 및 최적화

### 6.1 빌드 프로세스

```javascript
// webpack.config.js
const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
  entry: {
    background: './src/background.js',
    content: './src/content.js',
    popup: './src/popup/popup.js'
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js'
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: 'src/manifest.json', to: 'manifest.json' },
        { from: 'src/popup/popup.html', to: 'popup.html' },
        { from: 'src/icons', to: 'icons' }
      ]
    })
  ],
  optimization: {
    minimize: true
  }
};
```

### 6.2 Chrome Web Store 등록

1. **개발자 등록**
   - Chrome Web Store Developer Dashboard 접속
   - $5 등록비 결제

2. **Extension 패키징**
   ```bash
   # Chrome에서 "확장 프로그램 패키징" 사용
   # 또는 command line 도구 사용
   chrome --pack-extension=/path/to/extension
   ```

3. **Store 등록 정보 작성**
   - 설명, 스크린샷, 카테고리 등
   - 개인정보 보호정책 (필수)
   - 권한 사용 정당성 설명

### 6.3 성능 최적화

```javascript
// 메모리 사용량 최적화
class MemoryOptimizedExtension {
  constructor() {
    this.cache = new Map();
    this.maxCacheSize = 100;
  }

  addToCache(key, value) {
    if (this.cache.size >= this.maxCacheSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  // 이벤트 리스너 정리
  cleanup() {
    document.removeEventListener('click', this.handleClick);
    this.cache.clear();
  }
}

// Lazy loading 구현
class LazyLoader {
  static async loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  static async loadOnDemand(feature) {
    switch (feature) {
      case 'analytics':
        await this.loadScript('/scripts/analytics.js');
        break;
      case 'export':
        await this.loadScript('/scripts/export.js');
        break;
    }
  }
}
```

## 7. 보안 고려사항

### 7.1 CSP (Content Security Policy)

```json
{
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'"
  }
}
```

### 7.2 권한 최소화

```javascript
// 필요한 권한만 요청
{
  "permissions": [
    "activeTab"  // 모든 탭 대신 활성 탭만
  ],
  "host_permissions": [
    "https://specific-domain.com/*"  // 모든 사이트 대신 특정 도메인만
  ]
}

// 동적 권한 요청
chrome.permissions.request({
  permissions: ['downloads'],
  origins: ['https://example.com/*']
}, (granted) => {
  if (granted) {
    // 권한 승인됨
  }
});
```

### 7.3 데이터 검증

```javascript
// 입력 데이터 검증
function validateInput(input) {
  if (typeof input !== 'string') {
    throw new Error('Invalid input type');
  }
  
  if (input.length > 1000) {
    throw new Error('Input too long');
  }
  
  // XSS 방지를 위한 HTML 이스케이프
  return input.replace(/[<>'"&]/g, (char) => {
    const escapeMap = {
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '&': '&amp;'
    };
    return escapeMap[char];
  });
}

// 메시지 검증
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 발신자 검증
  if (!sender.tab || !sender.tab.url.startsWith('https://')) {
    return;
  }
  
  // 메시지 구조 검증
  if (!message.action || typeof message.action !== 'string') {
    return;
  }
  
  // 처리...
});
```

## 8. 유지보수 및 업데이트

### 8.1 버전 관리

```javascript
// 업데이트 감지 및 처리
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'update') {
    const currentVersion = chrome.runtime.getManifest().version;
    console.log('Extension updated to version:', currentVersion);
    
    // 마이그레이션 로직
    migrateData(details.previousVersion, currentVersion);
  }
});

async function migrateData(oldVersion, newVersion) {
  if (compareVersions(oldVersion, '2.0.0') < 0) {
    // 2.0.0 이전 버전에서 업그레이드된 경우
    const oldData = await chrome.storage.local.get('oldFormat');
    if (oldData.oldFormat) {
      const newData = convertToNewFormat(oldData.oldFormat);
      await chrome.storage.local.set({ newFormat: newData });
      await chrome.storage.local.remove('oldFormat');
    }
  }
}
```

### 8.2 에러 리포팅

```javascript
// 중앙화된 에러 처리
class ErrorReporter {
  static report(error, context = {}) {
    const errorData = {
      message: error.message,
      stack: error.stack,
      context: context,
      timestamp: new Date().toISOString(),
      version: chrome.runtime.getManifest().version,
      userAgent: navigator.userAgent
    };

    // 로컬 저장 (개발 중)
    console.error('Extension Error:', errorData);
    
    // 프로덕션에서는 서버로 전송
    if (this.isProduction()) {
      this.sendToServer(errorData);
    }
  }

  static isProduction() {
    return !chrome.runtime.getManifest().update_url.includes('localhost');
  }

  static async sendToServer(errorData) {
    try {
      await fetch('https://api.example.com/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(errorData)
      });
    } catch (e) {
      console.error('Failed to report error:', e);
    }
  }
}

// 전역 에러 핸들러
window.addEventListener('error', (event) => {
  ErrorReporter.report(event.error, {
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno
  });
});
```

## 9. 성능 모니터링

### 9.1 메트릭 수집

```javascript
class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.startTimes = {};
  }

  startTimer(name) {
    this.startTimes[name] = performance.now();
  }

  endTimer(name) {
    if (this.startTimes[name]) {
      const duration = performance.now() - this.startTimes[name];
      this.metrics[name] = (this.metrics[name] || []).concat(duration);
      delete this.startTimes[name];
      return duration;
    }
  }

  getAverageTime(name) {
    const times = this.metrics[name] || [];
    return times.length > 0 ? times.reduce((a, b) => a + b) / times.length : 0;
  }

  getMemoryUsage() {
    if (performance.memory) {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      };
    }
    return null;
  }

  collectMetrics() {
    return {
      performance: this.metrics,
      memory: this.getMemoryUsage(),
      timestamp: Date.now()
    };
  }
}

// 사용 예시
const monitor = new PerformanceMonitor();

// 페이지 분석 시간 측정
monitor.startTimer('pageAnalysis');
await analyzePage();
const analysisTime = monitor.endTimer('pageAnalysis');

console.log('Analysis completed in:', analysisTime, 'ms');
```

## 결론

Chrome Extension 개발은 웹 개발 기술을 활용하여 브라우저 기능을 확장하는 강력한 방법입니다. 이 가이드에서 다룬 내용들을 바탕으로:

1. **기본 구조 이해**: Manifest, Background Script, Content Script의 역할
2. **실제 구현**: 단계별 개발 과정과 코드 예시
3. **고급 기능**: Storage, Context Menu, Web Request API 활용
4. **테스트**: 디버깅과 자동화된 테스트 방법
5. **배포**: Chrome Web Store 등록 과정
6. **최적화**: 성능과 보안 고려사항
7. **유지보수**: 버전 관리와 에러 처리

성공적인 Extension 개발을 위해서는 사용자 경험을 최우선으로 고려하고, 필요한 권한만 요청하며, 성능과 보안을 지속적으로 모니터링하는 것이 중요합니다.

Extension 개발은 웹 생태계에 가치를 더하는 의미있는 작업입니다. 이 가이드가 여러분의 Extension 개발 여정에 도움이 되기를 바랍니다.