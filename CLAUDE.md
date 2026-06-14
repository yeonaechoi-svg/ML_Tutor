# CLAUDE.md — ML Tutor 프로젝트 개발 가이드

## 1. 프로젝트 목적 및 주요 기능 요약

### 목적
고등학교 정보 교과 인공지능 단원에서 학생들이 기계학습 모델 구현 프로젝트를
수행하는 전 과정을 지원하는 AI 튜터 및 멘토형 웹 서비스.

- 대상: 인공지능을 처음 접하는 고등학생
- 환경: 학교 내부 와이파이 / 학생 개인 노트북 / 교사 노트북이 서버 역할
- 운영: 수업 시간에만 교사 노트북에서 Flask 서버 실행

### 핵심 원칙 (AI 튜터 설계 철학)
- 정답 코드를 절대 직접 제공하지 않는다
- 단계별 체크포인트에서 개념 확인 + 코드 의미 확인 질문을 제공한다
- 학생이 스스로 생각하도록 힌트와 유도 질문(스캐폴딩)으로 이끈다
- AI 튜터 톤: 차분하고 격식있게 (교사처럼)

### 주요 기능
1. 학생 로그인 (반 + 학번 + 이름 + 비밀번호)
2. 7단계 학습 콘텐츠 (단계별 진도 저장)
3. AI 튜터 체크포인트 (Anthropic Claude API 연동)
4. 학습 기록 저장 (수업 끊겨도 이어서 진행 가능)
5. 교사 관리 페이지 (진행 상황 확인, 비밀번호 초기화)
6. 7단계 자기평가 및 동료 평가 (체크리스트형)

### 7단계 학습 흐름

```
1단계  기계학습 개념과 유형 — 사전학습
       세부 구성 (현재 페이지 틀 유지):
       [스텝1] 인공지능이란?
       [스텝2] 기계학습이란?
       [스텝3] 기계학습 유형 (지도학습 vs 비지도학습)
       [스텝4] 지도학습 — 회귀
               + 선형 회귀 알고리즘 설명
       [스텝5] 지도학습 — 분류
               + 의사결정 트리 알고리즘
               + 랜덤 포레스트 알고리즘
               + K-최근접 이웃(KNN) 알고리즘
       [스텝6] 비지도학습 — 군집
               + K-평균 알고리즘
       [퀴즈]  유형 판별 이해 확인 퀴즈
       → AI 체크포인트: 각 스텝 완료 시

2단계  아이디어 구상 및 문제 정의  [핵심 단계]
       - 해결하고 싶은 사회 문제 주제 선정
       - AI 튜터와 대화로 기계학습 유형 판별 유도
       - 문제 정의서 작성

3단계  데이터 탐색과 전처리
       - 공공데이터 포털 안내 및 수집 가이드
       - 데이터 로드 코드 템플릿 제공 (변수명 직접 대입)
       - 결측치/이상치 처리 가이드
       → AI 체크포인트: 전처리 과정 이해 확인

4단계  기계학습 유형과 알고리즘 선정
       - 2단계에서 정한 주제 기반으로 알고리즘 선정
       - 학생이 스스로 선택 → AI 튜터가 피드백
       - 선정 이유 작성

5단계  기계학습을 통한 모델 생성
       - 훈련/테스트 데이터 분리 코드 템플릿
       - 선택한 알고리즘별 일반화 코드 템플릿
       - 학생이 변수명 직접 대입하여 구현
       → AI 체크포인트: 코드 의미 확인

6단계  성능평가, 모델 정확도 확인 및 테스트 데이터를 이용한 예측
       - 성능 지표 해석 가이드
       - 낮은 정확도 시 AI 인지적 피드백
       - 테스트 데이터 예측 결과 도출
       - 시각화 구현 가이드
       → AI 체크포인트: 결과 해석 확인

7단계  자기평가 및 동료 평가
       - AI가 생성하는 자기평가 체크리스트
       - 같은 반 학생 결과물 동료 평가 (체크리스트형)
```

---

## 2. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 백엔드 | Python 3.11 + Flask | 교사 노트북에서 실행 |
| 데이터베이스 | SQLite + SQLAlchemy | 별도 설치 불필요 |
| 프론트엔드 | HTML/CSS/JavaScript | Jinja2 템플릿 |
| AI 튜터 | Anthropic Claude API | claude-sonnet-4-6 모델 사용 |
| 인증 | Flask-Login + Werkzeug | 비밀번호 해시 암호화 |
| 엑셀 처리 | openpyxl | 학생 명단 업로드 |
| 환경 변수 | python-dotenv | API 키 보안 관리 |

---

## 3. 폴더 구조

```
ml_tutor/
├── CLAUDE.md                  # 이 파일
├── .env                       # API 키 (절대 git에 올리지 않음)
├── .gitignore
├── requirements.txt
├── run.py                     # 서버 실행 진입점
│
├── app/
│   ├── __init__.py            # Flask 앱 팩토리
│   ├── models.py              # DB 모델
│   ├── auth/                  # 로그인/로그아웃
│   ├── student/               # 학생 학습 페이지
│   ├── teacher/               # 교사 관리 페이지
│   ├── ai_tutor/              # AI 튜터 API 연동
│   │   ├── routes.py
│   │   └── prompts.py         # 단계별 체크포인트 프롬프트
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   └── student/
│   │       ├── dashboard.html
│   │       ├── stage1/        # 1단계: 사전학습
│   │       │   ├── step1.html (인공지능이란?)
│   │       │   ├── step2.html (기계학습이란?)
│   │       │   ├── step3.html (기계학습 유형)
│   │       │   ├── step4.html (지도학습-회귀+선형회귀)
│   │       │   ├── step5.html (지도학습-분류+의사결정트리/랜덤포레스트/KNN)
│   │       │   ├── step6.html (비지도학습-군집+K-평균)
│   │       │   └── quiz.html  (이해 확인 퀴즈)
│   │       ├── stage2/        # 2단계: 아이디어 구상 및 문제 정의
│   │       ├── stage3/        # 3단계: 데이터 탐색과 전처리
│   │       ├── stage4/        # 4단계: 유형과 알고리즘 선정
│   │       ├── stage5/        # 5단계: 모델 생성
│   │       ├── stage6/        # 6단계: 성능평가 및 예측
│   │       └── stage7/        # 7단계: 자기평가 및 동료 평가
│   │
│   └── static/
│       ├── css/main.css
│       └── js/main.js
│
├── instance/
│   └── ml_tutor.db
└── uploads/
```

---

## 4. 데이터베이스 모델 요약

```
User                           # 학생 + 교사 계정
- id, name, student_id         # 학번
- class_name                   # 반
- password_hash
- role (student / teacher)
- is_first_login               # 첫 로그인 여부

Progress                       # 학습 진도
- user_id, stage (1~7), substep
- status (in_progress / completed)
- updated_at

ChatLog                        # AI 튜터 대화 기록
- user_id, stage, substep
- question, answer, feedback
- created_at

QuizResult                     # 퀴즈 결과
- user_id, stage, score, total

PeerReview                     # 동료 평가
- reviewer_id, reviewee_id
- checklist_json
```

---

## 5. 개발 시 지켜야 할 규칙과 주의사항

### API 키 보안
- Anthropic API 키는 반드시 `.env` 파일에만 저장
- `.env` 파일은 절대 git에 커밋하지 않는다
- 코드 어디에도 API 키를 하드코딩하지 않는다

### AI 튜터 프롬프트 원칙
- 정답 코드를 직접 제공하지 않는다
- 힌트와 유도 질문으로 학생이 스스로 생각하게 한다
- 차분하고 격식있는 어조를 유지한다
- 고등학생 수준에 맞는 언어를 사용한다
- 모델: claude-sonnet-4-6 / max_tokens: 1000

### 1단계 페이지 개발 원칙
- 기존 step1.html ~ step6.html의 페이지 틀(base.html, CSS 클래스 구조)을 유지한다
- 각 스텝에 알고리즘 설명 섹션만 추가한다
- step4.html: 회귀 개념 + 선형 회귀 알고리즘 설명 추가
- step5.html: 분류 개념 + 의사결정트리 / 랜덤포레스트 / KNN 알고리즘 설명 추가
- step6.html: 군집 개념 + K-평균 알고리즘 설명 추가

### Flask 개발 규칙
- 모든 학생 페이지는 @login_required 데코레이터 적용
- 교사 페이지는 role == 'teacher' 검증 필수
- 비밀번호는 werkzeug.security로 해시 처리
- DB 작업은 try/except로 오류 처리

### 실행 방법
```bash
pip install -r requirements.txt
python run.py
# 학생 접속: http://[선생님IP]:5000
# IP 확인: ipconfig
```
