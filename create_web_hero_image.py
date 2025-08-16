#!/usr/bin/env python3
"""
AWS 예약 인스턴스 포스트 대표 이미지 생성 (웹 이미지 사용)
"""

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
from pathlib import Path

def download_and_process_image():
    """AWS 관련 이미지를 다운로드하고 처리"""
    
    # AWS 공식 아키텍처 다이어그램 이미지 또는 관련 이미지 URL들
    image_urls = [
        "https://d1.awsstatic.com/webteam/architecture-icons/q1-2022/Arch_AWS-Cost-Management_64.4f13cf2648aed50b0fa8b9b37c27c64ce843a40e.svg",
        "https://d1.awsstatic.com/webteam/architecture-icons/q1-2022/Arch_Amazon-EC2_64.47b0457cccfd20fc4ce8b3dc6feca0fe8e0c4af3.svg",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&h=630&fit=crop",  # 기술 배경
        "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=1200&h=630&fit=crop",  # 클라우드 컨셉
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&h=630&fit=crop"   # 비즈니스/차트
    ]
    
    for url in image_urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            print(f"Trying to download: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 이미지 열기
            img = Image.open(io.BytesIO(response.content))
            
            # RGB로 변환
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            print(f"Successfully downloaded image: {img.size}")
            return img
            
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            continue
    
    # 모든 URL이 실패하면 단색 배경 생성
    print("Creating fallback gradient background...")
    return create_gradient_background()

def create_gradient_background():
    """그라데이션 배경 생성"""
    size = (1200, 630)
    img = Image.new('RGB', size, '#1a1a2e')
    
    # AWS 색상으로 그라데이션
    for y in range(size[1]):
        progress = y / size[1]
        
        # 색상 계산 (어두운 파란색에서 주황색으로)
        r = int(26 + (255 - 26) * progress * 0.3)  # 살짝 주황색 틴트
        g = int(26 + (153 - 26) * progress * 0.2)  # 살짝 주황색 틴트
        b = int(46 + (0 - 46) * progress * 0.1)    # 파란색 유지
        
        for x in range(size[0]):
            img.putpixel((x, y), (r, g, b))
    
    return img

def add_text_overlay(img):
    """이미지에 텍스트 오버레이 추가"""
    # 이미지 크기
    size = img.size
    
    # 반투명 오버레이
    overlay = Image.new('RGBA', size, (0, 0, 0, 128))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    draw = ImageDraw.Draw(img)
    
    # AWS 색상
    aws_orange = '#FF9900'
    text_color = 'white'
    
    # 폰트 설정 (영문으로 변경)
    try:
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
        ]
        
        title_font = None
        subtitle_font = None
        
        for font_path in font_paths:
            try:
                title_font = ImageFont.truetype(font_path, 56)
                subtitle_font = ImageFont.truetype(font_path, 32)
                break
            except:
                continue
        
        if not title_font:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
    
    except Exception as e:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # 메인 제목 (영문)
    main_title = "AWS Reserved Instances"
    subtitle = "Strategy & Best Practices"
    date_text = "July 28, 2025"
    
    # 제목 위치 계산
    bbox = draw.textbbox((0, 0), main_title, font=title_font)
    title_width = bbox[2] - bbox[0]
    title_x = (size[0] - title_width) // 2
    title_y = size[1] // 2 - 80
    
    # 제목 그리기 (그림자 효과)
    draw.text((title_x + 2, title_y + 2), main_title, fill='black', font=title_font)
    draw.text((title_x, title_y), main_title, fill=text_color, font=title_font)
    
    # 부제목
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = bbox[2] - bbox[0]
    subtitle_x = (size[0] - subtitle_width) // 2
    subtitle_y = title_y + 70
    
    draw.text((subtitle_x + 1, subtitle_y + 1), subtitle, fill='black', font=subtitle_font)
    draw.text((subtitle_x, subtitle_y), subtitle, fill=aws_orange, font=subtitle_font)
    
    # 날짜
    bbox = draw.textbbox((0, 0), date_text, font=subtitle_font)
    date_width = bbox[2] - bbox[0]
    date_x = size[0] - date_width - 50
    date_y = 50
    
    draw.text((date_x, date_y), date_text, fill=text_color, font=subtitle_font)
    
    # AWS 로고 스타일 박스
    box_width = 200
    box_height = 40
    box_x = 50
    box_y = 50
    
    draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], 
                  fill=aws_orange)
    
    # AWS 텍스트
    aws_text = "AWS"
    bbox = draw.textbbox((0, 0), aws_text, font=subtitle_font)
    aws_width = bbox[2] - bbox[0]
    aws_x = box_x + (box_width - aws_width) // 2
    aws_y = box_y + 5
    
    draw.text((aws_x, aws_y), aws_text, fill='white', font=subtitle_font)
    
    # 카테고리 태그들
    categories = ["Cost Optimization", "EC2", "FinOps"]
    tag_y = size[1] - 100
    tag_spacing = 150
    start_x = 100
    
    for i, category in enumerate(categories):
        tag_x = start_x + i * tag_spacing
        
        # 태그 배경
        bbox = draw.textbbox((0, 0), category, font=subtitle_font)
        tag_width = bbox[2] - bbox[0] + 20
        
        draw.rectangle([tag_x, tag_y, tag_x + tag_width, tag_y + 35], 
                      fill='rgba(35, 47, 62, 200)', outline=aws_orange, width=2)
        
        # 태그 텍스트
        draw.text((tag_x + 10, tag_y + 5), category, fill='white', font=subtitle_font)
    
    return img

def main():
    """메인 함수"""
    output_dir = Path('/home/lleague/projects/updaun.github.io/assets/images/aws-ri')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미지 다운로드 또는 생성
    img = download_and_process_image()
    
    # 1200x630 크기로 조정
    target_size = (1200, 630)
    
    # 비율 유지하며 크롭
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]
    
    if img_ratio > target_ratio:
        # 이미지가 더 넓음 - 높이를 맞추고 좌우 크롭
        new_height = target_size[1]
        new_width = int(new_height * img_ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # 중앙에서 크롭
        left = (new_width - target_size[0]) // 2
        img = img.crop((left, 0, left + target_size[0], target_size[1]))
    else:
        # 이미지가 더 높음 - 너비를 맞추고 상하 크롭
        new_width = target_size[0]
        new_height = int(new_width / img_ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # 중앙에서 크롭
        top = (new_height - target_size[1]) // 2
        img = img.crop((0, top, target_size[0], top + target_size[1]))
    
    # 텍스트 오버레이 추가
    img = add_text_overlay(img)
    
    # 이미지 저장
    img.save(output_dir / 'post-hero-web.png', 'PNG', quality=95)
    print("✓ Post hero image created: post-hero-web.png")
    
    # 블로그 메인 이미지도 생성
    img.save('/home/lleague/projects/updaun.github.io/assets/img/2025-07-28-aws-reserved-instances-strategy-best-practices.png', 'PNG', quality=95)
    print("✓ Blog thumbnail created: 2025-07-28-aws-reserved-instances-strategy-best-practices.png")

if __name__ == "__main__":
    main()
