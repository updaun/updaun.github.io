#!/usr/bin/env python3
"""
Jekyll에서 Django 템플릿 태그 충돌을 해결하는 스크립트
"""
import re
import glob

def fix_django_templates_in_file(file_path):
    """파일에서 Django 템플릿 태그를 raw 태그로 감싸기"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # HTML 코드 블록을 찾아서 Django 템플릿 태그가 있는지 확인
    html_code_blocks = re.finditer(r'```html\n(.*?)```', content, re.DOTALL)
    
    new_content = content
    offset = 0
    
    for match in html_code_blocks:
        block_content = match.group(1)
        
        # Django 템플릿 태그가 있는지 확인
        if '{%' in block_content and '{% raw %}' not in block_content:
            # raw 태그로 감싸기
            wrapped_content = f'```html\n{{% raw %}}\n{block_content}{{% endraw %}}\n```'
            
            # 원본 블록을 새로운 내용으로 교체
            start = match.start() + offset
            end = match.end() + offset
            
            new_content = new_content[:start] + wrapped_content + new_content[end:]
            
            # 길이 차이만큼 오프셋 조정
            offset += len(wrapped_content) - (end - start)
            
            print(f"Fixed HTML block at position {start}")
    
    # 파일에 쓰기
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Fixed Django template tags in {file_path}")

if __name__ == "__main__":
    # 모든 Django 관련 포스트 파일 찾기
    file_patterns = [
        "/home/lleague/projects/updaun.github.io/_posts/*django*.md",
        "/home/lleague/projects/updaun.github.io/_posts/*yolo*.md"
    ]
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern):
            print(f"Processing {file_path}")
            fix_django_templates_in_file(file_path)
