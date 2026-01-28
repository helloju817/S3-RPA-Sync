# 🌐 AI Layout – S3 ↔ RPA Sync

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python) ![AWS](https://img.shields.io/badge/AWS-S3-orange?logo=amazon-aws) ![RPA](https://img.shields.io/badge/RPA-Automation-blueviolet) ![License](https://img.shields.io/badge/License-MIT-green.svg)

AWS S3 버킷과 RPA 서버 간 자동 파일 동기화 스크립트

---

## 📦 설치

```bash
git clone https://github.com/juyoung.yun/S3-RPA-Sync.git
cd S3-RPA-Sync
pip install -r requirements.txt
```

---

## ⚙️ 환경 설정

실행 전 아래 환경 변수를 설정해야 합니다:

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-northeast-2

S3_BUCKET=ai-layout-data
RPA_INPUT_DIR=.../Input
RPA_COMPLETED_DIR=.../Completed
```

---

## ▶ 실행

```bash
python rpa_test.py
```

---

## 📂 프로젝트 구조

```
al_layout/
├── rpa_test.py        # 메인 동기화 스크립트
├── state.json         # 상태 관리 파일 (자동 생성)
├── requirements.txt   # 의존성
├── README.md
└── LICENSE
```
