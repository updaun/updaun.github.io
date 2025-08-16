#!/usr/bin/env python3
"""
AWS 예약 인스턴스 포스트 대표 이미지 생성
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_post_hero_image():
    """포스트 대표 이미지 생성"""
    
    # 이미지 크기 설정
    size = (1200, 630)
    
    # AWS 색상 팔레트
    aws_orange = '#FF9900'
    aws_blue = '#232F3E'
    aws_light_blue = '#4B8BBE'
    
    # 이미지 생성
    img = Image.new('RGB', size, '#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경
    for i in range(size[1]):
        alpha = i / size[1]
        r = int(26 + (35 - 26) * alpha)  # 1a -> 23
        g = int(26 + (47 - 26) * alpha)  # 1a -> 2f  
        b = int(46 + (62 - 46) * alpha)  # 2e -> 3e
        draw.line([(0, i), (size[0], i)], fill=(r, g, b))
    
    # AWS 로고 스타일 요소
    draw.rectangle([50, 50, size[0]-50, 120], fill=aws_orange)
    draw.rectangle([50, size[1]-120, size[0]-50, size[1]-50], fill=aws_light_blue)
    
    # 메인 텍스트 - 제목
    try:
        # 시스템 폰트 시도
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
        ]
        
        title_font = None
        subtitle_font = None
        
        for font_path in font_paths:
            try:
                title_font = ImageFont.truetype(font_path, 48)
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
    
    # 제목 텍스트
    title_lines = [
        "AWS 예약 인스턴스",
        "전략 및 모범 사례"
    ]
    
    y_start = 200
    for i, line in enumerate(title_lines):
        # 텍스트 크기 측정
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (size[0] - text_width) // 2
        
        # 텍스트 그리기
        draw.text((x, y_start + i * 60), line, fill='white', font=title_font)
    
    # 부제목
    subtitle = "실무자를 위한 완벽 가이드"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    text_width = bbox[2] - bbox[0]
    x = (size[0] - text_width) // 2
    draw.text((x, y_start + 140), subtitle, fill=aws_orange, font=subtitle_font)
    
    # 카테고리 태그들
    categories = ["AWS", "EC2", "Cost Optimization", "FinOps"]
    tag_y = size[1] - 200
    total_width = sum(len(cat) * 12 + 20 for cat in categories)  # 대략적인 계산
    start_x = (size[0] - total_width) // 2
    
    current_x = start_x
    for category in categories:
        # 태그 배경
        tag_width = len(category) * 12 + 20
        draw.rectangle([current_x, tag_y, current_x + tag_width, tag_y + 30], 
                      fill=aws_blue, outline=aws_orange, width=2)
        
        # 태그 텍스트
        text_x = current_x + 10
        draw.text((text_x, tag_y + 8), category, fill='white', font=subtitle_font)
        
        current_x += tag_width + 10
    
    # 장식 요소들
    # 상단 선
    draw.line([(100, 150), (size[0] - 100, 150)], fill=aws_orange, width=3)
    # 하단 선  
    draw.line([(100, size[1] - 150), (size[0] - 100, size[1] - 150)], fill=aws_light_blue, width=3)
    
    # 날짜
    date_text = "2025.07.28"
    bbox = draw.textbbox((0, 0), date_text, font=subtitle_font)
    text_width = bbox[2] - bbox[0]
    draw.text((size[0] - text_width - 60, 70), date_text, fill='white', font=subtitle_font)
    
    return img

# 이미지 생성 및 저장
output_dir = Path('/home/lleague/projects/updaun.github.io/assets/images/aws-ri')
output_dir.mkdir(parents=True, exist_ok=True)

img = create_post_hero_image()
img.save(output_dir / 'post-hero.png', 'PNG', quality=95)
print("✓ Post hero image created: post-hero.png")

# 블로그 메인 이미지도 생성 (1200x630 OG 이미지 형식)
img.save('/home/lleague/projects/updaun.github.io/assets/img/2025-07-28-aws-reserved-instances-strategy-best-practices.png', 'PNG', quality=95)
print("✓ Blog thumbnail created: 2025-07-28-aws-reserved-instances-strategy-best-practices.png")
