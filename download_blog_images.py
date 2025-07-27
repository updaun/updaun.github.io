#!/usr/bin/env python3
"""
블로그 포스트 대표이미지 다운로드 및 변환기
"""

from PIL import Image
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
    """최근 포스트들의 대표이미지 다운로드 및 변환"""
    posts_dir = Path("/home/lleague/projects/updaun.github.io/_posts")
    images_dir = Path("/home/lleague/projects/updaun.github.io/assets/img/posts")
    
    # 이미지 디렉토리 생성
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 최근 포스트들과 해당 이미지 URL들
    posts_images = {
        "2025-07-23-aws-sqs-to-stepfunctions-delayed-push-messaging.md": [
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&h=630&fit=crop&crop=center",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&h=630&fit=crop&crop=center"
        ],
        "2025-07-22-firebase-admin-python-messaging-guide.md": [
            "https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=1200&h=630&fit=crop&crop=center",
            "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&h=630&fit=crop&crop=center"
        ],
        "2025-07-20-yolo-v10-complete-guide.md": [
            "https://images.unsplash.com/photo-1555255707-c07966088b7b?w=1200&h=630&fit=crop&crop=center",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&h=630&fit=crop&crop=center"
        ]
    }
    
    for post_file, image_urls in posts_images.items():
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
        
        print(f"🎨 이미지 다운로드 중: {title}")
        print(f"📂 카테고리: {categories}")
        
        # 이미지 다운로드 시도
        success = False
        for i, url in enumerate(image_urls):
            print(f"🔄 시도 {i+1}: {url}")
            if download_and_convert_image(url, str(output_path)):
                success = True
                break
        
        if not success:
            print(f"❌ 모든 이미지 다운로드 실패: {post_file}")
        
        print("-" * 50)

if __name__ == "__main__":
    main()
