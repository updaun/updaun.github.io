#!/usr/bin/env python3
"""
Favicon 생성 스크립트
사이트의 보라색 테마에 맞는 favicon을 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_favicon():
    # 아이콘 크기들 (다양한 해상도를 위해)
    sizes = [16, 32, 48, 64, 128, 256]
    
    # 사이트 테마 색상
    primary_color = "#8b7ab8"
    light_color = "#b8a9d9"
    dark_color = "#6b5b95"
    
    for size in sizes:
        # 새 이미지 생성 (투명 배경)
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 원형 배경
        margin = size // 8
        circle_coords = [margin, margin, size - margin, size - margin]
        
        # 그라디언트 효과를 위한 원형 배경
        draw.ellipse(circle_coords, fill=primary_color)
        
        # 내부 원 (밝은 색상)
        inner_margin = size // 4
        inner_coords = [inner_margin, inner_margin, size - inner_margin, size - inner_margin]
        draw.ellipse(inner_coords, fill=light_color)
        
        # 중앙에 "U" 또는 점
        center_size = size // 3
        center_margin = (size - center_size) // 2
        center_coords = [center_margin, center_margin, center_margin + center_size, center_margin + center_size]
        draw.ellipse(center_coords, fill=dark_color)
        
        # 파일 저장
        filename = f'favicon_{size}x{size}.png'
        img.save(filename, 'PNG')
        print(f"Created {filename}")
    
    # 기본 favicon.png (32x32)
    img_32 = Image.open('favicon_32x32.png')
    img_32.save('favicon.png', 'PNG')
    print("Created favicon.png (32x32)")
    
    # favicon.ico 생성 (여러 크기 포함)
    images = []
    for size in [16, 32, 48]:
        img = Image.open(f'favicon_{size}x{size}.png')
        images.append(img)
    
    images[0].save('favicon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48)])
    print("Created favicon.ico")
    
    # Apple touch icon (180x180)
    img_180 = Image.new('RGBA', (180, 180), (0, 0, 0, 0))
    draw_180 = ImageDraw.Draw(img_180)
    
    # 큰 원형 배경
    margin_180 = 10
    circle_coords_180 = [margin_180, margin_180, 170, 170]
    draw_180.ellipse(circle_coords_180, fill=primary_color)
    
    # 내부 원
    inner_margin_180 = 40
    inner_coords_180 = [inner_margin_180, inner_margin_180, 140, 140]
    draw_180.ellipse(inner_coords_180, fill=light_color)
    
    # 중앙 원
    center_margin_180 = 70
    center_coords_180 = [center_margin_180, center_margin_180, 110, 110]
    draw_180.ellipse(center_coords_180, fill=dark_color)
    
    img_180.save('apple-touch-icon.png', 'PNG')
    print("Created apple-touch-icon.png")
    
    # 임시 파일들 정리
    for size in sizes:
        try:
            os.remove(f'favicon_{size}x{size}.png')
        except:
            pass
    
    print("\nFavicon 생성 완료!")
    print("생성된 파일들:")
    print("- favicon.png (32x32)")
    print("- favicon.ico (멀티 사이즈)")
    print("- apple-touch-icon.png (180x180)")

if __name__ == "__main__":
    create_favicon()
