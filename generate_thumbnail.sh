#!/bin/bash

# 썸네일 생성 간편 스크립트
# 사용법: ./generate_thumbnail.sh [옵션]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 가상환경 활성화
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ 가상환경을 찾을 수 없습니다. 먼저 가상환경을 설정해주세요."
    exit 1
fi

# Python 스크립트 실행
echo "🎨 썸네일 생성기 실행 중..."

if [ "$#" -eq 0 ]; then
    # 인수가 없으면 현재 포스트 처리
    python auto_thumbnail_generator.py --current
elif [ "$1" = "recent" ]; then
    # 최근 포스트들 처리
    DAYS=${2:-7}
    python auto_thumbnail_generator.py --recent "$DAYS"
elif [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "사용법:"
    echo "  ./generate_thumbnail.sh                 # 현재 편집 중인 포스트"
    echo "  ./generate_thumbnail.sh recent [일수]    # 최근 N일간의 포스트 (기본: 7일)"
    echo "  ./generate_thumbnail.sh [포스트파일명]   # 특정 포스트"
    echo ""
    echo "예시:"
    echo "  ./generate_thumbnail.sh                           # 현재 포스트"
    echo "  ./generate_thumbnail.sh recent 30                 # 최근 30일"
    echo "  ./generate_thumbnail.sh 2025-08-14-example.md     # 특정 포스트"
else
    # 특정 포스트 파일 처리
    python auto_thumbnail_generator.py --post "$1"
fi

echo "✅ 완료!"
