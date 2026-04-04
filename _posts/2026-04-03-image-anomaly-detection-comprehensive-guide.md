---
layout: post
title: "이미지 이상 감지 완벽 가이드: 데이터 준비부터 성능 평가까지"
date: 2026-04-03 10:00:00 +0900
categories: [AI, Computer Vision, Anomaly Detection, Deep Learning]
tags: [anomaly-detection, image-processing, autoencoder, PatchCore, PaDiM, AUROC, pytorch, computer-vision, unsupervised-learning]
description: "이미지 이상 감지(Image Anomaly Detection)의 전 과정을 다룹니다. 데이터 수집과 전처리부터 모델 학습, 실서비스 추론, 성능 최적화 및 평가 방법까지 실용적인 코드와 함께 완전히 설명합니다."
image: "/assets/img/posts/2026-04-03-image-anomaly-detection-comprehensive-guide.webp"
---

## 📌 이미지 이상 감지란?

이미지 이상 감지(Image Anomaly Detection)는 **정상(Normal) 샘플만으로 학습한 모델이 본 적 없는 이상(Abnormal) 패턴을 탐지**하는 기술입니다. 불량 제품 검사, 의료 영상 분석, 보안 감시, 인프라 시설 점검 등 레이블된 이상 데이터를 충분히 확보하기 어려운 모든 도메인에서 핵심 솔루션으로 자리잡고 있습니다.

전통적인 분류 모델(Classifier)과 달리 이상 감지 모델은 다음과 같은 특성을 가집니다.

```
전통 분류 모델 vs 이상 감지 모델
┌────────────────────┬──────────────────────────┬─────────────────────────────┐
│       구분         │     전통 분류 모델        │       이상 감지 모델        │
├────────────────────┼──────────────────────────┼─────────────────────────────┤
│  학습 데이터       │  정상 + 이상 레이블 필요  │  정상 데이터만으로 학습     │
│  이상 유형 대응    │  학습된 클래스만 탐지     │  미지의 이상도 탐지 가능    │
│  데이터 수집 난이도│  어려움 (이상 수집)       │  상대적으로 쉬움            │
│  결과 형태         │  클래스 레이블            │  이상 점수 + 히트맵         │
│  대표 활용 분야    │  품질 분류, 진단          │  불량 검사, 이상 탐지       │
└────────────────────┴──────────────────────────┴─────────────────────────────┘
```

이 포스트에서는 이상 감지의 전 파이프라인을 **데이터 준비 → 모델 선택 및 학습 → 실서비스 추론 → 성능 확보 → 성능 평가** 순서로 실용적인 코드와 함께 다루겠습니다.

---

## 📂 1단계: 데이터 준비

이상 감지에서 데이터 준비는 모델 품질을 결정하는 가장 중요한 단계입니다. 학습은 오직 정상 데이터만으로 이루어지므로, **정상 샘플의 품질과 다양성**이 모델의 일반화 성능을 직접 좌우합니다.

### 1.1 데이터셋 구조 설계

실무에서 권장하는 디렉터리 구조는 MVTec AD 벤치마크 데이터셋의 관례를 따릅니다.

```
dataset/
├── train/
│   └── good/          # 정상 이미지만 학습에 사용
│       ├── 0001.png
│       ├── 0002.png
│       └── ...
└── test/
    ├── good/          # 정상 테스트 이미지
    │   ├── 0001.png
    │   └── ...
    ├── crack/         # 이상 유형 1: 균열
    │   ├── 0001.png
    │   └── ...
    ├── scratch/       # 이상 유형 2: 스크래치
    └── contamination/ # 이상 유형 3: 오염
```

```python
import os
import shutil
from pathlib import Path

def build_dataset_structure(raw_dir: str, output_dir: str, train_ratio: float = 0.8):
    """
    원시 데이터에서 이상 감지용 데이터셋 구조 자동 생성
    raw_dir 하위에 good/, defect/ 폴더가 있다고 가정
    """
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)

    good_images = list((raw_dir / "good").glob("*.[jp][pn]g"))
    defect_images = list((raw_dir / "defect").glob("*.[jp][pn]g"))

    split_idx = int(len(good_images) * train_ratio)
    train_good = good_images[:split_idx]
    test_good = good_images[split_idx:]

    # 학습: 정상만
    for img in train_good:
        dest = output_dir / "train" / "good" / img.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, dest)

    # 테스트: 정상
    for img in test_good:
        dest = output_dir / "test" / "good" / img.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, dest)

    # 테스트: 이상 (레이블별 분류)
    for img in defect_images:
        label = img.stem.split("_")[0]  # 파일명 규칙: {label}_{idx}.png
        dest = output_dir / "test" / label / img.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, dest)

    print(f"✅ Train Good: {len(train_good)}")
    print(f"✅ Test Good: {len(test_good)}")
    print(f"✅ Test Defect: {len(defect_images)}")
```

### 1.2 데이터 품질 검증

학습 데이터에 이상 이미지가 섞여 있으면 모델 성능이 급격히 저하됩니다. 수집 직후 반드시 품질 검증을 수행해야 합니다.

```python
import cv2
import numpy as np
from pathlib import Path
from sklearn.ensemble import IsolationForest
from torchvision import models, transforms
import torch

class DataQualityChecker:
    """
    수집된 정상 이미지의 품질 및 오염 여부 자동 검사
    """
    def __init__(self, threshold_blur: float = 100.0, threshold_outlier: float = 0.05):
        self.threshold_blur = threshold_blur
        self.threshold_outlier = threshold_outlier
        self.feature_extractor = self._build_extractor()

    def _build_extractor(self):
        """EfficientNet-B0으로 특징 추출 (ImageNet 사전학습)"""
        model = models.efficientnet_b0(weights="IMAGENET1K_V1")
        model.classifier = torch.nn.Identity()
        model.eval()
        return model

    def check_blur(self, img_path: str) -> float:
        """라플라시안 분산으로 블러 점수 계산 (낮을수록 블러)"""
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        return float(cv2.Laplacian(img, cv2.CV_64F).var())

    def extract_features(self, img_paths: list) -> np.ndarray:
        """사전학습 모델로 이미지 특징 벡터 일괄 추출"""
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        features = []
        with torch.no_grad():
            for path in img_paths:
                img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
                tensor = transform(img).unsqueeze(0)
                feat = self.feature_extractor(tensor).squeeze().numpy()
                features.append(feat)
        return np.array(features)

    def find_outliers(self, img_paths: list) -> list:
        """Isolation Forest로 분포 이탈 샘플(잠재적 오염) 탐지"""
        features = self.extract_features(img_paths)
        clf = IsolationForest(contamination=self.threshold_outlier, random_state=42)
        preds = clf.fit_predict(features)
        outliers = [img_paths[i] for i, p in enumerate(preds) if p == -1]
        return outliers

    def run(self, good_dir: str):
        good_dir = Path(good_dir)
        img_paths = [str(p) for p in good_dir.glob("*.[jp][pn]g")]

        # 1. 블러 검사
        blurry = [p for p in img_paths if self.check_blur(p) < self.threshold_blur]
        print(f"⚠️  블러 의심 이미지 {len(blurry)}장: {blurry[:5]}")

        # 2. 분포 이탈 검사
        outliers = self.find_outliers(img_paths)
        print(f"⚠️  분포 이탈 의심 이미지 {len(outliers)}장: {outliers[:5]}")

        print(f"\n✅ 전체 {len(img_paths)}장 중 검토 필요: {len(set(blurry + outliers))}장")
        return blurry, outliers
```

### 1.3 이미지 전처리 파이프라인

모든 이미지는 같은 크기·색상·정규화 기준으로 변환되어야 합니다. 특히 산업 검사 환경에서는 조명과 카메라 위치를 고정하는 것이 가장 효과적인 전처리입니다.

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2

class AnomalyTransform:
    """
    이상 감지 전용 전처리/증강 파이프라인
    - Train: 정상 다양성 확보를 위한 보수적 증강
    - Test/Inference: 결정론적 변환만 적용
    """

    @staticmethod
    def train_transform(image_size: int = 256):
        return A.Compose([
            A.Resize(image_size, image_size),
            # 이상 감지에서는 형태를 바꾸는 강한 증강은 금지
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.3),
            A.Rotate(limit=15, p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.1, contrast_limit=0.1, p=0.5),
            A.GaussNoise(var_limit=(5, 20), p=0.3),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])

    @staticmethod
    def test_transform(image_size: int = 256):
        return A.Compose([
            A.Resize(image_size, image_size),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])
```

> **증강 주의사항**: CutOut, Mosaic, 극단적인 Color Jitter 등 이미지의 **구조나 텍스처를 크게 변형**하는 증강은 모델이 이상 패턴을 정상으로 학습하게 만들 수 있으므로 사용하지 않습니다.

---

## 🧠 2단계: 모델 선택과 학습

이상 감지에는 다양한 접근 방식이 있습니다. 데이터 규모, 필요한 추론 속도, 픽셀 단위 위치 표시(Localization) 여부에 따라 최적의 방법이 달라집니다.

### 2.1 주요 알고리즘 비교

```
이상 감지 알고리즘 비교
┌───────────────┬──────────────┬────────────┬─────────────┬─────────────────────┐
│   알고리즘    │   AUROC      │  속도      │  Localize   │   특징              │
├───────────────┼──────────────┼────────────┼─────────────┼─────────────────────┤
│  Autoencoder  │  ~85%        │  빠름      │  가능(재구성)│ 구조 간단, 학습 쉬움│
│  VAE          │  ~87%        │  빠름      │  가능        │ 잠재 공간 불확실성  │
│  PaDiM        │  ~97%        │  빠름      │  가능        │ 특징 분포 모델링    │
│  PatchCore    │  ~98%        │  중간      │  가능        │ 메모리뱅크 기반     │
│  EfficientAD  │  ~98%        │  매우 빠름 │  가능        │ 경량화 최적화       │
│  SimpleNet    │  ~99%        │  빠름      │  가능        │ 최신 SOTA           │
└───────────────┴──────────────┴────────────┴─────────────┴─────────────────────┘
```

### 2.2 Autoencoder 기반 이상 감지

가장 직관적인 방법입니다. 정상 이미지만으로 학습하여 원본을 잘 복원하도록 훈련하면, 이상 이미지는 잘 복원되지 않아 재구성 오차가 높아집니다.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvAutoEncoder(nn.Module):
    """
    Conv-기반 Autoencoder: 정상 이미지 재구성 학습
    입력: (B, 3, H, W)  →  재구성: (B, 3, H, W)
    """
    def __init__(self, latent_dim: int = 512):
        super().__init__()

        # Encoder
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, 4, 2, 1),   # 256 -> 128
            nn.BatchNorm2d(32), nn.LeakyReLU(0.2),
            nn.Conv2d(32, 64, 4, 2, 1),  # 128 -> 64
            nn.BatchNorm2d(64), nn.LeakyReLU(0.2),
            nn.Conv2d(64, 128, 4, 2, 1), # 64 -> 32
            nn.BatchNorm2d(128), nn.LeakyReLU(0.2),
            nn.Conv2d(128, 256, 4, 2, 1),# 32 -> 16
            nn.BatchNorm2d(256), nn.LeakyReLU(0.2),
        )
        self.flatten_dim = 256 * 16 * 16
        self.fc_enc = nn.Linear(self.flatten_dim, latent_dim)
        self.fc_dec = nn.Linear(latent_dim, self.flatten_dim)

        # Decoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 4, 2, 1),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 4, 2, 1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, 2, 1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.ConvTranspose2d(32, 3, 4, 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        feat = self.encoder(x).view(-1, self.flatten_dim)
        z = self.fc_enc(feat)
        dec_feat = self.fc_dec(z).view(-1, 256, 16, 16)
        return self.decoder(dec_feat)

    def anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """픽셀별 재구성 오차를 이상 점수 히트맵으로 반환"""
        recon = self.forward(x)
        return F.mse_loss(recon, x, reduction="none").mean(dim=1)  # (B, H, W)
```

### 2.3 PatchCore (실무 권장)

PatchCore는 사전학습된 CNN의 패치 수준 특징을 Coreset으로 압축한 메모리 뱅크를 구축하여, 추론 시 최근방 이웃(kNN) 거리를 이상 점수로 사용합니다. MVTec AD 기준 98% 이상의 AUROC를 달성하는 현재 산업 현장에서 가장 많이 사용되는 방법입니다.

```python
import faiss
import numpy as np
import torch
import torch.nn as nn
from torchvision import models
from tqdm import tqdm

class PatchCore:
    """
    PatchCore 이상 감지 구현
    - Backbone: Wide ResNet-50 (사전학습 고정)
    - 메모리 뱅크: Coreset 서브샘플링으로 압축
    - 이상 점수: 패치별 kNN 최소 거리의 최댓값
    """

    def __init__(self, backbone: str = "wide_resnet50_2", device: str = "cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.patch_lib = []
        self.model = self._build_backbone(backbone)

    def _build_backbone(self, backbone_name: str) -> nn.Module:
        model = getattr(models, backbone_name)(weights="IMAGENET1K_V1")
        # layer2, layer3 특징을 동시에 사용 (다중 스케일 패치)
        model.eval()
        for param in model.parameters():
            param.requires_grad = False
        return model.to(self.device)

    def _extract_features(self, dataloader) -> torch.Tensor:
        """layer2 + layer3 중간 특징 추출 후 adaptive pooling으로 동일 크기 맞춤"""
        features = []
        hooks = []
        layer_outputs = {}

        def hook_fn(name):
            def fn(_, __, output):
                layer_outputs[name] = output
            return fn

        hooks.append(self.model.layer2.register_forward_hook(hook_fn("layer2")))
        hooks.append(self.model.layer3.register_forward_hook(hook_fn("layer3")))

        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Feature extraction"):
                imgs = batch[0].to(self.device) if isinstance(batch, (list, tuple)) else batch.to(self.device)
                self.model(imgs)

                # 두 레이어 특징을 같은 해상도로 맞추고 채널 방향 concat
                f2 = F.adaptive_avg_pool2d(layer_outputs["layer2"], (28, 28))
                f3 = F.adaptive_avg_pool2d(layer_outputs["layer3"], (28, 28))
                patch_feat = torch.cat([f2, f3], dim=1)  # (B, C2+C3, 28, 28)

                B, C, H, W = patch_feat.shape
                # 패치 단위로 펼치기: (B*H*W, C)
                patch_feat = patch_feat.permute(0, 2, 3, 1).reshape(-1, C)
                features.append(patch_feat.cpu())

        for h in hooks:
            h.remove()

        return torch.cat(features, dim=0)

    def fit(self, dataloader, coreset_ratio: float = 0.1):
        """정상 데이터로 메모리 뱅크 구축"""
        print("📦 [1/2] 정상 데이터 특징 추출 중...")
        all_features = self._extract_features(dataloader)

        print(f"📦 [2/2] Coreset 서브샘플링 ({coreset_ratio*100:.0f}%)...")
        n_samples = int(len(all_features) * coreset_ratio)
        indices = torch.randperm(len(all_features))[:n_samples]
        self.memory_bank = all_features[indices].numpy()

        # FAISS IVF 인덱스 구축 (고속 kNN 검색)
        dim = self.memory_bank.shape[1]
        quantizer = faiss.IndexFlatL2(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, 100)
        self.index.train(self.memory_bank)
        self.index.add(self.memory_bank)
        self.index.nprobe = 10
        print(f"✅ 메모리 뱅크 구축 완료: {len(self.memory_bank):,}개 패치")

    def predict(self, img_tensor: torch.Tensor) -> tuple:
        """
        단일 이미지에 대한 이상 점수 및 히트맵 반환
        Returns:
            score (float): 이미지 레벨 이상 점수
            heatmap (np.ndarray): 픽셀 수준 이상 히트맵
        """
        layer_outputs = {}
        hooks = []

        def hook_fn(name):
            def fn(_, __, output):
                layer_outputs[name] = output
            return fn

        hooks.append(self.model.layer2.register_forward_hook(hook_fn("layer2")))
        hooks.append(self.model.layer3.register_forward_hook(hook_fn("layer3")))

        with torch.no_grad():
            self.model(img_tensor.unsqueeze(0).to(self.device))

        for h in hooks:
            h.remove()

        f2 = F.adaptive_avg_pool2d(layer_outputs["layer2"], (28, 28))
        f3 = F.adaptive_avg_pool2d(layer_outputs["layer3"], (28, 28))
        patch_feat = torch.cat([f2, f3], dim=1)  # (1, C, 28, 28)

        B, C, H, W = patch_feat.shape
        patches = patch_feat.permute(0, 2, 3, 1).reshape(-1, C).cpu().numpy()

        # kNN 거리로 이상 점수 계산
        distances, _ = self.index.search(patches, k=1)
        patch_scores = distances[:, 0].reshape(H, W)

        # 이미지 레벨 점수: 패치 이상 점수의 최댓값
        score = float(patch_scores.max())

        # 원본 해상도로 업샘플링한 히트맵
        heatmap = cv2.resize(patch_scores, (img_tensor.shape[-1], img_tensor.shape[-2]))
        return score, heatmap
```

### 2.4 학습 루프

```python
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

def train_patchcore(data_dir: str, image_size: int = 256, batch_size: int = 32):
    """PatchCore 학습 진입점"""
    transform = AnomalyTransform.train_transform(image_size)

    def albumentations_wrapper(img):
        import numpy as np
        img_np = np.array(img)
        return transform(image=img_np)["image"]

    dataset = ImageFolder(root=f"{data_dir}/train", transform=albumentations_wrapper)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=4)

    model = PatchCore(device="cuda")
    model.fit(dataloader, coreset_ratio=0.1)

    # 모델 저장 (메모리 뱅크 + FAISS 인덱스)
    import pickle
    with open("patchcore_model.pkl", "wb") as f:
        pickle.dump({"memory_bank": model.memory_bank}, f)
    faiss.write_index(model.index, "patchcore.faiss")
    print("✅ 모델 저장 완료")
    return model
```

---

## 🚀 3단계: 실서비스 추론

학습된 모델을 프로덕션 환경에서 안전하게 사용하려면 **임계값 설정, 배치 처리, API 서빙** 등의 구성이 필요합니다.

### 3.1 임계값(Threshold) 결정

임계값은 정상/이상을 나누는 기준선입니다. **검증 세트의 정상 샘플 점수 분포**를 기반으로 설정합니다.

```python
import numpy as np
from scipy import stats

class ThresholdCalibrator:
    """
    정상 분포 기반 임계값 자동 설정
    """
    def fit(self, normal_scores: np.ndarray, method: str = "percentile", fp_rate: float = 0.01):
        """
        Args:
            normal_scores: 검증 세트 정상 이미지들의 이상 점수
            method: 임계값 결정 방식
                - 'percentile': 상위 fp_rate% 분위수
                - 'gaussian': 가우시안 가정 하 3-sigma
                - 'kde': 커널 밀도 추정
            fp_rate: False Positive 허용 비율
        """
        self.normal_scores = normal_scores

        if method == "percentile":
            self.threshold = np.percentile(normal_scores, (1 - fp_rate) * 100)

        elif method == "gaussian":
            mu, sigma = normal_scores.mean(), normal_scores.std()
            self.threshold = mu + stats.norm.ppf(1 - fp_rate) * sigma

        elif method == "kde":
            kde = stats.gaussian_kde(normal_scores)
            x = np.linspace(normal_scores.min(), normal_scores.max(), 1000)
            cdf = np.cumsum(kde(x)) / np.sum(kde(x))
            self.threshold = x[np.searchsorted(cdf, 1 - fp_rate)]

        print(f"✅ 임계값 설정 완료: {self.threshold:.4f} (방법: {method}, FP 허용율: {fp_rate*100:.1f}%)")
        return self.threshold

    def predict(self, score: float) -> dict:
        return {
            "score": round(score, 4),
            "is_anomaly": bool(score > self.threshold),
            "confidence": round(min((score / self.threshold), 2.0), 4),
        }
```

### 3.2 FastAPI 기반 추론 서버

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import faiss
import pickle
import torch
import io
from PIL import Image

app = FastAPI(title="Image Anomaly Detection API", version="1.0.0")

# 서버 시작 시 모델 로드
@app.on_event("startup")
async def load_model():
    global detector, calibrator, transform

    with open("patchcore_model.pkl", "rb") as f:
        data = pickle.load(f)

    detector = PatchCore(device="cpu")
    detector.memory_bank = data["memory_bank"]
    detector.index = faiss.read_index("patchcore.faiss")

    # 임계값 로드
    with open("threshold.pkl", "rb") as f:
        calibrator = pickle.load(f)

    transform = AnomalyTransform.test_transform(256)
    print("✅ 모델 로드 완료")


@app.post("/predict")
async def predict_anomaly(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    img_array = np.frombuffer(contents, dtype=np.uint8)
    img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise HTTPException(status_code=400, detail="이미지 디코딩 실패")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_tensor = transform(image=img_rgb)["image"]

    score, heatmap = detector.predict(img_tensor)
    result = calibrator.predict(score)

    return JSONResponse({
        "filename": file.filename,
        "anomaly_score": result["score"],
        "is_anomaly": result["is_anomaly"],
        "confidence": result["confidence"],
        "threshold": round(calibrator.threshold, 4),
    })


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

### 3.3 배치 추론 (대용량 처리)

```python
from torch.utils.data import DataLoader, Dataset
from pathlib import Path
import pandas as pd

class InferenceDataset(Dataset):
    def __init__(self, img_dir: str, transform):
        self.paths = list(Path(img_dir).glob("*.[jp][pn]g"))
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        img = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
        return self.transform(image=img)["image"], str(path)


def batch_inference(img_dir: str, model: PatchCore, calibrator: ThresholdCalibrator,
                    batch_size: int = 32, num_workers: int = 4) -> pd.DataFrame:
    """폴더 내 전체 이미지에 대한 일괄 추론"""
    transform = AnomalyTransform.test_transform()
    dataset = InferenceDataset(img_dir, transform)
    loader = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers)

    results = []
    for imgs, paths in tqdm(loader, desc="Batch inference"):
        for img, path in zip(imgs, paths):
            score, _ = model.predict(img)
            result = calibrator.predict(score)
            results.append({"path": path, **result})

    df = pd.DataFrame(results)
    df.to_csv("inference_results.csv", index=False)
    print(f"✅ 추론 완료: {len(df)}장, 이상 감지: {df['is_anomaly'].sum()}장")
    return df
```

---

## ⚡ 4단계: 성능 확보 전략

높은 정확도를 달성하기 위해 적용할 수 있는 핵심 전략들을 정리합니다.

### 4.1 Backbone 선택 전략

사전학습 모델의 품질이 PatchCore 성능을 크게 좌우합니다. 일반적으로 ImageNet 분류 정확도가 높은 모델보다 **표현력이 풍부한 중간 레이어 특징**을 가진 모델이 이상 감지에 유리합니다.

```python
# Backbone별 MVTec AD 평균 AUROC 비교 (참고값)
backbone_benchmark = {
    "ResNet-18":        {"auroc": 0.943, "speed_ms": 8,  "params_M": 11.7},
    "Wide_ResNet-50-2": {"auroc": 0.975, "speed_ms": 15, "params_M": 68.9},
    "EfficientNet-B4":  {"auroc": 0.971, "speed_ms": 12, "params_M": 19.3},
    "ViT-B/16":         {"auroc": 0.983, "speed_ms": 22, "params_M": 86.6},
    "DINOv2-B":         {"auroc": 0.988, "speed_ms": 20, "params_M": 86.6},
}

# 추천 선택 기준
# - 실시간 < 20ms 필요: EfficientNet-B4
# - 최고 정확도 우선: DINOv2-B
# - 균형: Wide_ResNet-50-2 (오랜 검증 기반)
```

### 4.2 Multi-Scale 앙상블

단일 레이어 특징 대신 여러 레이어의 특징을 결합하면 미세 결점과 큰 결점을 동시에 포착할 수 있습니다.

```python
def extract_multiscale_features(model, img_tensor, layers=("layer2", "layer3"), target_size=(28, 28)):
    """
    지정된 여러 레이어에서 패치 특징을 추출하고 동일 해상도로 맞춰 결합
    """
    outputs = {}
    hooks = []

    for name in layers:
        layer = dict(model.named_modules())[name]
        def make_hook(n):
            def fn(_, __, out): outputs[n] = out
            return fn
        hooks.append(layer.register_forward_hook(make_hook(name)))

    with torch.no_grad():
        model(img_tensor.unsqueeze(0))

    for h in hooks:
        h.remove()

    resized = [F.adaptive_avg_pool2d(outputs[n], target_size) for n in layers]
    return torch.cat(resized, dim=1)  # 채널 방향 결합
```

### 4.3 도메인 미세조정(Domain Adaptation)

자체 데이터에 맞게 Backbone 특징을 미세조정하면 AUROC를 추가로 1~3% 향상시킬 수 있습니다.

```python
class FeatureAdaptationHead(nn.Module):
    """
    Backbone 특징을 도메인에 맞게 정제하는 경량 어댑터 (Backbone은 고정)
    """
    def __init__(self, in_channels: int, bottleneck_dim: int = 128):
        super().__init__()
        self.adapter = nn.Sequential(
            nn.Conv2d(in_channels, bottleneck_dim, 1),
            nn.BatchNorm2d(bottleneck_dim),
            nn.ReLU(),
            nn.Conv2d(bottleneck_dim, in_channels, 1),
        )

    def forward(self, x):
        return x + self.adapter(x)  # Residual 연결로 안정적인 미세조정


# 어댑터 학습 (정상 데이터만 사용, Reconstruction loss)
def train_adapter(adapter, normal_loader, epochs=10, lr=1e-4):
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=lr)
    for epoch in range(epochs):
        total_loss = 0
        for batch in normal_loader:
            imgs = batch[0].cuda()
            with torch.no_grad():
                feats = extract_backbone_features(imgs)  # Backbone 고정
            adapted = adapter(feats)
            loss = F.mse_loss(adapted, feats)  # 정상 특징을 잘 재구성하도록
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{epochs} Loss: {total_loss/len(normal_loader):.4f}")
```

### 4.4 추론 속도 최적화

프로덕션 환경에서 수용 가능한 지연시간을 확보하기 위한 기법들입니다.

```python
# ① TorchScript 변환으로 Python 오버헤드 제거
scripted_backbone = torch.jit.script(backbone)

# ② ONNX 변환 + ONNX Runtime 추론
import onnx, onnxruntime as ort

torch.onnx.export(
    backbone,
    dummy_input,
    "backbone.onnx",
    opset_version=17,
    input_names=["input"],
    output_names=["features"],
    dynamic_axes={"input": {0: "batch_size"}, "features": {0: "batch_size"}},
)

ort_session = ort.InferenceSession("backbone.onnx", providers=["CUDAExecutionProvider"])

def onnx_infer(img_np: np.ndarray) -> np.ndarray:
    return ort_session.run(None, {"input": img_np})[0]

# ③ INT8 양자화 (CPU 추론 속도 2~4배 향상)
from torch.quantization import quantize_dynamic

quantized_backbone = quantize_dynamic(
    backbone_cpu,
    {nn.Linear, nn.Conv2d},
    dtype=torch.qint8
)

# ④ FAISS GPU 인덱스 (kNN 검색 속도 10배 이상 향상)
res = faiss.StandardGpuResources()
gpu_index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
```

---

## 📊 5단계: 성능 평가

이상 감지 모델의 성능은 일반 분류 모델과 다른 관점에서 평가해야 합니다. 특히 **이미지 레벨 탐지 성능**과 **픽셀 레벨 위치 특정 성능**을 분리하여 측정하는 것이 중요합니다.

### 5.1 주요 평가 지표

```
이상 감지 평가 지표 정리
┌──────────────┬─────────────────────────────────────────────────────┐
│    지표      │                     설명                           │
├──────────────┼─────────────────────────────────────────────────────┤
│  AUROC       │ ROC 곡선 아래 면적. 임계값 독립적 전체 성능 지표   │
│  AUPR        │ Precision-Recall 곡선 아래 면적. 불균형 데이터 적합│
│  F1-Score    │ Precision/Recall 조화평균. 임계값 의존적           │
│  PRO-score   │ 픽셀 단위 Localization 성능 (Per-Region Overlap)  │
│  FPS         │ 초당 처리 프레임 수. 실시간 요건 충족 여부        │
│  Threshold   │ 임계값별 FPR·TPR Trade-off                        │
└──────────────┴─────────────────────────────────────────────────────┘
```

### 5.2 종합 평가 클래스

```python
import numpy as np
from sklearn.metrics import (
    roc_auc_score, roc_curve,
    average_precision_score, precision_recall_curve,
    f1_score, confusion_matrix, classification_report,
)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

class AnomalyEvaluator:
    """
    이상 감지 모델 종합 평가 도구
    - 이미지 레벨: AUROC, AUPR, F1, Confusion Matrix
    - 픽셀 레벨: PRO-score, Pixel-AUROC
    """

    def __init__(self, scores: np.ndarray, labels: np.ndarray,
                 pixel_scores: np.ndarray = None, pixel_masks: np.ndarray = None):
        """
        Args:
            scores:       이미지 레벨 이상 점수 배열 (N,)
            labels:       이미지 레벨 정답 (0=정상, 1=이상) 배열 (N,)
            pixel_scores: 픽셀 레벨 이상 히트맵 배열 (N, H, W), 선택
            pixel_masks:  픽셀 레벨 정답 마스크 배열 (N, H, W), 선택
        """
        self.scores = scores
        self.labels = labels
        self.pixel_scores = pixel_scores
        self.pixel_masks = pixel_masks

    # ──────────────── 이미지 레벨 ────────────────

    def image_auroc(self) -> float:
        return roc_auc_score(self.labels, self.scores)

    def image_aupr(self) -> float:
        return average_precision_score(self.labels, self.scores)

    def best_f1(self) -> tuple:
        """임계값 탐색으로 최적 F1 반환"""
        precisions, recalls, thresholds = precision_recall_curve(self.labels, self.scores)
        f1s = 2 * precisions * recalls / (precisions + recalls + 1e-8)
        best_idx = np.argmax(f1s)
        return float(f1s[best_idx]), float(thresholds[best_idx])

    def confusion_matrix_report(self, threshold: float) -> dict:
        preds = (self.scores >= threshold).astype(int)
        cm = confusion_matrix(self.labels, preds)
        tn, fp, fn, tp = cm.ravel()
        return {
            "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn),
            "Precision": round(tp / (tp + fp + 1e-8), 4),
            "Recall (TPR)":  round(tp / (tp + fn + 1e-8), 4),
            "Specificity":   round(tn / (tn + fp + 1e-8), 4),
            "F1": round(2*tp / (2*tp + fp + fn + 1e-8), 4),
        }

    # ──────────────── 픽셀 레벨 ────────────────

    def pixel_auroc(self) -> float:
        """히트맵 vs 정답 마스크로 픽셀 단위 AUROC 계산"""
        assert self.pixel_scores is not None and self.pixel_masks is not None
        flat_scores = self.pixel_scores[self.labels == 1].flatten()
        flat_masks  = self.pixel_masks[self.labels == 1].flatten().astype(int)
        return roc_auc_score(flat_masks, flat_scores)

    def pro_score(self, num_thresholds: int = 100) -> float:
        """
        Per-Region Overlap (PRO) Score
        각 이상 영역(connected component)에 대한 IoU 평균
        """
        import cv2
        assert self.pixel_scores is not None and self.pixel_masks is not None

        thresholds = np.linspace(self.pixel_scores.min(), self.pixel_scores.max(), num_thresholds)
        anomaly_indices = np.where(self.labels == 1)[0]
        pro_values = []

        for thresh in thresholds:
            per_image_overlap = []
            for idx in anomaly_indices:
                pred_mask = (self.pixel_scores[idx] >= thresh).astype(np.uint8)
                gt_mask   = self.pixel_masks[idx].astype(np.uint8)

                n_comps, comp_labels = cv2.connectedComponents(gt_mask)
                for comp_id in range(1, n_comps):
                    region = (comp_labels == comp_id)
                    overlap = (pred_mask[region].sum()) / (region.sum() + 1e-8)
                    per_image_overlap.append(overlap)

            if per_image_overlap:
                pro_values.append(np.mean(per_image_overlap))

        return float(np.mean(pro_values)) if pro_values else 0.0

    # ──────────────── 시각화 ────────────────

    def plot_full_report(self, threshold: float = None, save_path: str = None):
        """AUROC, PR 곡선, Confusion Matrix, 점수 분포를 한 화면에 시각화"""
        fig = plt.figure(figsize=(18, 12))
        gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

        # 1. ROC Curve
        ax1 = fig.add_subplot(gs[0, 0])
        fpr, tpr, _ = roc_curve(self.labels, self.scores)
        auroc = self.image_auroc()
        ax1.plot(fpr, tpr, "b-", lw=2, label=f"AUROC = {auroc:.4f}")
        ax1.plot([0, 1], [0, 1], "k--", lw=1)
        ax1.set(xlabel="False Positive Rate", ylabel="True Positive Rate", title="ROC Curve")
        ax1.legend(loc="lower right")

        # 2. PR Curve
        ax2 = fig.add_subplot(gs[0, 1])
        prec, rec, _ = precision_recall_curve(self.labels, self.scores)
        aupr = self.image_aupr()
        ax2.plot(rec, prec, "g-", lw=2, label=f"AUPR = {aupr:.4f}")
        ax2.set(xlabel="Recall", ylabel="Precision", title="Precision-Recall Curve")
        ax2.legend(loc="upper right")

        # 3. Score Distribution
        ax3 = fig.add_subplot(gs[0, 2])
        normal_scores  = self.scores[self.labels == 0]
        anomaly_scores = self.scores[self.labels == 1]
        ax3.hist(normal_scores,  bins=50, alpha=0.7, color="blue",   label="Normal")
        ax3.hist(anomaly_scores, bins=50, alpha=0.7, color="red",    label="Anomaly")
        if threshold:
            ax3.axvline(threshold, color="black", linestyle="--", label=f"Threshold={threshold:.3f}")
        ax3.set(xlabel="Anomaly Score", ylabel="Count", title="Score Distribution")
        ax3.legend()

        # 4. Confusion Matrix
        if threshold:
            ax4 = fig.add_subplot(gs[1, 0])
            preds = (self.scores >= threshold).astype(int)
            cm = confusion_matrix(self.labels, preds)
            im = ax4.imshow(cm, cmap="Blues")
            for i in range(2):
                for j in range(2):
                    ax4.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=14)
            ax4.set(xticks=[0, 1], yticks=[0, 1],
                    xticklabels=["Normal", "Anomaly"],
                    yticklabels=["Normal", "Anomaly"],
                    xlabel="Predicted", ylabel="Actual",
                    title=f"Confusion Matrix (threshold={threshold:.3f})")

        # 5. Summary Table
        ax5 = fig.add_subplot(gs[1, 1:])
        ax5.axis("off")
        best_f1, best_thresh = self.best_f1()
        eval_thresh = threshold or best_thresh
        cm_report = self.confusion_matrix_report(eval_thresh)

        table_data = [
            ["Metric", "Value"],
            ["Image AUROC",  f"{auroc:.4f}"],
            ["Image AUPR",   f"{aupr:.4f}"],
            ["Best F1",      f"{best_f1:.4f} (thresh={best_thresh:.4f})"],
            ["Precision",    f"{cm_report['Precision']}"],
            ["Recall (TPR)", f"{cm_report['Recall (TPR)']}"],
            ["Specificity",  f"{cm_report['Specificity']}"],
        ]
        if self.pixel_scores is not None:
            table_data.append(["Pixel AUROC", f"{self.pixel_auroc():.4f}"])
            table_data.append(["PRO-score",   f"{self.pro_score():.4f}"])

        table = ax5.table(cellText=table_data[1:], colLabels=table_data[0],
                          loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.8)
        ax5.set_title("Evaluation Summary", fontsize=12, fontweight="bold")

        plt.suptitle("Anomaly Detection - Full Evaluation Report", fontsize=15, fontweight="bold")
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.show()
```

### 5.3 전체 평가 예시

```python
def run_full_evaluation(model: PatchCore, calibrator: ThresholdCalibrator,
                        test_dir: str, image_size: int = 256):
    """테스트 세트 전체에 대한 평가 실행 예시"""
    from torchvision.datasets import ImageFolder

    transform = AnomalyTransform.test_transform(image_size)

    def wrap_transform(img):
        import numpy as np
        return transform(image=np.array(img))["image"]

    dataset = ImageFolder(root=test_dir, transform=wrap_transform)
    # ImageFolder: 'good' → 정상(0), 그 외 → 이상(1)
    class_to_label = {v: (0 if k == "good" else 1) for k, v in dataset.class_to_idx.items()}

    all_scores, all_labels = [], []
    for img_tensor, class_idx in tqdm(dataset, desc="Evaluating"):
        score, _ = model.predict(img_tensor)
        all_scores.append(score)
        all_labels.append(class_to_label[class_idx])

    scores = np.array(all_scores)
    labels = np.array(all_labels)

    evaluator = AnomalyEvaluator(scores, labels)
    evaluator.plot_full_report(
        threshold=calibrator.threshold,
        save_path="evaluation_report.png"
    )

    # 최종 수치 출력
    auroc = evaluator.image_auroc()
    aupr  = evaluator.image_aupr()
    best_f1, _ = evaluator.best_f1()
    print(f"\n{'='*40}")
    print(f"  Image AUROC : {auroc:.4f}")
    print(f"  Image AUPR  : {aupr:.4f}")
    print(f"  Best F1     : {best_f1:.4f}")
    print(f"{'='*40}")
```

### 5.4 지속적 모니터링 (Production)

서비스 배포 후에도 데이터 분포 변화(Data Drift)를 감지하고 모델 재학습 시점을 자동으로 파악해야 합니다.

```python
class ProductionMonitor:
    """
    운영 중 점수 분포 변화를 감지하여 재학습 필요 여부 알림
    """
    def __init__(self, baseline_scores: np.ndarray, window_size: int = 500, drift_alpha: float = 0.01):
        self.baseline = baseline_scores
        self.window_size = window_size
        self.drift_alpha = drift_alpha
        self.recent_scores = []

    def add_score(self, score: float):
        self.recent_scores.append(score)
        if len(self.recent_scores) >= self.window_size:
            self._check_drift()
            self.recent_scores = []  # 슬라이딩 윈도우 초기화

    def _check_drift(self):
        from scipy.stats import ks_2samp
        recent = np.array(self.recent_scores)
        stat, p_value = ks_2samp(self.baseline, recent)

        if p_value < self.drift_alpha:
            print(f"⚠️  데이터 드리프트 감지! KS stat={stat:.4f}, p={p_value:.4f}")
            print("   → 모델 재학습 또는 임계값 재보정을 검토하세요.")
        else:
            print(f"✅ 분포 안정: KS stat={stat:.4f}, p={p_value:.4f}")
```

---

## 🗂️ 전체 파이프라인 요약

```
이미지 이상 감지 파이프라인 전체 흐름

[데이터 수집]
  정상 이미지 수집 (최소 200장 이상 권장)
       │
       ▼
[품질 검증]
  블러 검사 + Isolation Forest로 이상 오염 제거
       │
       ▼
[전처리 & 증강]
  Resize → 보수적 증강 → Normalize (학습용)
  Resize → Normalize only (추론용)
       │
       ▼
[모델 학습]
  PatchCore: Backbone 특징 → Coreset 메모리 뱅크 구축
       │
       ▼
[임계값 보정]
  검증 세트 정상 점수 분포 → Percentile / Gaussian 방법
       │
       ▼
[배포]
  FastAPI 서버 + FAISS GPU 인덱스 + ONNX Runtime
       │
       ▼
[평가]
  AUROC / AUPR / F1 / PRO-score
       │
       ▼
[운영 모니터링]
  KS-test로 점수 드리프트 감지 → 자동 재학습 트리거
```

---

## 📌 핵심 요약

| 단계 | 핵심 포인트 |
|------|------------|
| **데이터 준비** | 정상 데이터 품질이 전부. 최소 200장, 다양한 조명·각도 포함 |
| **모델 선택** | 소규모 데이터: PatchCore / 경량화 필요: EfficientAD / 최고 정확도: DINOv2+SimpleNet |
| **추론 서빙** | 임계값은 검증 정상 분포의 99 percentile 기준 설정 권장 |
| **성능 확보** | DINOv2 Backbone + Multi-scale 특징 + Domain Adaptation |
| **성능 평가** | AUROC 단독이 아닌 AUPR + PRO-score 병행 측정 필수 |
| **운영** | KS-test 기반 드리프트 모니터링으로 장기 품질 유지 |

이상 감지 시스템은 **"어떤 모델을 선택하느냐"보다 "얼마나 깨끗한 정상 데이터를 준비하느냐"**가 성능을 결정하는 핵심 요소입니다. 충분한 데이터 품질 검증과 일관된 전처리 파이프라인을 먼저 구축한 후, PatchCore와 같은 검증된 알고리즘을 적용하면 실무 환경에서도 AUROC 95% 이상의 안정적인 성능을 달성할 수 있습니다.
