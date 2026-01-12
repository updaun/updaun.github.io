---
layout: post
title: "네이버 지도 API로 맛집 공유 서비스 만들기: API 선택부터 구현까지"
date: 2026-01-12
categories: [Web Development, API]
tags: [네이버 지도, Naver Maps API, 맛집 서비스, Local Search API, Geocoding, Web Service]
---

## 들어가며

맛집을 발견하면 누군가와 공유하고 싶은 마음이 들기 마련입니다. 특히 요즘처럼 SNS가 활성화된 시대에는 맛집 정보가 곧 소중한 콘텐츠가 되었죠. 저도 평소 맛집 탐방을 좋아하는데, 단순히 방문 기록만 남기는 것이 아니라 다른 사람들과 위치 정보를 직관적으로 공유할 수 있는 서비스를 만들고 싶었습니다. 이런 서비스를 만들기 위해서는 지도 표시, 장소 검색, 위치 정보 관리 등 여러 기능이 필요한데, 네이버 지도 API가 이 모든 것을 제공합니다. 이번 글에서는 네이버 지도 API를 활용하여 맛집 공유 서비스를 만드는 과정을 단계별로 살펴보겠습니다.

## 네이버가 제공하는 지도 관련 API 살펴보기

맛집 공유 서비스를 만들기 위해 먼저 네이버가 제공하는 API들을 파악해야 합니다. 네이버는 위치 기반 서비스 개발을 위해 크게 네 가지 핵심 API를 제공합니다. 첫째, **네이버 지도 (Maps) API**는 웹 페이지에 인터랙티브한 지도를 표시하고 마커, 정보창, 도형 등을 그릴 수 있게 해줍니다. 둘째, **Local Search API**는 특정 지역의 음식점, 카페 등 업체 정보를 검색할 수 있는 기능을 제공합니다. 셋째, **Geocoding API**는 주소를 좌표로, 또는 좌표를 주소로 변환해주는 역할을 합니다. 마지막으로 **Directions API**는 두 지점 간의 경로를 계산해줍니다. 맛집 공유 서비스에서는 이 중 지도 표시를 위한 Maps API와 맛집 검색을 위한 Local Search API, 그리고 정확한 위치 표시를 위한 Geocoding API가 핵심적으로 필요합니다.

## 맛집 공유 서비스에 필요한 API 조합

구체적으로 어떤 API를 어떻게 조합해야 할까요? 우선 사용자가 웹 페이지에 접속하면 **Maps API**를 통해 기본 지도를 표시합니다. 이때 사용자의 현재 위치를 중심으로 지도를 보여주면 더 좋겠죠. 다음으로 사용자가 "강남역 맛집"처럼 검색어를 입력하면 **Local Search API**를 호출하여 해당 지역의 음식점 목록을 가져옵니다. 이 API는 업체명, 주소, 전화번호, 카테고리 등의 정보를 JSON 형태로 반환해줍니다. 검색 결과를 받으면 각 맛집의 주소를 **Geocoding API**로 위도/경도 좌표로 변환하고, 이 좌표를 기반으로 지도 위에 마커를 표시합니다. 마커를 클릭하면 정보창이 열려 상세 정보를 보여주고, 사용자는 마음에 드는 맛집을 저장하거나 다른 사람과 공유할 수 있습니다. 이렇게 세 가지 API를 유기적으로 연결하면 완성도 높은 맛집 공유 플랫폼을 만들 수 있습니다.

## 네이버 클라우드 플랫폼에서 API 키 발급받기

API를 사용하려면 먼저 인증 키를 발급받아야 합니다. 네이버 클라우드 플랫폼(NCP) 콘솔에 접속하여 회원가입 후 로그인합니다. 상단 메뉴에서 'Services'를 클릭하고 'AI·NAVER API'에서 'Maps'와 'Search'를 각각 찾아 이용 신청을 합니다. Maps API의 경우 Web Dynamic Map을 선택하고, Search API에서는 Local(지역) 검색을 활성화합니다. 각 API 서비스를 등록하면 Client ID와 Client Secret이 발급되는데, 이 두 값은 API 호출 시 인증에 사용되므로 안전하게 보관해야 합니다. Maps API는 주로 Client ID를 사용하며, Local Search API와 Geocoding API는 HTTP 헤더에 Client ID와 Secret을 포함하여 요청합니다. 무료 플랜의 경우 일일 호출 횟수 제한이 있으므로, 상용 서비스를 운영한다면 적절한 캐싱 전략을 함께 고려해야 합니다.

## 기본 지도 화면 구현하기

이제 본격적으로 코드를 작성해보겠습니다. HTML 파일에 네이버 지도 API를 로드하고 기본 지도를 표시하는 것부터 시작합니다. 먼저 HTML의 head 태그에 Maps API 스크립트를 추가합니다. `<script>` 태그의 src 속성에 네이버 지도 API URL을 넣고, 발급받은 Client ID를 파라미터로 전달합니다. 지도를 표시할 div 요소를 만들고 적절한 높이를 지정합니다. JavaScript에서는 `naver.maps.Map` 객체를 생성하여 div에 지도를 렌더링합니다. 이때 중심 좌표와 줌 레벨을 설정할 수 있습니다. 서울 강남역을 중심으로 한다면 위도 37.498095, 경도 127.027610 정도가 적절합니다. 줌 레벨은 15~17 정도면 주변 상권이 잘 보입니다. 추가로 지도 타입을 설정하거나, 확대/축소 컨트롤을 추가하는 등 다양한 옵션을 적용할 수 있습니다.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>맛집 지도</title>
    <script type="text/javascript" 
            src="https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=YOUR_CLIENT_ID"></script>
    <style>
        #map { width: 100%; height: 600px; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = new naver.maps.Map('map', {
            center: new naver.maps.LatLng(37.498095, 127.027610),
            zoom: 16
        });
    </script>
</body>
</html>
```

## Local Search API로 맛집 검색 기능 구현

지도가 준비되었으니 이제 맛집을 검색하는 기능을 추가합니다. Local Search API는 REST API 방식으로 동작하므로, JavaScript의 fetch 함수나 axios 라이브러리를 사용하여 호출할 수 있습니다. 검색 쿼리는 "강남역 맛집", "서울 이탈리안 레스토랑" 같은 형태로 입력하면 됩니다. API 요청 시 헤더에 `X-Naver-Client-Id`와 `X-Naver-Client-Secret`을 포함해야 합니다. 응답 데이터는 items 배열에 각 업체의 title(상호명), category(카테고리), address(주소), roadAddress(도로명주소), mapx, mapy(좌표) 등이 포함됩니다. 중요한 점은 이 API에서 반환하는 mapx, mapy 좌표가 카텍(KATEC) 좌표계라는 것입니다. 네이버 지도 API는 WGS84 좌표계를 사용하므로, 실제 마커 표시 시에는 좌표 변환이 필요하거나 roadAddress를 Geocoding API로 다시 조회해야 합니다.

```javascript
async function searchRestaurants(query) {
    const url = `https://openapi.naver.com/v1/search/local.json?query=${encodeURIComponent(query)}&display=10`;
    
    try {
        const response = await fetch(url, {
            headers: {
                'X-Naver-Client-Id': 'YOUR_CLIENT_ID',
                'X-Naver-Client-Secret': 'YOUR_CLIENT_SECRET'
            }
        });
        
        const data = await response.json();
        return data.items;
    } catch (error) {
        console.error('검색 오류:', error);
        return [];
    }
}

// 사용 예시
const restaurants = await searchRestaurants('강남역 맛집');
console.log(restaurants);
```

## Geocoding으로 정확한 좌표 얻고 마커 표시하기

Local Search API에서 받은 주소를 정확한 위도/경도로 변환하기 위해 Geocoding API를 사용합니다. 이 API도 REST 방식으로 도로명주소나 지번주소를 query 파라미터로 전달하면, 해당 위치의 WGS84 좌표를 반환합니다. 응답에는 주소 정확도를 나타내는 status와 함께 x(경도), y(위도) 값이 포함됩니다. 좌표를 얻었으면 `naver.maps.Marker`를 생성하여 지도에 표시합니다. 마커 생성 시 position에 좌표를 설정하고, map 속성에 지도 객체를 연결하면 자동으로 표시됩니다. 여러 개의 맛집을 표시할 때는 배열로 마커들을 관리하면 나중에 삭제하거나 업데이트하기 편합니다. 마커 아이콘을 커스터마이징하려면 icon 속성에 이미지 URL과 크기를 지정할 수도 있습니다.

```javascript
async function getCoordinates(address) {
    const url = `https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query=${encodeURIComponent(address)}`;
    
    try {
        const response = await fetch(url, {
            headers: {
                'X-NCP-APIGW-API-KEY-ID': 'YOUR_CLIENT_ID',
                'X-NCP-APIGW-API-KEY': 'YOUR_CLIENT_SECRET'
            }
        });
        
        const data = await response.json();
        if (data.addresses && data.addresses.length > 0) {
            return {
                lat: parseFloat(data.addresses[0].y),
                lng: parseFloat(data.addresses[0].x)
            };
        }
        return null;
    } catch (error) {
        console.error('좌표 변환 오류:', error);
        return null;
    }
}

// 마커 추가 함수
function addMarker(position, title) {
    const marker = new naver.maps.Marker({
        position: new naver.maps.LatLng(position.lat, position.lng),
        map: map,
        title: title
    });
    
    return marker;
}
```

## 정보창으로 맛집 상세 정보 표시하기

마커만 표시하면 어떤 맛집인지 알 수 없으므로, 클릭 시 상세 정보를 보여주는 정보창을 추가합니다. 네이버 지도 API는 `naver.maps.InfoWindow`를 제공하며, HTML 콘텐츠를 자유롭게 구성할 수 있습니다. 정보창에는 업체명, 카테고리, 주소, 전화번호 등을 표시하고, "저장하기" 버튼을 추가하여 사용자가 마음에 드는 맛집을 북마크할 수 있게 만듭니다. 마커에 click 이벤트 리스너를 등록하고, 클릭 시 해당 마커 위치에 정보창을 엽니다. 여러 마커가 있을 때 하나의 정보창을 재사용하는 것이 효율적이므로, 전역으로 InfoWindow 인스턴스를 하나만 만들고 내용만 업데이트하는 방식을 권장합니다. CSS로 정보창을 꾸미면 더 보기 좋은 UI를 만들 수 있습니다.

```javascript
let currentInfoWindow = null;

function createInfoWindow(restaurant) {
    const content = `
        <div style="padding:15px;min-width:200px;">
            <h3 style="margin:0 0 10px 0;">${restaurant.title.replace(/<[^>]*>/g, '')}</h3>
            <p style="margin:5px 0;"><strong>카테고리:</strong> ${restaurant.category}</p>
            <p style="margin:5px 0;"><strong>주소:</strong> ${restaurant.roadAddress || restaurant.address}</p>
            ${restaurant.telephone ? `<p style="margin:5px 0;"><strong>전화:</strong> ${restaurant.telephone}</p>` : ''}
            <button onclick="saveRestaurant('${restaurant.title}')" 
                    style="margin-top:10px;padding:5px 15px;background:#03c75a;color:white;border:none;cursor:pointer;">
                저장하기
            </button>
        </div>
    `;
    
    return new naver.maps.InfoWindow({
        content: content
    });
}

function attachInfoWindow(marker, restaurant) {
    naver.maps.Event.addListener(marker, 'click', function() {
        if (currentInfoWindow) {
            currentInfoWindow.close();
        }
        
        const infoWindow = createInfoWindow(restaurant);
        infoWindow.open(map, marker);
        currentInfoWindow = infoWindow;
    });
}
```

## 전체 통합: 검색부터 마커 표시까지

이제 모든 요소를 하나로 통합하여 완전한 검색 기능을 구현합니다. 사용자가 검색창에 키워드를 입력하고 버튼을 클릭하면, Local Search API로 맛집 목록을 가져오고, 각 맛집의 주소를 Geocoding으로 좌표로 변환한 후, 지도에 마커를 표시하는 전체 플로우를 만듭니다. 기존에 표시된 마커들은 새로운 검색 시 모두 제거하고, 검색 결과에 맞는 새 마커들로 교체합니다. 검색 결과가 여러 개일 때는 모든 마커가 화면에 보이도록 지도의 bounds를 자동으로 조정하면 사용자 경험이 향상됩니다. 에러 처리도 중요한데, API 호출 실패나 좌표 변환 실패 시 사용자에게 적절한 메시지를 보여줘야 합니다.

```javascript
let markers = [];

async function searchAndDisplayRestaurants(query) {
    // 기존 마커 제거
    markers.forEach(marker => marker.setMap(null));
    markers = [];
    
    // 맛집 검색
    const restaurants = await searchRestaurants(query);
    
    if (restaurants.length === 0) {
        alert('검색 결과가 없습니다.');
        return;
    }
    
    // 각 맛집의 좌표를 얻고 마커 생성
    const bounds = new naver.maps.LatLngBounds();
    
    for (const restaurant of restaurants) {
        const address = restaurant.roadAddress || restaurant.address;
        const coords = await getCoordinates(address);
        
        if (coords) {
            const marker = addMarker(coords, restaurant.title);
            attachInfoWindow(marker, restaurant);
            markers.push(marker);
            
            bounds.extend(new naver.maps.LatLng(coords.lat, coords.lng));
        }
    }
    
    // 모든 마커가 보이도록 지도 범위 조정
    if (markers.length > 0) {
        map.fitBounds(bounds);
    }
}

// HTML에서 사용할 검색 함수
function handleSearch() {
    const query = document.getElementById('searchInput').value;
    if (query.trim()) {
        searchAndDisplayRestaurants(query);
    }
}
```

## 사용자 맛집 저장 및 공유 기능 추가

마지막으로 사용자가 마음에 드는 맛집을 저장하고 다른 사람과 공유할 수 있는 기능을 추가합니다. 저장 기능은 localStorage를 활용하여 브라우저에 로컬로 저장하거나, 백엔드 서버와 연동하여 데이터베이스에 저장할 수 있습니다. 간단한 프로토타입이라면 localStorage로 충분하며, 맛집 정보를 JSON 형태로 저장하고 페이지 로드 시 불러와 "내가 저장한 맛집" 목록을 보여줍니다. 공유 기능은 URL에 맛집 정보를 파라미터로 포함시키거나, 카카오톡, 트위터 같은 SNS 공유 API를 활용할 수 있습니다. 특정 맛집의 좌표와 이름을 URL 파라미터로 전달하면, 받는 사람이 링크를 클릭했을 때 바로 해당 위치의 지도가 열리도록 구현할 수 있습니다. 더 나아가 사용자별 맛집 리스트를 관리하고, 평점이나 리뷰를 추가하는 등 소셜 기능을 확장할 수도 있습니다.

```javascript
// 맛집 저장
function saveRestaurant(restaurant) {
    let savedRestaurants = JSON.parse(localStorage.getItem('myRestaurants') || '[]');
    
    // 중복 체크
    const exists = savedRestaurants.some(r => r.title === restaurant.title);
    if (!exists) {
        savedRestaurants.push(restaurant);
        localStorage.setItem('myRestaurants', JSON.stringify(savedRestaurants));
        alert('맛집이 저장되었습니다!');
    } else {
        alert('이미 저장된 맛집입니다.');
    }
}

// 저장된 맛집 불러오기
function loadSavedRestaurants() {
    const saved = JSON.parse(localStorage.getItem('myRestaurants') || '[]');
    return saved;
}

// URL 공유 링크 생성
function generateShareLink(restaurant, coords) {
    const baseUrl = window.location.origin + window.location.pathname;
    const params = new URLSearchParams({
        name: restaurant.title,
        lat: coords.lat,
        lng: coords.lng
    });
    return `${baseUrl}?${params.toString()}`;
}

// 페이지 로드 시 URL 파라미터 확인
window.addEventListener('load', function() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('lat') && params.has('lng')) {
        const lat = parseFloat(params.get('lat'));
        const lng = parseFloat(params.get('lng'));
        const name = params.get('name') || '공유된 맛집';
        
        map.setCenter(new naver.maps.LatLng(lat, lng));
        map.setZoom(17);
        addMarker({lat, lng}, name);
    }
});
```

## 마치며

네이버 지도 API를 활용하면 생각보다 쉽게 위치 기반 서비스를 만들 수 있습니다. 이번 글에서는 맛집 공유 서비스를 예시로 Maps API, Local Search API, Geocoding API를 조합하는 방법을 살펴봤습니다. 핵심은 각 API의 역할을 정확히 이해하고 적재적소에 활용하는 것입니다. Maps API로 시각적인 지도를 제공하고, Local Search로 데이터를 가져오며, Geocoding으로 정확한 위치를 파악하는 3단계 구조를 기억하면 됩니다. 여기서 더 나아가 실시간 위치 추적, 경로 안내, 사용자 리뷰 시스템 등을 추가하면 더욱 풍부한 서비스를 만들 수 있습니다. 네이버 API 문서를 참고하여 다양한 옵션과 기능을 실험해보시기 바랍니다. 여러분만의 독특한 위치 기반 서비스를 만들어보세요!

## 참고 자료

- [네이버 클라우드 플랫폼 - Maps API 문서](https://www.ncloud.com/product/applicationService/maps)
- [네이버 개발자 센터 - Search API 가이드](https://developers.naver.com/docs/serviceapi/search/local/local.md)
- [네이버 클라우드 플랫폼 - Geocoding API](https://api.ncloud-docs.com/docs/ai-naver-mapsgeocoding)
- [네이버 지도 API v3 예제 코드](https://navermaps.github.io/maps.js.ncp/docs/tutorial-digest.example.html)

