#!/usr/bin/env python3
"""
포스트 키워드 기반 자동 썸네일 생성기

이 스크립트는 블로그 포스트의 카테고리, 태그, 제목을 분석하여
관련된 키워드를 추출하고, 해당 키워드로 Unsplash에서 이미지를 검색하여
자동으로 썸네일을 생성합니다.
"""

import os
import re
import requests
import yaml
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib


class AutoThumbnailGenerator:
    """포스트 키워드 기반 자동 썸네일 생성기"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.posts_dir = self.workspace_path / "_posts"
        self.images_dir = self.workspace_path / "assets" / "img" / "posts"
        self.cache_dir = self.workspace_path / ".thumbnail_cache"
        
        # 디렉토리 생성
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 캐시 파일 경로
        self.cache_file = self.cache_dir / "keyword_cache.json"
        self.image_cache_file = self.cache_dir / "image_cache.json"
        
        # 키워드 매핑 로드
        self.keyword_mapping = self._load_keyword_mapping()
        
        # 이미지 캐시 로드
        self.image_cache = self._load_image_cache()
        
        # 색상 팔레트
        self.color_schemes = {
            'aws': {
                'primary': '#232F3E',
                'secondary': '#FF9900', 
                'accent': '#4A90E2',
                'text': '#FFFFFF',
                'gradient': ['#232F3E', '#1A252F']
            },
            'python': {
                'primary': '#1E3A8A',
                'secondary': '#FFD43B',
                'accent': '#306998', 
                'text': '#FFFFFF',
                'gradient': ['#1E3A8A', '#3B82F6']
            },
            'django': {
                'primary': '#0C4B33',
                'secondary': '#44B78B',
                'accent': '#092A1C',
                'text': '#FFFFFF', 
                'gradient': ['#0C4B33', '#44B78B']
            },
            'ai': {
                'primary': '#0C0A09',
                'secondary': '#A855F7',
                'accent': '#06B6D4',
                'text': '#FFFFFF',
                'gradient': ['#0C0A09', '#1F1B24']
            },
            'firebase': {
                'primary': '#1A1A1A',
                'secondary': '#FFCB2B', 
                'accent': '#FF6B35',
                'text': '#FFFFFF',
                'gradient': ['#1A1A1A', '#2D2D2D']
            },
            'opencv': {
                'primary': '#0F172A',
                'secondary': '#22C55E',
                'accent': '#3B82F6',
                'text': '#FFFFFF',
                'gradient': ['#0F172A', '#1E293B']
            },
            'default': {
                'primary': '#1F2937',
                'secondary': '#3B82F6',
                'accent': '#10B981',
                'text': '#FFFFFF',
                'gradient': ['#1F2937', '#374151']
            }
        }

    def _load_keyword_mapping(self) -> Dict:
        """키워드 매핑 로드 또는 생성"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 캐시 파일 로드 실패: {e}")
        
        return self._create_default_keyword_mapping()

    def _load_image_cache(self) -> Dict:
        """이미지 캐시 로드"""
        if self.image_cache_file.exists():
            try:
                with open(self.image_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 이미지 캐시 파일 로드 실패: {e}")
        
        return {}

    def _save_caches(self):
        """캐시 파일들 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.keyword_mapping, f, ensure_ascii=False, indent=2)
            
            with open(self.image_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.image_cache, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 캐시 저장 실패: {e}")

    def _create_default_keyword_mapping(self) -> Dict:
        """기본 키워드 매핑 생성"""
        return {
            # AWS 관련
            'aws': ['cloud computing', 'amazon web services', 'server infrastructure', 'cloud architecture'],
            'ec2': ['virtual machines', 'cloud servers', 'compute instances', 'server hosting'],
            's3': ['cloud storage', 'data backup', 'file storage', 'digital archives'],
            'lambda': ['serverless', 'cloud functions', 'microservices', 'automation'],
            'rds': ['database', 'cloud database', 'data management', 'sql servers'],
            'vpc': ['network security', 'cloud networking', 'private cloud', 'network infrastructure'],
            
            # Python/Django 관련  
            'python': ['programming', 'coding', 'software development', 'computer programming'],
            'django': ['web development', 'backend programming', 'web framework', 'server development'],
            'flask': ['web development', 'microframework', 'api development', 'python web'],
            'fastapi': ['api development', 'modern web', 'async programming', 'high performance'],
            'ninja': ['api framework', 'fast development', 'modern programming', 'web api'],
            
            # AI/ML 관련
            'ai': ['artificial intelligence', 'machine learning', 'neural networks', 'deep learning'],
            'yolo': ['computer vision', 'object detection', 'image recognition', 'ai vision'],
            'opencv': ['computer vision', 'image processing', 'video analysis', 'visual computing'],
            'tensorflow': ['machine learning', 'deep learning', 'neural networks', 'ai development'],
            'pytorch': ['deep learning', 'machine learning', 'neural networks', 'ai research'],
            
            # 웹 개발
            'javascript': ['web development', 'frontend programming', 'interactive web', 'coding'],
            'react': ['frontend development', 'user interface', 'web components', 'modern web'],
            'vue': ['frontend framework', 'user interface', 'web development', 'javascript'],
            'nextjs': ['full stack', 'react framework', 'modern web', 'web development'],
            
            # 데이터베이스
            'mongodb': ['database', 'nosql', 'document database', 'data storage'],
            'postgresql': ['database', 'sql', 'relational database', 'data management'],
            'mysql': ['database', 'sql server', 'data management', 'web database'],
            'redis': ['caching', 'in-memory database', 'performance', 'data structure'],
            
            # DevOps/도구
            'docker': ['containerization', 'devops', 'deployment', 'software containers'],
            'kubernetes': ['container orchestration', 'devops', 'cloud native', 'microservices'],
            'git': ['version control', 'collaboration', 'code management', 'development tools'],
            'cicd': ['automation', 'devops', 'continuous integration', 'deployment pipeline'],
            
            # 기타 기술
            'api': ['software integration', 'web services', 'data exchange', 'programming interfaces'],
            'testing': ['software testing', 'quality assurance', 'code validation', 'debugging'],
            'performance': ['optimization', 'speed improvement', 'efficiency', 'system performance'],
            'security': ['cybersecurity', 'data protection', 'secure coding', 'system security'],
            'async': ['concurrent programming', 'parallel processing', 'performance optimization', 'modern programming'],
            'tdd': ['test driven development', 'software testing', 'code quality', 'agile development'],
            
            # 일반적인 프로그래밍 개념
            'architecture': ['software architecture', 'system design', 'technical blueprint', 'engineering'],
            'optimization': ['performance tuning', 'efficiency improvement', 'speed optimization', 'resource management'],
            'guide': ['tutorial', 'learning', 'education', 'instruction manual'],
            'analysis': ['data analysis', 'research', 'investigation', 'examination'],
            
            # 한글 키워드 매핑
            '가이드': ['tutorial', 'learning', 'education', 'instruction manual'],
            '분석': ['data analysis', 'research', 'investigation', 'examination'],
            '최적화': ['performance tuning', 'efficiency improvement', 'speed optimization'],
            '아키텍처': ['software architecture', 'system design', 'technical blueprint'],
            '성능': ['performance', 'optimization', 'speed', 'efficiency'],
            '보안': ['cybersecurity', 'data protection', 'secure coding', 'system security'],
            '데이터베이스': ['database', 'data management', 'sql', 'storage'],
            '웹개발': ['web development', 'frontend', 'backend', 'full stack'],
            '머신러닝': ['machine learning', 'artificial intelligence', 'neural networks'],
            '딥러닝': ['deep learning', 'neural networks', 'ai', 'machine learning'],
            '컴퓨터비전': ['computer vision', 'image processing', 'object detection'],
            '클라우드': ['cloud computing', 'aws', 'server infrastructure'],
            '서버리스': ['serverless', 'cloud functions', 'microservices'],
            '마이크로서비스': ['microservices', 'distributed systems', 'api'],
            '컨테이너': ['containerization', 'docker', 'kubernetes'],
            '데브옵스': ['devops', 'automation', 'deployment', 'ci/cd'],
            '테스트': ['software testing', 'quality assurance', 'tdd'],
            '리팩토링': ['code refactoring', 'code improvement', 'clean code'],
            '알고리즘': ['algorithms', 'data structures', 'computer science'],
            '자료구조': ['data structures', 'algorithms', 'programming'],
            '프레임워크': ['framework', 'development tools', 'programming'],
            '라이브러리': ['library', 'programming tools', 'software development'],
            '백엔드': ['backend development', 'server programming', 'api development'],
            '프론트엔드': ['frontend development', 'user interface', 'web design'],
            '풀스택': ['full stack development', 'web development', 'programming'],
            '모바일': ['mobile development', 'app development', 'mobile apps'],
            '게임개발': ['game development', 'game programming', 'interactive media'],
            '블록체인': ['blockchain', 'cryptocurrency', 'distributed ledger'],
            '빅데이터': ['big data', 'data analytics', 'data science'],
            '인공지능': ['artificial intelligence', 'machine learning', 'neural networks']
        }

    def extract_post_metadata(self, post_path: Path) -> Dict:
        """포스트 파일에서 메타데이터 추출"""
        try:
            with open(post_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAML front matter 추출
            yaml_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
            if not yaml_match:
                return {}
            
            # YAML 파싱
            yaml_content = yaml_match.group(1)
            metadata = yaml.safe_load(yaml_content)
            
            # 본문에서 주요 키워드 추출 (제한적으로)
            body_content = content[yaml_match.end():]
            body_keywords = self._extract_keywords_from_content(body_content)
            
            metadata['body_keywords'] = body_keywords
            return metadata
            
        except Exception as e:
            print(f"❌ 메타데이터 추출 실패 ({post_path}): {e}")
            return {}

    def _extract_keywords_from_content(self, content: str, max_keywords: int = 10) -> List[str]:
        """본문에서 주요 키워드 추출"""
        # 기술 용어 패턴
        tech_patterns = [
            r'\b(AWS|EC2|S3|Lambda|RDS|VPC|CloudFormation|API Gateway)\b',
            r'\b(Python|Django|Flask|FastAPI|JavaScript|React|Vue|Node\.js)\b',
            r'\b(MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch)\b',
            r'\b(Docker|Kubernetes|Git|CI/CD|DevOps)\b',
            r'\b(AI|ML|YOLO|OpenCV|TensorFlow|PyTorch)\b',
            r'\b(API|REST|GraphQL|gRPC|WebSocket)\b'
        ]
        
        keywords = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            keywords.extend([match.lower() for match in matches])
        
        # 중복 제거 및 빈도순 정렬
        keyword_counts = {}
        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:max_keywords]]

    def generate_search_keywords(self, metadata: Dict) -> List[str]:
        """메타데이터에서 검색 키워드 생성"""
        keywords = set()
        
        # 카테고리에서 키워드 추출
        categories = metadata.get('categories', [])
        if isinstance(categories, str):
            categories = [categories]
        
        for category in categories:
            category_lower = category.lower()
            keywords.add(category_lower)
            
            # 매핑된 키워드 추가
            if category_lower in self.keyword_mapping:
                keywords.update(self.keyword_mapping[category_lower])
        
        # 태그에서 키워드 추출
        tags = metadata.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
            
        for tag in tags:
            tag_lower = tag.lower().replace('-', ' ')
            keywords.add(tag_lower)
            
            # 매핑된 키워드 추가
            tag_key = tag_lower.replace(' ', '').replace('-', '')
            if tag_key in self.keyword_mapping:
                keywords.update(self.keyword_mapping[tag_key])
        
        # 제목에서 주요 기술 용어 추출
        title = metadata.get('title', '')
        title_keywords = self._extract_keywords_from_content(title)
        for kw in title_keywords:
            keywords.add(kw)
            if kw in self.keyword_mapping:
                keywords.update(self.keyword_mapping[kw])
        
        # 본문 키워드 추가
        body_keywords = metadata.get('body_keywords', [])
        for kw in body_keywords:
            keywords.add(kw)
            if kw in self.keyword_mapping:
                keywords.update(self.keyword_mapping[kw])
        
        # 키워드 우선순위 정렬
        keyword_list = list(keywords)
        
        # 기술 관련 키워드 우선
        tech_keywords = [kw for kw in keyword_list if any(tech in kw.lower() for tech in 
                        ['programming', 'development', 'software', 'computer', 'technology', 
                         'coding', 'api', 'database', 'cloud', 'server', 'web'])]
        
        other_keywords = [kw for kw in keyword_list if kw not in tech_keywords]
        
        return tech_keywords[:5] + other_keywords[:3]  # 최대 8개 키워드

    def search_unsplash_images(self, keywords: List[str], count: int = 5) -> List[Dict]:
        """Unsplash에서 이미지 검색 (무료 API 사용)"""
        images = []
        
        for keyword in keywords[:3]:  # 처음 3개 키워드만 사용
            cache_key = f"unsplash_{hashlib.md5(keyword.encode()).hexdigest()}"
            
            # 캐시 확인
            if cache_key in self.image_cache:
                cached_data = self.image_cache[cache_key]
                if time.time() - cached_data['timestamp'] < 86400:  # 24시간 캐시
                    images.extend(cached_data['images'][:2])
                    continue
            
            try:
                # Unsplash 무료 API 엔드포인트 (rate limited)
                url = f"https://source.unsplash.com/1200x630/?{keyword.replace(' ', ',')}"
                
                # 간단한 메타데이터 생성
                image_info = {
                    'url': url,
                    'keyword': keyword,
                    'width': 1200,
                    'height': 630,
                    'description': f"Image for {keyword}"
                }
                
                images.append(image_info)
                
                # 캐시 저장
                self.image_cache[cache_key] = {
                    'images': [image_info],
                    'timestamp': time.time()
                }
                
                # API 호출 제한을 위한 대기
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Unsplash 검색 실패 ({keyword}): {e}")
                continue
            
            if len(images) >= count:
                break
        
        return images[:count]

    def download_and_process_image(self, image_info: Dict, output_path: Path, 
                                 metadata: Dict) -> bool:
        """이미지 다운로드 및 처리"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(image_info['url'], headers=headers, timeout=30)
            response.raise_for_status()
            
            # 이미지 열기
            img = Image.open(io.BytesIO(response.content))
            
            # RGB로 변환
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 크기 조정 (1200x630)
            img = self._resize_and_crop(img, (1200, 630))
            
            # 오버레이 추가
            img = self._add_overlay(img, metadata)
            
            # WebP로 저장
            img.save(output_path, 'WEBP', quality=85, optimize=True)
            print(f"✅ 이미지 처리 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 이미지 다운로드/처리 실패: {e}")
            return False

    def _resize_and_crop(self, img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """이미지 크기 조정 및 크롭"""
        img_ratio = img.width / img.height
        target_ratio = size[0] / size[1]
        
        if img_ratio > target_ratio:
            # 이미지가 더 넓음
            new_height = size[1]
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - size[0]) // 2
            img = img.crop((left, 0, left + size[0], size[1]))
        else:
            # 이미지가 더 높음
            new_width = size[0]
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - size[1]) // 2
            img = img.crop((0, top, size[0], top + size[1]))
        
        return img

    def _add_overlay(self, img: Image.Image, metadata: Dict) -> Image.Image:
        """이미지에 텍스트 오버레이 추가"""
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 색상 스키마 선택
        scheme = self._select_color_scheme(metadata)
        
        # 제목 추출
        title = metadata.get('title', '블로그 포스트')
        if len(title) > 60:
            title = title[:57] + "..."
        
        # 하단 그라데이션 배경
        gradient_height = 200
        for i in range(gradient_height):
            alpha = int(150 * (i / gradient_height))
            y = img.height - gradient_height + i
            color = tuple(list(self._hex_to_rgb(scheme['primary'])) + [alpha])
            draw.line([(0, y), (img.width, y)], fill=color)
        
        # 한글 지원 폰트 로드 시도
        try:
            # macOS 한글 폰트들
            title_font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 42)
            category_font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 24)
        except:
            try:
                # 대체 한글 폰트
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
                category_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                try:
                    # NanumGothic (많이 사용되는 한글 폰트)
                    title_font = ImageFont.truetype("/System/Library/Fonts/NanumGothic.ttc", 42)
                    category_font = ImageFont.truetype("/System/Library/Fonts/NanumGothic.ttc", 24)
                except:
                    try:
                        # Windows 한글 폰트
                        title_font = ImageFont.truetype("malgun.ttf", 42)
                        category_font = ImageFont.truetype("malgun.ttf", 24)
                    except:
                        # 기본 폰트 (한글 지원 제한적)
                        title_font = ImageFont.load_default()
                        category_font = ImageFont.load_default()
        
        # 제목 텍스트 (여러 줄 처리)
        lines = self._wrap_text(title, title_font, img.width - 100)
        
        total_text_height = len(lines) * 50
        start_y = img.height - 160 - (len(lines) - 1) * 25  # 줄 수에 따라 시작 위치 조정
        
        for i, line in enumerate(lines):
            try:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(line) * 20  # 근사치
            
            x = 50
            y = start_y + i * 50
            
            # 더 부드러운 텍스트 그림자 (여러 레이어)
            for offset in [(3, 3), (2, 2), (1, 1)]:
                shadow_alpha = 100 - (offset[0] * 20)
                draw.text((x + offset[0], y + offset[1]), line, font=title_font, 
                         fill=(0, 0, 0, shadow_alpha))
            
            # 메인 텍스트 (더 선명하게)
            draw.text((x, y), line, font=title_font, fill=(255, 255, 255, 255))
        
        # 카테고리/태그 표시
        categories = metadata.get('categories', [])
        if categories:
            if isinstance(categories, list):
                category_text = ' • '.join(categories[:2])
            else:
                category_text = categories
                
            draw.text((50, img.height - 40), category_text, 
                     font=category_font, fill=tuple(list(self._hex_to_rgb(scheme['secondary'])) + [255]))
        
        # 오버레이 합성
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        return img.convert('RGB')

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """텍스트를 여러 줄로 래핑 (한글 지원)"""
        # 한글과 영어가 섞인 텍스트 처리
        words = []
        current_word = ""
        
        for char in text:
            if char.isspace():
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)
            elif self._is_korean(char):
                # 한글 문자의 경우 적절한 위치에서 줄바꿈 가능
                current_word += char
                if len(current_word) >= 15:  # 한글 15자 정도에서 줄바꿈 가능
                    words.append(current_word)
                    current_word = ""
            else:
                current_word += char
        
        if current_word:
            words.append(current_word)
        
        # 공백 제거
        words = [w for w in words if not w.isspace()]
        
        lines = []
        current_line = []
        
        for word in words:
            test_line = ''.join(current_line + [word])
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except:
                # 폰트가 getbbox를 지원하지 않는 경우
                text_width = len(test_line) * 20  # 근사치
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(''.join(current_line))
                    current_line = [word]
                else:
                    # 단어가 너무 긴 경우 강제로 잘라내기
                    if len(word) > 20:
                        lines.append(word[:20] + "...")
                    else:
                        lines.append(word)
        
        if current_line:
            lines.append(''.join(current_line))
        
        return lines[:2]  # 최대 2줄
    
    def _is_korean(self, char: str) -> bool:
        """한글 문자인지 확인"""
        return '\uac00' <= char <= '\ud7af' or '\u3131' <= char <= '\u318e'

    def _select_color_scheme(self, metadata: Dict) -> Dict:
        """메타데이터를 기반으로 색상 스키마 선택"""
        categories = metadata.get('categories', [])
        tags = metadata.get('tags', [])
        
        all_terms = []
        if isinstance(categories, list):
            all_terms.extend([cat.lower() for cat in categories])
        elif isinstance(categories, str):
            all_terms.append(categories.lower())
            
        if isinstance(tags, list):
            all_terms.extend([tag.lower() for tag in tags])
        elif isinstance(tags, str):
            all_terms.append(tags.lower())
        
        # 우선순위에 따른 스키마 선택
        for term in all_terms:
            if 'aws' in term:
                return self.color_schemes['aws']
            elif any(python_term in term for python_term in ['python', 'django', 'flask', 'fastapi']):
                if 'django' in term:
                    return self.color_schemes['django']
                return self.color_schemes['python']
            elif any(ai_term in term for ai_term in ['ai', 'yolo', 'opencv', 'tensorflow', 'pytorch']):
                return self.color_schemes['ai']
            elif 'firebase' in term:
                return self.color_schemes['firebase']
            elif 'opencv' in term:
                return self.color_schemes['opencv']
        
        return self.color_schemes['default']

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """HEX 색상을 RGB로 변환"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def create_fallback_image(self, metadata: Dict, output_path: Path) -> bool:
        """키워드 기반 이미지 검색 실패 시 폴백 이미지 생성"""
        try:
            size = (1200, 630)
            scheme = self._select_color_scheme(metadata)
            
            # 그라데이션 배경 생성
            img = Image.new('RGB', size, self._hex_to_rgb(scheme['primary']))
            
            # 그라데이션 효과
            for i in range(size[1]):
                alpha = i / size[1]
                primary_rgb = self._hex_to_rgb(scheme['primary'])
                secondary_rgb = self._hex_to_rgb(scheme['gradient'][1])
                
                blended = tuple(int(primary_rgb[j] * (1 - alpha) + secondary_rgb[j] * alpha) for j in range(3))
                
                draw = ImageDraw.Draw(img)
                draw.line([(0, i), (size[0], i)], fill=blended)
            
            # 장식적 요소
            draw = ImageDraw.Draw(img)
            
            # 상단 장식 바
            draw.rectangle([0, 0, size[0], 8], fill=self._hex_to_rgb(scheme['secondary']))
            
            # 하단 장식 바
            draw.rectangle([0, size[1]-8, size[0], size[1]], fill=self._hex_to_rgb(scheme['accent']))
            
            # 기하학적 패턴
            for i in range(0, size[0], 100):
                draw.line([(i, 0), (i + 50, 50)], fill=self._hex_to_rgb(scheme['accent']), width=1)
            
            # 오버레이 추가
            img = self._add_overlay(img, metadata)
            
            # 저장
            img.save(output_path, 'WEBP', quality=85, optimize=True)
            print(f"✅ 폴백 이미지 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 폴백 이미지 생성 실패: {e}")
            return False

    def generate_thumbnail_for_post(self, post_file: str) -> bool:
        """특정 포스트의 썸네일 생성"""
        post_path = self.posts_dir / post_file
        
        if not post_path.exists():
            print(f"❌ 포스트 파일을 찾을 수 없습니다: {post_path}")
            return False
        
        # 메타데이터 추출
        metadata = self.extract_post_metadata(post_path)
        if not metadata:
            print(f"❌ 메타데이터를 추출할 수 없습니다: {post_file}")
            return False
        
        # 출력 파일 경로
        image_name = post_file.replace('.md', '.webp')
        output_path = self.images_dir / image_name
        
        # 이미 존재하는 경우 건너뛰기 (덮어쓰기 원하면 삭제 후 실행)
        if output_path.exists():
            print(f"ℹ️ 썸네일이 이미 존재합니다: {output_path}")
            return True
        
        print(f"🎨 썸네일 생성 중: {metadata.get('title', post_file)}")
        
        # 검색 키워드 생성
        keywords = self.generate_search_keywords(metadata)
        print(f"🔍 검색 키워드: {keywords}")
        
        # 이미지 검색
        images = self.search_unsplash_images(keywords)
        
        # 이미지 다운로드 및 처리 시도
        success = False
        for i, image_info in enumerate(images):
            print(f"🔄 이미지 다운로드 시도 {i+1}/{len(images)}: {image_info['keyword']}")
            if self.download_and_process_image(image_info, output_path, metadata):
                success = True
                break
        
        # 모든 이미지 다운로드 실패 시 폴백 이미지 생성
        if not success:
            print("⚠️ 모든 이미지 다운로드 실패, 폴백 이미지 생성 중...")
            success = self.create_fallback_image(metadata, output_path)
        
        if success:
            print(f"✅ 썸네일 생성 완료: {output_path}")
        else:
            print(f"❌ 썸네일 생성 실패: {post_file}")
        
        # 캐시 저장
        self._save_caches()
        
        return success

    def generate_thumbnails_for_recent_posts(self, days: int = 30) -> List[str]:
        """최근 포스트들의 썸네일 생성"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_posts = []
        
        # 최근 포스트 찾기
        for post_file in self.posts_dir.glob("*.md"):
            try:
                # 파일명에서 날짜 추출 (YYYY-MM-DD 형식)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', post_file.name)
                if date_match:
                    post_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    if post_date >= cutoff_date:
                        recent_posts.append(post_file.name)
            except Exception:
                continue
        
        # 날짜순 정렬 (최신순)
        recent_posts.sort(reverse=True)
        
        print(f"📅 최근 {days}일 간의 포스트 {len(recent_posts)}개 발견")
        
        success_count = 0
        for post_file in recent_posts:
            if self.generate_thumbnail_for_post(post_file):
                success_count += 1
        
        print(f"✅ 총 {success_count}/{len(recent_posts)}개 썸네일 생성 완료")
        
        return recent_posts

    def generate_thumbnail_for_current_post(self) -> bool:
        """현재 편집 중인 포스트의 썸네일 생성"""
        # 가장 최근 수정된 포스트 파일 찾기
        latest_post = None
        latest_time = 0
        
        for post_file in self.posts_dir.glob("*.md"):
            mtime = post_file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_post = post_file
        
        if latest_post:
            print(f"📝 가장 최근 수정된 포스트: {latest_post.name}")
            return self.generate_thumbnail_for_post(latest_post.name)
        else:
            print("❌ 포스트 파일을 찾을 수 없습니다.")
            return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='포스트 키워드 기반 자동 썸네일 생성기')
    parser.add_argument('--post', '-p', help='특정 포스트 파일명 (예: 2025-08-14-example.md)')
    parser.add_argument('--recent', '-r', type=int, default=7, help='최근 N일간의 포스트 처리 (기본값: 7)')
    parser.add_argument('--current', '-c', action='store_true', help='현재 편집 중인 포스트 처리')
    parser.add_argument('--workspace', '-w', default='.', help='작업 공간 경로 (기본값: 현재 디렉토리)')
    
    args = parser.parse_args()
    
    # 현재 스크립트가 있는 디렉토리를 기본 작업공간으로 설정
    if args.workspace == '.':
        args.workspace = os.path.dirname(os.path.abspath(__file__))
    
    generator = AutoThumbnailGenerator(args.workspace)
    
    if args.post:
        # 특정 포스트 처리
        generator.generate_thumbnail_for_post(args.post)
    elif args.current:
        # 현재 편집 중인 포스트 처리
        generator.generate_thumbnail_for_current_post()
    else:
        # 최근 포스트들 처리
        generator.generate_thumbnails_for_recent_posts(args.recent)


if __name__ == "__main__":
    main()
