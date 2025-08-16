#!/usr/bin/env python3
"""
AWS 예약 인스턴스 포스트용 이미지 생성기
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 출력 디렉토리
output_dir = Path('/home/lleague/projects/updaun.github.io/assets/images/aws-ri')
output_dir.mkdir(parents=True, exist_ok=True)

# AWS 색상 팔레트
aws_orange = '#FF9900'
aws_blue = '#232F3E'
aws_light_blue = '#4B8BBE'
aws_gray = '#E6E6E6'

def create_cost_explorer_analysis():
    """Cost Explorer 분석 이미지 생성"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 월별 비용 추이
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ondemand_cost = [8400, 8200, 8600, 8800, 9200, 9600, 9800, 9400, 8900, 8500, 8300, 8100]
    ri_cost = [4200, 4100, 4300, 4400, 4600, 4800, 4900, 4700, 4450, 4250, 4150, 4050]
    
    ax1.plot(months, ondemand_cost, 'o-', color=aws_orange, linewidth=3, markersize=8, label='On-Demand')
    ax1.plot(months, ri_cost, 's-', color=aws_blue, linewidth=3, markersize=8, label='Reserved Instance')
    ax1.fill_between(months, ondemand_cost, ri_cost, alpha=0.3, color=aws_orange)
    
    ax1.set_title('Monthly Cost Comparison', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Cost ($)', fontsize=12)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 절약 효과 파이 차트
    savings = sum(ondemand_cost) - sum(ri_cost)
    total_ondemand = sum(ondemand_cost)
    
    sizes = [savings, total_ondemand - savings]
    labels = [f'Savings\n${savings:,}\n({savings/total_ondemand*100:.1f}%)', 
              f'RI Cost\n${total_ondemand - savings:,}']
    colors = [aws_orange, aws_blue]
    
    ax2.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90, 
            textprops={'fontsize': 11, 'fontweight': 'bold'})
    ax2.set_title('Annual Savings with RI', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'cost-explorer-analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_ri_utilization_dashboard():
    """RI 활용률 대시보드 이미지 생성"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 활용률 게이지
    utilization = 87
    ax1.pie([utilization, 100-utilization], colors=[aws_orange, aws_gray], 
            startangle=90, counterclock=False)
    circle = plt.Circle((0,0), 0.7, color='white')
    ax1.add_artist(circle)
    ax1.text(0, 0, f'{utilization}%', ha='center', va='center', fontsize=20, fontweight='bold')
    ax1.set_title('RI Utilization Rate', fontsize=14, fontweight='bold')
    
    # 2. 인스턴스 타입별 활용률
    instance_types = ['m5.large', 'm5.xlarge', 'c5.large', 'r5.large', 't3.medium']
    utilization_rates = [95, 88, 92, 78, 85]
    
    bars = ax2.bar(instance_types, utilization_rates, color=aws_blue, alpha=0.7)
    ax2.axhline(y=80, color=aws_orange, linestyle='--', linewidth=2, label='Target (80%)')
    ax2.set_title('Utilization by Instance Type', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Utilization (%)')
    ax2.legend()
    ax2.tick_params(axis='x', rotation=45)
    
    # 막대 위에 값 표시
    for bar, rate in zip(bars, utilization_rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{rate}%', ha='center', va='bottom', fontweight='bold')
    
    # 3. 월별 활용률 트렌드
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    monthly_util = [82, 85, 88, 86, 89, 87]
    
    ax3.plot(months, monthly_util, 'o-', color=aws_orange, linewidth=3, markersize=8)
    ax3.fill_between(months, monthly_util, alpha=0.3, color=aws_orange)
    ax3.axhline(y=85, color=aws_blue, linestyle='--', alpha=0.7, label='Average')
    ax3.set_title('Monthly Utilization Trend', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Utilization (%)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. RI 커버리지
    coverage_data = {'Production': 85, 'Staging': 60, 'Development': 0}
    ax4.barh(list(coverage_data.keys()), list(coverage_data.values()), 
             color=[aws_blue, aws_light_blue, aws_gray])
    ax4.set_title('RI Coverage by Environment', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Coverage (%)')
    
    for i, (env, coverage) in enumerate(coverage_data.items()):
        ax4.text(coverage + 2, i, f'{coverage}%', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'ri-utilization-dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_size_flexibility_matrix():
    """Size Flexibility 매트릭스 이미지 생성"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 인스턴스 패밀리 데이터
    instances = {
        'm5.small': {'size': 1, 'vcpu': 1, 'memory': 2},
        'm5.medium': {'size': 2, 'vcpu': 1, 'memory': 4},
        'm5.large': {'size': 4, 'vcpu': 2, 'memory': 8},
        'm5.xlarge': {'size': 8, 'vcpu': 4, 'memory': 16},
        'm5.2xlarge': {'size': 16, 'vcpu': 8, 'memory': 32},
        'm5.4xlarge': {'size': 32, 'vcpu': 16, 'memory': 64}
    }
    
    # 매트릭스 생성
    y_pos = np.arange(len(instances))
    instance_names = list(instances.keys())
    sizes = [instances[name]['size'] for name in instance_names]
    
    # 기준 인스턴스 (m5.large) 하이라이트
    colors = [aws_orange if name == 'm5.large' else aws_blue for name in instance_names]
    
    bars = ax.barh(y_pos, sizes, color=colors, alpha=0.7)
    
    # 설정
    ax.set_yticks(y_pos)
    ax.set_yticklabels(instance_names)
    ax.set_xlabel('Normalization Factor', fontsize=12)
    ax.set_title('m5 Family Size Flexibility Matrix\n(m5.large RI = 4 units)', 
                 fontsize=16, fontweight='bold')
    
    # 값 표시
    for i, (bar, size, name) in enumerate(zip(bars, sizes, instance_names)):
        vcpu = instances[name]['vcpu']
        memory = instances[name]['memory']
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{size} units\n{vcpu} vCPU, {memory}GB RAM',
                va='center', fontsize=10)
    
    # m5.large 기준선
    ax.axvline(x=4, color=aws_orange, linestyle='--', alpha=0.8, linewidth=2)
    ax.text(4.2, len(instances)-1, 'Base RI\n(m5.large)', 
            color=aws_orange, fontweight='bold', va='top')
    
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(output_dir / 'size-flexibility-matrix.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_success_case_graph():
    """성공 사례 그래프 생성"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 사례 1: e-커머스 플랫폼 비용 변화
    quarters = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024', 'Q1 2025']
    before_ri = [650000, 680000, 720000, 850000, 700000]  # 계절성 반영
    after_ri = [420000, 440000, 465000, 550000, 450000]
    
    x = np.arange(len(quarters))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_ri, width, label='Before RI', color=aws_orange, alpha=0.7)
    bars2 = ax1.bar(x + width/2, after_ri, width, label='After RI Strategy', color=aws_blue, alpha=0.7)
    
    ax1.set_title('E-commerce Platform Cost Reduction', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Monthly Cost ($)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, rotation=45)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 절약액 표시
    for i, (before, after) in enumerate(zip(before_ri, after_ri)):
        savings = before - after
        ax1.text(i, max(before, after) + 20000, f'-${savings:,}', 
                ha='center', va='bottom', fontweight='bold', color='green')
    
    # 사례 2: 핀테크 스타트업 성장 대응
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    total_cost = [15000, 18000, 22000, 28000, 35000, 42000, 38000, 45000, 52000, 48000, 55000, 60000]
    ri_savings = [0, 0, 1500, 3000, 5000, 8000, 7500, 9500, 12000, 11000, 13500, 15000]
    effective_cost = [total - saving for total, saving in zip(total_cost, ri_savings)]
    
    ax2.fill_between(months, total_cost, alpha=0.3, color=aws_orange, label='Total Cost (without RI)')
    ax2.fill_between(months, effective_cost, alpha=0.7, color=aws_blue, label='Effective Cost (with RI)')
    ax2.plot(months, total_cost, 'o-', color=aws_orange, linewidth=2, markersize=6)
    ax2.plot(months, effective_cost, 's-', color=aws_blue, linewidth=2, markersize=6)
    
    ax2.set_title('Fintech Startup Growth & RI Adoption', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Monthly Cost ($)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'success-case-graph.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_hero_image():
    """포스트 메인 이미지 생성"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 배경 설정
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_facecolor('#f8f9fa')
    
    # AWS 로고 스타일 박스
    aws_box = FancyBboxPatch((0.5, 4), 9, 1.5, 
                            boxstyle="round,pad=0.1", 
                            facecolor=aws_blue, 
                            edgecolor='none')
    ax.add_patch(aws_box)
    
    # 메인 타이틀
    ax.text(5, 4.75, 'AWS Reserved Instances', 
            ha='center', va='center', fontsize=28, fontweight='bold', color='white')
    ax.text(5, 4.25, 'Strategy & Best Practices', 
            ha='center', va='center', fontsize=18, color='white', alpha=0.9)
    
    # 절약 효과 시각화
    savings_data = [72, 54, 45, 0]  # Standard 3년, Convertible 3년, Standard 1년, On-Demand
    labels = ['Standard\n3-Year', 'Convertible\n3-Year', 'Standard\n1-Year', 'On-Demand']
    x_positions = [1.5, 3.5, 5.5, 7.5]
    
    colors = [aws_orange, aws_light_blue, '#FFB84D', aws_gray]
    
    for i, (savings, label, x_pos, color) in enumerate(zip(savings_data, labels, x_positions, colors)):
        # 절약률 바
        bar_height = savings / 100 * 2.5  # 최대 높이 2.5
        rect = patches.Rectangle((x_pos-0.3, 0.5), 0.6, bar_height, 
                               facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        
        # 퍼센트 표시
        ax.text(x_pos, bar_height + 0.6, f'{savings}%', 
                ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        # 라벨
        ax.text(x_pos, 0.2, label, 
                ha='center', va='center', fontsize=10, fontweight='bold')
    
    ax.text(5, 3.5, 'Maximum Savings Comparison', 
            ha='center', va='center', fontsize=16, fontweight='bold', color=aws_blue)
    
    # 축 제거
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'aws-ri-hero.png', dpi=300, bbox_inches='tight', 
                facecolor='#f8f9fa', edgecolor='none')
    plt.close()

if __name__ == "__main__":
    print("Creating AWS Reserved Instances blog images...")
    
    create_cost_explorer_analysis()
    print("✓ Cost Explorer analysis image created")
    
    create_ri_utilization_dashboard()
    print("✓ RI utilization dashboard created")
    
    create_size_flexibility_matrix()
    print("✓ Size flexibility matrix created")
    
    create_success_case_graph()
    print("✓ Success case graph created")
    
    create_hero_image()
    print("✓ Hero image created")
    
    print(f"\nAll images saved to: {output_dir}")
    print("Images created:")
    for image_file in output_dir.glob("*.png"):
        print(f"  - {image_file.name}")
