---
layout: post
title: "YOLOv10 데이터 전처리 완벽 가이드: 클래스별 균등 분할부터 데이터 증강까지"
date: 2025-08-06 10:00:00 +0900
categories: [AI, Computer Vision, YOLO]
tags: [yolov10, data preprocessing, data augmentation, object detection, machine learning]
description: "YOLOv10 학습을 위한 데이터 전처리 전 과정을 다룹니다. 클래스별 균등 분할, train/validation/test 데이터셋 구성, 그리고 데이터 부족 시 증강 기법까지 실용적인 예제와 함께 설명합니다."
---

# YOLOv10 데이터 전처리 완벽 가이드: 클래스별 균등 분할부터 데이터 증강까지

객체 탐지 모델의 성능은 데이터의 품질과 전처리 방법에 크게 좌우됩니다. 특히 YOLOv10과 같은 최신 모델에서는 올바른 데이터 전처리가 학습 성공의 핵심입니다. 이번 포스트에서는 YOLOv10 학습을 위한 데이터 전처리의 전 과정을 실용적인 예제와 함께 살펴보겠습니다.

## 목차
1. [YOLOv10 데이터 구조 이해](#yolov10-데이터-구조-이해)
2. [클래스별 균등 분할 전략](#클래스별-균등-분할-전략)
3. [Train/Validation/Test 데이터셋 구성](#trainvalidationtest-데이터셋-구성)
4. [데이터 증강 기법](#데이터-증강-기법)
5. [실제 구현 예제](#실제-구현-예제)
6. [모범 사례와 주의사항](#모범-사례와-주의사항)

## YOLOv10 데이터 구조 이해

### 기본 디렉토리 구조

YOLOv10은 다음과 같은 데이터 구조를 요구합니다:

```
dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

### 라벨 형식

YOLO 형식의 라벨은 각 이미지에 대해 다음과 같은 형식을 따릅니다:

```
class_id center_x center_y width height
```

- `class_id`: 클래스 인덱스 (0부터 시작)
- `center_x, center_y`: 바운딩 박스 중심점 (0-1 정규화)
- `width, height`: 바운딩 박스 크기 (0-1 정규화)

## 클래스별 균등 분할 전략

### 클래스 불균형 문제

실제 데이터에서는 클래스별 샘플 수가 불균등한 경우가 많습니다. 이는 다음과 같은 문제를 야기할 수 있습니다:

- **편향된 학습**: 많은 샘플을 가진 클래스에 편향
- **성능 저하**: 적은 샘플 클래스의 탐지 성능 저하
- **일반화 부족**: 실제 환경에서의 성능 차이

### 균등 분할 구현

다음은 클래스별로 균등하게 데이터를 분할하는 Python 코드입니다:

```python
import os
import shutil
import random
from collections import defaultdict, Counter
import yaml

class YOLODatasetSplitter:
    def __init__(self, source_images_dir, source_labels_dir, output_dir):
        self.source_images_dir = source_images_dir
        self.source_labels_dir = source_labels_dir
        self.output_dir = output_dir
        self.class_counts = defaultdict(list)
        
    def analyze_dataset(self):
        """데이터셋의 클래스별 분포를 분석합니다."""
        print("데이터셋 분석 중...")
        
        for label_file in os.listdir(self.source_labels_dir):
            if not label_file.endswith('.txt'):
                continue
                
            label_path = os.path.join(self.source_labels_dir, label_file)
            image_name = label_file.replace('.txt', '.jpg')  # 또는 .png
            
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            # 이미지에 포함된 클래스들을 추출
            classes_in_image = set()
            for line in lines:
                if line.strip():
                    class_id = int(line.split()[0])
                    classes_in_image.add(class_id)
            
            # 각 클래스에 대해 이미지 파일 추가
            for class_id in classes_in_image:
                self.class_counts[class_id].append(image_name)
        
        # 클래스별 통계 출력
        print("\n클래스별 이미지 수:")
        for class_id, images in self.class_counts.items():
            print(f"클래스 {class_id}: {len(images)}개 이미지")
            
        return self.class_counts
    
    def stratified_split(self, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
        """계층화 샘플링을 통한 데이터셋 분할"""
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("비율의 합이 1이 되어야 합니다.")
        
        train_images = set()
        val_images = set()
        test_images = set()
        
        print("\n계층화 샘플링 수행 중...")
        
        for class_id, images in self.class_counts.items():
            # 각 클래스별로 무작위 섞기
            random.shuffle(images)
            
            n_total = len(images)
            n_train = int(n_total * train_ratio)
            n_val = int(n_total * val_ratio)
            
            # 분할
            class_train = images[:n_train]
            class_val = images[n_train:n_train + n_val]
            class_test = images[n_train + n_val:]
            
            train_images.update(class_train)
            val_images.update(class_val)
            test_images.update(class_test)
            
            print(f"클래스 {class_id}: Train {len(class_train)}, Val {len(class_val)}, Test {len(class_test)}")
        
        return train_images, val_images, test_images
    
    def create_dataset_structure(self, train_images, val_images, test_images):
        """데이터셋 디렉토리 구조를 생성하고 파일을 복사합니다."""
        
        # 디렉토리 생성
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(self.output_dir, 'images', split), exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, 'labels', split), exist_ok=True)
        
        splits = {
            'train': train_images,
            'val': val_images,
            'test': test_images
        }
        
        print("\n파일 복사 중...")
        
        for split_name, image_list in splits.items():
            for image_name in image_list:
                # 이미지 파일 복사
                src_image = os.path.join(self.source_images_dir, image_name)
                dst_image = os.path.join(self.output_dir, 'images', split_name, image_name)
                
                if os.path.exists(src_image):
                    shutil.copy2(src_image, dst_image)
                
                # 라벨 파일 복사
                label_name = image_name.replace('.jpg', '.txt').replace('.png', '.txt')
                src_label = os.path.join(self.source_labels_dir, label_name)
                dst_label = os.path.join(self.output_dir, 'labels', split_name, label_name)
                
                if os.path.exists(src_label):
                    shutil.copy2(src_label, dst_label)
            
            print(f"{split_name}: {len(image_list)}개 파일 복사 완료")
```

## Train/Validation/Test 데이터셋 구성

### 분할 비율 결정

일반적인 분할 비율은 다음과 같습니다:

| 데이터셋 크기 | Train | Validation | Test |
|---------------|-------|------------|------|
| 소규모 (<1000) | 60% | 20% | 20% |
| 중간 규모 (1000-10000) | 70% | 20% | 10% |
| 대규모 (>10000) | 80% | 15% | 5% |

### 데이터셋 구성 실행

```python
def main():
    # 설정
    source_images_dir = "raw_data/images"
    source_labels_dir = "raw_data/labels"
    output_dir = "yolo_dataset"
    
    # 클래스 이름 정의
    class_names = ['person', 'car', 'bicycle', 'motorbike']
    
    # 데이터셋 분할 실행
    splitter = YOLODatasetSplitter(source_images_dir, source_labels_dir, output_dir)
    
    # 1. 데이터셋 분석
    class_counts = splitter.analyze_dataset()
    
    # 2. 계층화 분할
    train_images, val_images, test_images = splitter.stratified_split(
        train_ratio=0.7, val_ratio=0.2, test_ratio=0.1
    )
    
    # 3. 디렉토리 구조 생성 및 파일 복사
    splitter.create_dataset_structure(train_images, val_images, test_images)
    
    # 4. data.yaml 파일 생성
    create_data_yaml(output_dir, class_names)
    
    print(f"\n데이터셋 준비 완료: {output_dir}")

def create_data_yaml(output_dir, class_names):
    """YOLOv10용 data.yaml 파일을 생성합니다."""
    data_config = {
        'path': output_dir,
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': len(class_names),
        'names': class_names
    }
    
    with open(os.path.join(output_dir, 'data.yaml'), 'w') as f:
        yaml.dump(data_config, f, default_flow_style=False)
    
    print("data.yaml 파일 생성 완료")

if __name__ == "__main__":
    main()
```

## 데이터 증강 기법

### 데이터 부족 시 증강 전략

데이터가 부족한 경우 다음과 같은 증강 기법을 적용할 수 있습니다:

#### 1. 기본 증강 기법

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
import numpy as np

class YOLOAugmentation:
    def __init__(self):
        self.transform = A.Compose([
            # 기하학적 변환
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.1),
            A.RandomRotate90(p=0.3),
            A.Rotate(limit=15, p=0.3),
            A.ShiftScaleRotate(
                shift_limit=0.1, 
                scale_limit=0.2, 
                rotate_limit=15, 
                p=0.5
            ),
            
            # 색상 변환
            A.RandomBrightnessContrast(p=0.4),
            A.HueSaturationValue(
                hue_shift_limit=20,
                sat_shift_limit=30,
                val_shift_limit=20,
                p=0.3
            ),
            A.CLAHE(p=0.3),
            A.RandomGamma(p=0.3),
            
            # 노이즈 및 블러
            A.GaussNoise(p=0.2),
            A.Blur(blur_limit=3, p=0.2),
            A.MotionBlur(p=0.2),
            
            # 날씨 효과
            A.RandomRain(p=0.1),
            A.RandomSunFlare(p=0.05),
            
            # 크롭 및 패딩
            A.RandomCrop(height=512, width=512, p=0.3),
            A.PadIfNeeded(min_height=640, min_width=640, p=0.3),
            
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels']
        ))
    
    def augment_image(self, image, bboxes, class_labels):
        """이미지와 바운딩 박스를 함께 증강합니다."""
        try:
            augmented = self.transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_labels
            )
            return augmented['image'], augmented['bboxes'], augmented['class_labels']
        except Exception as e:
            print(f"증강 실패: {e}")
            return image, bboxes, class_labels
```

#### 2. 스마트 증강 시스템

```python
class SmartAugmentationSystem:
    def __init__(self, source_dir, target_dir, target_samples_per_class=1000):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.target_samples_per_class = target_samples_per_class
        self.augmentor = YOLOAugmentation()
        
    def analyze_class_distribution(self):
        """클래스별 현재 샘플 수를 분석합니다."""
        class_counts = defaultdict(int)
        
        for label_file in os.listdir(os.path.join(self.source_dir, 'labels', 'train')):
            if not label_file.endswith('.txt'):
                continue
                
            label_path = os.path.join(self.source_dir, 'labels', 'train', label_file)
            
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            classes_in_image = set()
            for line in lines:
                if line.strip():
                    class_id = int(line.split()[0])
                    classes_in_image.add(class_id)
            
            for class_id in classes_in_image:
                class_counts[class_id] += 1
        
        return class_counts
    
    def calculate_augmentation_needed(self, class_counts):
        """각 클래스별로 필요한 증강 수를 계산합니다."""
        augmentation_plan = {}
        
        for class_id, current_count in class_counts.items():
            if current_count < self.target_samples_per_class:
                needed = self.target_samples_per_class - current_count
                augmentation_plan[class_id] = needed
                print(f"클래스 {class_id}: 현재 {current_count}개, {needed}개 증강 필요")
            else:
                print(f"클래스 {class_id}: 현재 {current_count}개, 증강 불필요")
        
        return augmentation_plan
    
    def perform_targeted_augmentation(self, augmentation_plan):
        """클래스별로 타겟된 증강을 수행합니다."""
        
        for class_id, needed_count in augmentation_plan.items():
            print(f"\n클래스 {class_id} 증강 시작...")
            
            # 해당 클래스가 포함된 이미지들 찾기
            class_images = []
            
            for label_file in os.listdir(os.path.join(self.source_dir, 'labels', 'train')):
                if not label_file.endswith('.txt'):
                    continue
                    
                label_path = os.path.join(self.source_dir, 'labels', 'train', label_file)
                
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                
                has_target_class = False
                for line in lines:
                    if line.strip() and int(line.split()[0]) == class_id:
                        has_target_class = True
                        break
                
                if has_target_class:
                    image_name = label_file.replace('.txt', '.jpg')
                    class_images.append((image_name, label_file))
            
            # 증강 수행
            augmented_count = 0
            attempts = 0
            max_attempts = needed_count * 3  # 실패를 고려한 최대 시도 횟수
            
            while augmented_count < needed_count and attempts < max_attempts:
                # 랜덤하게 이미지 선택
                image_name, label_name = random.choice(class_images)
                
                # 이미지 로드
                image_path = os.path.join(self.source_dir, 'images', 'train', image_name)
                label_path = os.path.join(self.source_dir, 'labels', 'train', label_name)
                
                image = cv2.imread(image_path)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # 라벨 로드
                bboxes, class_labels = self.load_yolo_labels(label_path)
                
                # 증강 수행
                aug_image, aug_bboxes, aug_class_labels = self.augmentor.augment_image(
                    image, bboxes, class_labels
                )
                
                # 타겟 클래스가 여전히 존재하는지 확인
                if class_id in aug_class_labels:
                    # 증강된 이미지 저장
                    aug_image_name = f"aug_{class_id}_{augmented_count}_{image_name}"
                    aug_label_name = f"aug_{class_id}_{augmented_count}_{label_name}"
                    
                    self.save_augmented_data(
                        aug_image, aug_bboxes, aug_class_labels,
                        aug_image_name, aug_label_name
                    )
                    
                    augmented_count += 1
                    
                    if augmented_count % 50 == 0:
                        print(f"클래스 {class_id}: {augmented_count}/{needed_count} 완료")
                
                attempts += 1
            
            print(f"클래스 {class_id} 증강 완료: {augmented_count}개 생성")
    
    def load_yolo_labels(self, label_path):
        """YOLO 형식의 라벨을 로드합니다."""
        bboxes = []
        class_labels = []
        
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if line.strip():
                parts = line.strip().split()
                class_id = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:])
                
                bboxes.append([x_center, y_center, width, height])
                class_labels.append(class_id)
        
        return bboxes, class_labels
    
    def save_augmented_data(self, image, bboxes, class_labels, image_name, label_name):
        """증강된 데이터를 저장합니다."""
        # 이미지 저장
        image_path = os.path.join(self.target_dir, 'images', 'train', image_name)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(image_path, image_bgr)
        
        # 라벨 저장
        label_path = os.path.join(self.target_dir, 'labels', 'train', label_name)
        with open(label_path, 'w') as f:
            for bbox, class_label in zip(bboxes, class_labels):
                f.write(f"{class_label} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
```

### 증강 실행 예제

```python
def run_smart_augmentation():
    """스마트 증강 시스템을 실행합니다."""
    
    # 설정
    source_dir = "yolo_dataset"
    target_dir = "yolo_dataset_augmented"
    target_samples = 800  # 클래스당 목표 샘플 수
    
    # 타겟 디렉토리 생성
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(target_dir, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(target_dir, 'labels', split), exist_ok=True)
    
    # 기존 데이터 복사
    print("기존 데이터 복사 중...")
    for split in ['train', 'val', 'test']:
        for file_type in ['images', 'labels']:
            src_dir = os.path.join(source_dir, file_type, split)
            dst_dir = os.path.join(target_dir, file_type, split)
            
            for file_name in os.listdir(src_dir):
                shutil.copy2(os.path.join(src_dir, file_name), 
                           os.path.join(dst_dir, file_name))
    
    # 스마트 증강 수행
    augmentation_system = SmartAugmentationSystem(
        source_dir, target_dir, target_samples
    )
    
    # 1. 현재 분포 분석
    class_counts = augmentation_system.analyze_class_distribution()
    
    # 2. 증강 계획 수립
    augmentation_plan = augmentation_system.calculate_augmentation_needed(class_counts)
    
    # 3. 증강 수행
    if augmentation_plan:
        augmentation_system.perform_targeted_augmentation(augmentation_plan)
        print("\n모든 클래스 증강 완료!")
    else:
        print("\n증강이 필요한 클래스가 없습니다.")
    
    # 4. data.yaml 복사
    shutil.copy2(os.path.join(source_dir, 'data.yaml'), 
                 os.path.join(target_dir, 'data.yaml'))

if __name__ == "__main__":
    run_smart_augmentation()
```

## 실제 구현 예제

### 완전한 파이프라인

```python
import os
import sys
import argparse
from pathlib import Path

def complete_preprocessing_pipeline(
    raw_images_dir,
    raw_labels_dir,
    output_dir,
    class_names,
    target_samples_per_class=1000,
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1
):
    """완전한 YOLOv10 전처리 파이프라인"""
    
    print("=" * 60)
    print("YOLOv10 데이터 전처리 파이프라인 시작")
    print("=" * 60)
    
    # 1단계: 초기 데이터셋 분할
    print("\n1단계: 데이터셋 분할")
    temp_dir = f"{output_dir}_temp"
    
    splitter = YOLODatasetSplitter(raw_images_dir, raw_labels_dir, temp_dir)
    class_counts = splitter.analyze_dataset()
    train_images, val_images, test_images = splitter.stratified_split(
        train_ratio, val_ratio, test_ratio
    )
    splitter.create_dataset_structure(train_images, val_images, test_images)
    create_data_yaml(temp_dir, class_names)
    
    # 2단계: 증강이 필요한지 확인
    print("\n2단계: 증강 필요성 분석")
    train_class_counts = defaultdict(int)
    
    for label_file in os.listdir(os.path.join(temp_dir, 'labels', 'train')):
        if not label_file.endswith('.txt'):
            continue
            
        label_path = os.path.join(temp_dir, 'labels', 'train', label_file)
        
        with open(label_path, 'r') as f:
            lines = f.readlines()
            
        classes_in_image = set()
        for line in lines:
            if line.strip():
                class_id = int(line.split()[0])
                classes_in_image.add(class_id)
        
        for class_id in classes_in_image:
            train_class_counts[class_id] += 1
    
    needs_augmentation = any(
        count < target_samples_per_class 
        for count in train_class_counts.values()
    )
    
    if needs_augmentation:
        print("증강이 필요합니다. 3단계로 진행...")
        
        # 3단계: 스마트 증강
        print("\n3단계: 스마트 증강 수행")
        augmentation_system = SmartAugmentationSystem(
            temp_dir, output_dir, target_samples_per_class
        )
        
        # 기존 데이터 복사
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(output_dir, 'images', split), exist_ok=True)
            os.makedirs(os.path.join(output_dir, 'labels', split), exist_ok=True)
            
            for file_type in ['images', 'labels']:
                src_dir = os.path.join(temp_dir, file_type, split)
                dst_dir = os.path.join(output_dir, file_type, split)
                
                for file_name in os.listdir(src_dir):
                    shutil.copy2(os.path.join(src_dir, file_name), 
                               os.path.join(dst_dir, file_name))
        
        # 증강 수행
        class_counts = augmentation_system.analyze_class_distribution()
        augmentation_plan = augmentation_system.calculate_augmentation_needed(class_counts)
        
        if augmentation_plan:
            augmentation_system.perform_targeted_augmentation(augmentation_plan)
        
        # data.yaml 복사
        shutil.copy2(os.path.join(temp_dir, 'data.yaml'), 
                     os.path.join(output_dir, 'data.yaml'))
        
        # 임시 디렉토리 삭제
        shutil.rmtree(temp_dir)
        
    else:
        print("증강이 필요하지 않습니다. 기존 분할 결과를 사용합니다.")
        os.rename(temp_dir, output_dir)
    
    # 4단계: 최종 검증
    print("\n4단계: 최종 검증")
    validate_dataset(output_dir)
    
    print("\n" + "=" * 60)
    print("전처리 파이프라인 완료!")
    print(f"결과 디렉토리: {output_dir}")
    print("=" * 60)

def validate_dataset(dataset_dir):
    """데이터셋의 유효성을 검증합니다."""
    
    for split in ['train', 'val', 'test']:
        images_dir = os.path.join(dataset_dir, 'images', split)
        labels_dir = os.path.join(dataset_dir, 'labels', split)
        
        image_files = set(f.replace('.jpg', '').replace('.png', '') 
                         for f in os.listdir(images_dir) 
                         if f.endswith(('.jpg', '.png')))
        
        label_files = set(f.replace('.txt', '') 
                         for f in os.listdir(labels_dir) 
                         if f.endswith('.txt'))
        
        print(f"{split.upper()}: 이미지 {len(image_files)}개, 라벨 {len(label_files)}개")
        
        missing_labels = image_files - label_files
        missing_images = label_files - image_files
        
        if missing_labels:
            print(f"  경고: {len(missing_labels)}개 이미지에 라벨이 없습니다.")
        
        if missing_images:
            print(f"  경고: {len(missing_images)}개 라벨에 이미지가 없습니다.")

# CLI 인터페이스
def main():
    parser = argparse.ArgumentParser(description='YOLOv10 데이터 전처리 파이프라인')
    parser.add_argument('--images', required=True, help='원본 이미지 디렉토리')
    parser.add_argument('--labels', required=True, help='원본 라벨 디렉토리')
    parser.add_argument('--output', required=True, help='출력 디렉토리')
    parser.add_argument('--classes', required=True, nargs='+', help='클래스 이름들')
    parser.add_argument('--target-samples', type=int, default=1000, 
                       help='클래스당 목표 샘플 수')
    parser.add_argument('--train-ratio', type=float, default=0.7, help='훈련 비율')
    parser.add_argument('--val-ratio', type=float, default=0.2, help='검증 비율')
    parser.add_argument('--test-ratio', type=float, default=0.1, help='테스트 비율')
    
    args = parser.parse_args()
    
    complete_preprocessing_pipeline(
        args.images,
        args.labels,
        args.output,
        args.classes,
        args.target_samples,
        args.train_ratio,
        args.val_ratio,
        args.test_ratio
    )

if __name__ == "__main__":
    main()
```

### 사용 예제

```bash
# 기본 실행
python yolo_preprocessing.py \
    --images /path/to/raw/images \
    --labels /path/to/raw/labels \
    --output /path/to/processed/dataset \
    --classes person car bicycle motorbike \
    --target-samples 800

# 비율 조정
python yolo_preprocessing.py \
    --images /path/to/raw/images \
    --labels /path/to/raw/labels \
    --output /path/to/processed/dataset \
    --classes person car bicycle motorbike \
    --target-samples 1200 \
    --train-ratio 0.8 \
    --val-ratio 0.15 \
    --test-ratio 0.05
```

## 모범 사례와 주의사항

### 데이터 품질 관리

1. **라벨 품질 검증**
```python
def validate_label_quality(labels_dir):
    """라벨 품질을 검증합니다."""
    issues = []
    
    for label_file in os.listdir(labels_dir):
        if not label_file.endswith('.txt'):
            continue
            
        label_path = os.path.join(labels_dir, label_file)
        
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
                
            parts = line.strip().split()
            if len(parts) != 5:
                issues.append(f"{label_file}:{line_num} - 잘못된 형식")
                continue
            
            try:
                class_id = int(parts[0])
                coords = [float(x) for x in parts[1:]]
                
                # 좌표 범위 검증
                for coord in coords:
                    if not 0 <= coord <= 1:
                        issues.append(f"{label_file}:{line_num} - 좌표 범위 오류")
                        break
                
            except ValueError:
                issues.append(f"{label_file}:{line_num} - 데이터 타입 오류")
    
    return issues
```

2. **이미지-라벨 매칭 확인**
```python
def check_image_label_matching(images_dir, labels_dir):
    """이미지와 라벨 파일의 매칭을 확인합니다."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    image_files = {os.path.splitext(f)[0] for f in os.listdir(images_dir) 
                   if os.path.splitext(f)[1].lower() in image_extensions}
    
    label_files = {os.path.splitext(f)[0] for f in os.listdir(labels_dir) 
                   if f.endswith('.txt')}
    
    missing_labels = image_files - label_files
    missing_images = label_files - image_files
    
    return missing_labels, missing_images
```

### 증강 시 주의사항

1. **과도한 증강 방지**: 너무 많은 증강은 오히려 성능을 저하시킬 수 있습니다.
2. **현실적인 증강**: 실제 환경에서 발생할 수 있는 변형만 적용해야 합니다.
3. **바운딩 박스 보존**: 증강 후에도 객체의 바운딩 박스가 올바르게 유지되는지 확인해야 합니다.

### 성능 최적화

1. **병렬 처리**
```python
from multiprocessing import Pool
import functools

def parallel_augmentation(image_paths, num_processes=4):
    """병렬 처리를 통한 증강 최적화"""
    with Pool(num_processes) as pool:
        results = pool.map(augment_single_image, image_paths)
    return results
```

2. **메모리 효율성**
```python
def memory_efficient_processing(dataset_dir, batch_size=32):
    """메모리 효율적인 배치 처리"""
    image_paths = list(Path(dataset_dir).glob('**/*.jpg'))
    
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        process_batch(batch_paths)
        # 배치 처리 후 메모리 정리
        gc.collect()
```

## 결론

YOLOv10의 성공적인 학습을 위해서는 체계적인 데이터 전처리가 필수입니다. 이번 포스트에서 다룬 내용을 요약하면:

1. **균등 분할**: 클래스별로 균등하게 train/validation/test 데이터를 분할
2. **스마트 증강**: 데이터 부족 시 타겟된 증강을 통한 클래스 균형 맞추기
3. **품질 관리**: 라벨 품질 검증과 이미지-라벨 매칭 확인
4. **자동화**: 전체 파이프라인을 자동화하여 재사용성 향상

이러한 전처리 과정을 통해 더 안정적이고 성능이 좋은 YOLOv10 모델을 학습할 수 있습니다. 실제 프로젝트에서는 데이터의 특성에 맞게 파라미터를 조정하고, 도메인 특화된 증강 기법을 추가로 적용하는 것이 좋습니다.

---

**참고 자료:**
- [YOLOv10 공식 문서](https://github.com/THU-MIG/yolov10)
- [Albumentations 라이브러리](https://albumentations.ai/)
- [객체 탐지 데이터 증강 모범 사례](https://blog.roboflow.com/why-and-how-to-implement-random-rotate-data-augmentation/)
