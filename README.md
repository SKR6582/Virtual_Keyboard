# CV-Type Virtual Keyboard

멀티뷰 카메라(1대~최대 4대 가변 지원)와 MediaPipe, OpenCV, scikit-learn 회귀/분류 모델(`.pkl`), Electron Always-on-Top 오버레이를 결합한 가상 평면 키보드 시스템입니다.

LG Gram(8GB RAM) 및 Galaxy Book(16GB RAM)과 같은 내장 그래픽 환경에서도 CPU 연산만으로 실시간 30 FPS 처리가 가능하도록 설계되었습니다.

---

## 1. 주요 기능

- **가변 멀티 카메라 지원**: 1대부터 최대 4대까지 연결된 카메라를 자동 감지(1080p MJPEG 비동기 스레드 버퍼링). 물리 카메라가 없을 경우 시뮬레이션 카메라로 자동 전환.
- **ArUco 기반 투시 변환 (Warp Perspective)**: 4개 모서리 마커(ID 0, 1, 2, 3)를 통해 카메라 각도 왜곡을 자동으로 보정하여 자판 정규화 2D 평면 좌표계 수립.
- **물리 지표(FSM) 및 머신러닝 복합 타건 판정**: Z축 하강 속도($dz/dt$)와 PIP-DIP 관절 각도 기반 유한 상태 머신(FSM) 및 16차원 멀티뷰 특징 벡터 scikit-learn 회귀/분류 모델(`.pkl`) 앙상블.
- **실제 OS 키보드 주입**: `pynput`을 통한 시스템 전역 가상 키 입력 및 250ms 채터링 방지 디바운싱.
- **청각 및 시각 피드백**: 0.06s 기계식 키보드 사운드(`.wav`) 및 투명 오버레이 HUD 실시간 점등.
- **Electron UI 대시보드 및 Always-on-Top 투명 오버레이**:
  - 카메라 영상 및 손 관절 실시간 프리뷰
  - 키보드 평면 캔버스 실시간 커서 및 히트 시각화
  - 키별 데이터 수집 및 원클릭 `.pkl` 모델 학습 파이프라인
  - 단축키(`Ctrl+Shift+O` / `Cmd+Shift+O`)를 통한 투명 HUD 토글

---

## 2. 디렉토리 구조

```
Virtual_Keyboard/
├── backend/
│   ├── app.py                      # WebSocket 서버 및 오케스트레이터
│   ├── config.py                   # 전역 설정
│   ├── camera/manager.py           # 1~4대 카메라 비동기 캡처 및 시뮬레이션
│   ├── vision/
│   │   ├── perspective.py          # ArUco 마커 검출 및 투시 왜곡 보정
│   │   ├── hand_tracker.py         # MediaPipe 손 관절 추출 및 이동평균 스무딩
│   │   └── feature_extractor.py    # 16차원 다중 시점 정규화 특징 벡터 추출
│   ├── engine/
│   │   ├── fsm.py                  # Z속도 & 관절각 기반 FSM 타건 상태기
│   │   ├── key_mapper.py           # keymap.json Bounding Box 충돌 판정
│   │   └── sound_player.py         # 기계식 키보드 클릭 사운드 재생기
│   ├── ml/
│   │   ├── model.py                # scikit-learn (.pkl) 모델 추론기
│   │   ├── dataset.py              # 학습 데이터셋 관리자
│   │   └── trainer.py              # 원클릭 모델 학습기
│   ├── input/key_injector.py       # pynput 기반 OS 키보드 주입
│   └── requirements.txt
│
├── frontend/
│   ├── package.json
│   ├── main.js                     # Electron 메인 프로세스 (대시보드 + 오버레이)
│   ├── preload.js
│   └── src/
│       ├── index.html              # 메인 대시보드
│       ├── overlay.html            # 투명 오버레이 HUD
│       ├── css/
│       │   ├── style.css
│       │   └── overlay.css
│       └── js/
│           ├── app.js
│           └── overlay.js
│
├── config/
│   ├── keymap.json                 # 키보드 레이아웃 및 바운딩 박스
│   └── virtual_keyboard_model.pkl  # 학습된 머신러닝 모델
├── assets/sounds/click.wav         # 타건 사운드 에셋
└── tests/                          # 단위 및 통합 테스트 스위트
```

---

## 3. 설치 및 실행 방법

### 1) Python 백엔드 의존성 설치
```bash
pip install -r backend/requirements.txt
```

### 2) Electron 프론트엔드 의존성 설치
```bash
cd frontend
npm install
cd ..
```

### 3) 애플리케이션 실행
Electron 앱을 실행하면 Python 백엔드가 백그라운드에서 자동 실행됩니다:
```bash
cd frontend
npm start
```

백엔드만 단독 실행하여 디버깅하려는 경우:
```bash
python3 -m backend.app
```

### 4) 테스트 스위트 실행
```bash
python3 -m unittest discover -s tests
```

---

## 4. ArUco 바닥판 구성 안내

자판 이미지의 4개 모서리에 `DICT_4X4_50` 마커를 배치합니다:
- **ID 0**: 좌상단 (Top-Left)
- **ID 1**: 우상단 (Top-Right)
- **ID 2**: 우하단 (Bottom-Right)
- **ID 3**: 좌하단 (Bottom-Left)

카메라가 켜지면 ArUco 마커를 자동 감지하여 투시 보정을 수행합니다. 카메라가 없거나 마커가 감지되지 않는 경우 기본 뷰로 동작합니다.

