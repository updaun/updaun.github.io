#!/usr/bin/env python3
"""
포스트와 썸네일 매칭 점검 및 수정 도구

이 스크립트는:
1. 포스트 파일과 썸네일 이미지 파일을 매칭하여 상태를 확인합니다
2. 포스트의 front matter에 올바른 image 경로를 추가/수정합니다
3. 썸네일이 없는 포스트를 자동으로 생성할 수 있는 목록을 제공합니다
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml


class PostThumbnailMatcher:
    """포스트와 썸네일 매칭 관리자"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.posts_dir = self.workspace_path / "_posts"
        self.images_dir = self.workspace_path / "assets" / "img" / "posts"
        
        if not self.posts_dir.exists():
            raise FileNotFoundError(f"포스트 디렉토리를 찾을 수 없습니다: {self.posts_dir}")
        
        if not self.images_dir.exists():
            print(f"이미지 디렉토리가 없어 생성합니다: {self.images_dir}")
            self.images_dir.mkdir(parents=True, exist_ok=True)

    def get_post_files(self) -> List[Path]:
        """모든 포스트 파일 가져오기"""
        return list(self.posts_dir.glob("*.md"))

    def get_thumbnail_files(self) -> Dict[str, Path]:
        """썸네일 파일들을 파일명을 키로 하는 딕셔너리로 반환"""
        thumbnails = {}
        for img_file in self.images_dir.iterdir():
            if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                # 확장자를 제거한 파일명을 키로 사용
                base_name = img_file.stem
                thumbnails[base_name] = img_file
        return thumbnails

    def extract_post_metadata(self, post_file: Path) -> Tuple[str, Optional[str], Dict]:
        """포스트 파일에서 메타데이터 추출"""
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAML front matter 추출
            if content.startswith('---'):
                try:
                    end_idx = content.find('---', 3)
                    if end_idx != -1:
                        yaml_content = content[3:end_idx].strip()
                        metadata = yaml.safe_load(yaml_content)
                        if metadata:
                            # 포스트 파일명에서 확장자 제거
                            post_name = post_file.stem
                            current_image = metadata.get('image')
                            return post_name, current_image, metadata
                except yaml.YAMLError as e:
                    print(f"⚠️ YAML 파싱 오류 ({post_file.name}): {e}")
            
            return post_file.stem, None, {}
            
        except Exception as e:
            print(f"⚠️ 파일 읽기 오류 ({post_file.name}): {e}")
            return post_file.stem, None, {}

    def check_matching_status(self) -> Dict:
        """포스트와 썸네일 매칭 상태 확인"""
        posts = self.get_post_files()
        thumbnails = self.get_thumbnail_files()
        
        result = {
            'matched': [],      # 매칭된 포스트
            'unmatched_posts': [],  # 썸네일이 없는 포스트
            'orphaned_thumbnails': [],  # 포스트가 없는 썸네일
            'incorrect_paths': []   # 잘못된 경로를 가진 포스트
        }
        
        post_names = set()
        
        for post_file in posts:
            post_name, current_image, metadata = self.extract_post_metadata(post_file)
            post_names.add(post_name)
            
            # 썸네일 파일 존재 확인
            if post_name in thumbnails:
                thumbnail_path = thumbnails[post_name]
                expected_image_path = f"/assets/img/posts/{thumbnail_path.name}"
                
                if current_image == expected_image_path:
                    result['matched'].append({
                        'post': post_file.name,
                        'thumbnail': thumbnail_path.name,
                        'image_path': current_image
                    })
                else:
                    result['incorrect_paths'].append({
                        'post': post_file.name,
                        'thumbnail': thumbnail_path.name,
                        'current_path': current_image,
                        'expected_path': expected_image_path
                    })
            else:
                result['unmatched_posts'].append({
                    'post': post_file.name,
                    'post_name': post_name,
                    'current_image': current_image
                })
        
        # 포스트가 없는 썸네일 찾기
        for thumb_name, thumb_path in thumbnails.items():
            if thumb_name not in post_names:
                result['orphaned_thumbnails'].append({
                    'thumbnail': thumb_path.name,
                    'thumbnail_name': thumb_name
                })
        
        return result

    def fix_incorrect_paths(self, incorrect_paths: List[Dict]) -> int:
        """잘못된 이미지 경로 수정"""
        fixed_count = 0
        
        for item in incorrect_paths:
            post_file = self.posts_dir / item['post']
            expected_path = item['expected_path']
            
            try:
                # 파일 읽기
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # YAML front matter 부분에서 image 필드 수정/추가
                if content.startswith('---'):
                    end_idx = content.find('---', 3)
                    if end_idx != -1:
                        yaml_part = content[3:end_idx]
                        rest_part = content[end_idx:]
                        
                        # YAML 파싱
                        try:
                            metadata = yaml.safe_load(yaml_part)
                            if metadata is None:
                                metadata = {}
                            
                            # image 필드 추가/수정
                            metadata['image'] = expected_path
                            
                            # YAML 다시 생성
                            new_yaml = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
                            new_content = f"---\n{new_yaml}---{rest_part}"
                            
                            # 파일 저장
                            with open(post_file, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            print(f"✅ 수정됨: {item['post']} -> {expected_path}")
                            fixed_count += 1
                            
                        except yaml.YAMLError as e:
                            print(f"⚠️ YAML 처리 오류 ({item['post']}): {e}")
                
            except Exception as e:
                print(f"⚠️ 파일 수정 오류 ({item['post']}): {e}")
        
        return fixed_count

    def add_missing_image_paths(self, unmatched_posts: List[Dict]) -> int:
        """썸네일이 있는데 image 경로가 없는 포스트에 경로 추가"""
        thumbnails = self.get_thumbnail_files()
        added_count = 0
        
        for item in unmatched_posts:
            post_name = item['post_name']
            if post_name in thumbnails:  # 썸네일이 존재하는 경우만
                post_file = self.posts_dir / item['post']
                thumbnail_path = thumbnails[post_name]
                expected_path = f"/assets/img/posts/{thumbnail_path.name}"
                
                try:
                    # 파일 읽기
                    with open(post_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # YAML front matter에 image 필드 추가
                    if content.startswith('---'):
                        end_idx = content.find('---', 3)
                        if end_idx != -1:
                            yaml_part = content[3:end_idx]
                            rest_part = content[end_idx:]
                            
                            try:
                                metadata = yaml.safe_load(yaml_part)
                                if metadata is None:
                                    metadata = {}
                                
                                # image 필드가 없거나 비어있는 경우에만 추가
                                if not metadata.get('image'):
                                    metadata['image'] = expected_path
                                    
                                    # YAML 다시 생성
                                    new_yaml = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
                                    new_content = f"---\n{new_yaml}---{rest_part}"
                                    
                                    # 파일 저장
                                    with open(post_file, 'w', encoding='utf-8') as f:
                                        f.write(new_content)
                                    
                                    print(f"✅ 이미지 경로 추가: {item['post']} -> {expected_path}")
                                    added_count += 1
                                
                            except yaml.YAMLError as e:
                                print(f"⚠️ YAML 처리 오류 ({item['post']}): {e}")
                    
                except Exception as e:
                    print(f"⚠️ 파일 수정 오류 ({item['post']}): {e}")
        
        return added_count

    def print_status_report(self, status: Dict):
        """상태 리포트 출력"""
        print("\n" + "="*60)
        print("📊 포스트-썸네일 매칭 상태 리포트")
        print("="*60)
        
        print(f"\n✅ 정상 매칭: {len(status['matched'])}개")
        if status['matched']:
            for item in status['matched'][:5]:  # 처음 5개만 표시
                print(f"   • {item['post']} ↔ {item['thumbnail']}")
            if len(status['matched']) > 5:
                print(f"   ... 및 {len(status['matched']) - 5}개 더")
        
        print(f"\n⚠️ 경로 오류: {len(status['incorrect_paths'])}개")
        if status['incorrect_paths']:
            for item in status['incorrect_paths']:
                print(f"   • {item['post']}")
                print(f"     현재: {item['current_path']}")
                print(f"     예상: {item['expected_path']}")
        
        print(f"\n❌ 썸네일 없음: {len(status['unmatched_posts'])}개")
        if status['unmatched_posts']:
            for item in status['unmatched_posts']:
                thumbnails = self.get_thumbnail_files()
                has_thumbnail = item['post_name'] in thumbnails
                status_icon = "🔗" if has_thumbnail else "❌"
                print(f"   {status_icon} {item['post']}")
                if has_thumbnail:
                    print(f"     (썸네일 존재하지만 경로 미설정)")
        
        print(f"\n🗑️ 고아 썸네일: {len(status['orphaned_thumbnails'])}개")
        if status['orphaned_thumbnails']:
            for item in status['orphaned_thumbnails']:
                print(f"   • {item['thumbnail']}")

    def run_fix(self):
        """모든 매칭 문제 자동 수정"""
        print("🔧 포스트-썸네일 매칭 문제를 수정합니다...")
        
        status = self.check_matching_status()
        self.print_status_report(status)
        
        total_fixed = 0
        
        # 1. 잘못된 경로 수정
        if status['incorrect_paths']:
            print(f"\n🔧 잘못된 이미지 경로 {len(status['incorrect_paths'])}개를 수정합니다...")
            fixed = self.fix_incorrect_paths(status['incorrect_paths'])
            total_fixed += fixed
            print(f"✅ {fixed}개 경로 수정 완료")
        
        # 2. 썸네일은 있지만 경로가 설정되지 않은 포스트 처리
        if status['unmatched_posts']:
            print(f"\n🔗 썸네일 경로 누락된 포스트를 확인합니다...")
            added = self.add_missing_image_paths(status['unmatched_posts'])
            total_fixed += added
            print(f"✅ {added}개 이미지 경로 추가 완료")
        
        # 최종 상태 확인
        print(f"\n🎉 총 {total_fixed}개 항목이 수정되었습니다!")
        
        # 수정 후 다시 상태 확인
        if total_fixed > 0:
            print("\n📋 수정 후 상태:")
            final_status = self.check_matching_status()
            self.print_status_report(final_status)
            
            # 여전히 썸네일이 필요한 포스트들 안내
            still_need_thumbnails = [
                item for item in final_status['unmatched_posts'] 
                if item['post_name'] not in self.get_thumbnail_files()
            ]
            
            if still_need_thumbnails:
                print(f"\n📝 썸네일 생성이 필요한 포스트 {len(still_need_thumbnails)}개:")
                for item in still_need_thumbnails:
                    print(f"   • {item['post']}")
                print("\n💡 auto_thumbnail_generator.py를 실행하여 썸네일을 생성하세요.")


def main():
    """메인 실행 함수"""
    workspace_path = "/home/lleague/projects/updaun.github.io"
    
    try:
        matcher = PostThumbnailMatcher(workspace_path)
        matcher.run_fix()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
