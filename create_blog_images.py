#!/usr/bin/env python3
"""
블로그 포스트 대표이미지 생성기 - 웹에서 이미지 다운로드 및 변환
"""

from PIL import Image, ImageDraw, ImageFont
import os
import re
import requests
from pathlib import Path
import io

def download_and_convert_image(url, output_path, size=(1200, 630)):
    """웹에서 이미지를 다운로드하고 webp로 변환"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 이미지 열기
        img = Image.open(io.BytesIO(response.content))
        
        # RGB로 변환 (RGBA나 다른 형식일 경우)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 크기 조정 (비율 유지하며 크롭)
        img_ratio = img.width / img.height
        target_ratio = size[0] / size[1]
        
        if img_ratio > target_ratio:
            # 이미지가 더 넓음 - 높이를 맞추고 좌우 크롭
            new_height = size[1]
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # 중앙에서 크롭
            left = (new_width - size[0]) // 2
            img = img.crop((left, 0, left + size[0], size[1]))
        else:
            # 이미지가 더 높음 - 너비를 맞추고 상하 크롭
            new_width = size[0]
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # 중앙에서 크롭
            top = (new_height - size[1]) // 2
            img = img.crop((0, top, size[0], top + size[1]))
        
        # WebP로 저장
        img.save(output_path, 'WEBP', quality=85, optimize=True)
        print(f"✅ 이미지 다운로드 및 변환 완료: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 이미지 다운로드 실패 ({url}): {e}")
        return False
    """블로그 포스트용 대표이미지 생성"""
    
    # 색상 팔레트 (카테고리별)
    color_schemes = {
        'aws': {
            'bg': '#232F3E',
            'accent': '#FF9900',
            'text': '#FFFFFF',
            'secondary': '#4A90E2'
        },
        'python': {
            'bg': '#1E3A8A',
            'accent': '#FFD43B',
            'text': '#FFFFFF', 
            'secondary': '#306998'
        },
        'firebase': {
            'bg': '#1A1A1A',
            'accent': '#FFCB2B',
            'text': '#FFFFFF',
            'secondary': '#FF6B35'
        },
        'opencv': {
            'bg': '#0F172A',
            'accent': '#22C55E',
            'text': '#FFFFFF',
            'secondary': '#3B82F6'
        },
        'ai': {
            'bg': '#0C0A09',
            'accent': '#A855F7',
            'text': '#FFFFFF',
            'secondary': '#06B6D4'
        },
        'default': {
            'bg': '#1F2937',
            'accent': '#3B82F6',
            'text': '#FFFFFF',
            'secondary': '#10B981'
        }
    }
    
    # 카테고리에 따른 색상 선택
    scheme_key = 'default'
    for category in categories:
        if 'aws' in category.lower():
            scheme_key = 'aws'
            break
        elif 'python' in category.lower() or 'django' in category.lower():
            scheme_key = 'python'
            break
        elif 'firebase' in category.lower():
            scheme_key = 'firebase'
            break
        elif 'opencv' in category.lower() or 'computer vision' in category.lower():
            scheme_key = 'opencv'
            break
        elif 'ai' in category.lower() or 'yolo' in category.lower():
            scheme_key = 'ai'
            break
    
    colors = color_schemes[scheme_key]
    
    # 이미지 생성
    img = Image.new('RGB', size, colors['bg'])
    draw = ImageDraw.Draw(img)
    
    # 배경 그라데이션 효과
    for i in range(size[1]):
        alpha = i / size[1]
        # 단순한 그라데이션 효과를 위한 색상 계산
        bg_color = tuple(int(c * (1 - alpha * 0.3)) for c in [int(colors['bg'][i:i+2], 16) for i in (1, 3, 5)])
        draw.line([(0, i), (size[0], i)], fill=bg_color)
    
    # 장식적 요소들
    draw.rectangle([50, 50, size[0]-50, 120], fill=colors['accent'])
    draw.rectangle([50, size[1]-120, size[0]-50, size[1]-50], fill=colors['secondary'])
    
    # 텍스트 추가
    try:
        # 시스템 폰트 찾기
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
            '/System/Library/Fonts/Arial.ttf',
            'arial.ttf'
        ]
        
        title_font = None
        category_font = None
        
        for font_path in font_paths:
            try:
                title_font = ImageFont.truetype(font_path, 72)
                category_font = ImageFont.truetype(font_path, 36)
                break
            except (OSError, IOError):
                continue
        
        if title_font is None:
            title_font = ImageFont.load_default()
            category_font = ImageFont.load_default()
    
    except Exception:
        title_font = ImageFont.load_default()
        category_font = ImageFont.load_default()
    
    # 제목 텍스트 래핑
    words = title.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        if bbox[2] - bbox[0] <= size[0] - 100:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # 최대 3줄로 제한
    if len(lines) > 3:
        lines = lines[:2] + [lines[2] + '...']
    
    # 제목 텍스트 그리기
    total_height = len(lines) * 80
    start_y = (size[1] - total_height) // 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (size[0] - text_width) // 2
        y = start_y + i * 80
        
        # 텍스트 그림자
        draw.text((x+2, y+2), line, font=title_font, fill='#000000')
        # 메인 텍스트
        draw.text((x, y), line, font=title_font, fill=colors['text'])
    
    # 카테고리 표시
    category_text = ' | '.join(categories)
    bbox = draw.textbbox((0, 0), category_text, font=category_font)
    cat_width = bbox[2] - bbox[0]
    cat_x = (size[0] - cat_width) // 2
    cat_y = size[1] - 100
    
    draw.text((cat_x, cat_y), category_text, font=category_font, fill=colors['accent'])
    
    # WebP로 저장
    img.save(output_path, 'WEBP', quality=85, optimize=True)
    print(f"✅ 이미지 생성 완료: {output_path}")

def extract_post_info(file_path):
    """포스트 파일에서 제목과 카테고리 추출"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # YAML front matter 추출
    yaml_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
    if not yaml_match:
        return None, None
    
    yaml_content = yaml_match.group(1)
    
    # 제목 추출
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', yaml_content, re.MULTILINE)
    title = title_match.group(1) if title_match else "제목 없음"
    
    # 카테고리 추출
    categories_match = re.search(r'^categories:\s*\[(.*?)\]', yaml_content, re.MULTILINE)
    if categories_match:
        categories = [cat.strip().strip('"\'') for cat in categories_match.group(1).split(',')]
    else:
        categories = ["블로그"]
    
    return title, categories

def main():
    """최근 포스트들의 대표이미지 생성"""
    posts_dir = Path("/home/lleague/projects/updaun.github.io/_posts")
    images_dir = Path("/home/lleague/projects/updaun.github.io/assets/img/posts")
    
    # 이미지 디렉토리 생성
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 최근 포스트들 (2025년 7월 이후)
    recent_posts = [
        "2025-07-23-aws-sqs-to-stepfunctions-delayed-push-messaging.md",
        "2025-07-22-firebase-admin-python-messaging-guide.md", 
        "2025-07-20-yolo-v10-complete-guide.md"
    ]
    
    for post_file in recent_posts:
        post_path = posts_dir / post_file
        if not post_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {post_path}")
            continue
        
        # 포스트 정보 추출
        title, categories = extract_post_info(post_path)
        if not title:
            print(f"❌ 제목을 추출할 수 없습니다: {post_file}")
            continue
        
        # 출력 파일명 생성
        image_name = post_file.replace('.md', '.webp')
        output_path = images_dir / image_name
        
        print(f"🎨 이미지 생성 중: {title}")
        print(f"📂 카테고리: {categories}")
        
        # 이미지 생성
        create_blog_image(title, categories, str(output_path))
        
        print("-" * 50)

if __name__ == "__main__":
    main()
