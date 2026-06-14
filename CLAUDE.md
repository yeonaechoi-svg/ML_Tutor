# CLAUDE.md — ML Tutor 프로젝트 개발 가이드

## 1. 프로젝트 목적 및 주요 기능 요약

### 목적
고등학교 정보 교과 인공지능 단원에서 학생들이 기계학습 모델 구현 프로젝트를
수행하기 전, 사전 학습을 지원하는 AI 튜터 및 멘토형 웹 서비스.

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
6. 7단계 동료 평가 (체크리스트형)

### 7단계 학습 흐름
```
1단계  개념 이해 및 유형 판별
       - 인공지능 / 기계학습 개념
       - 지도학습(회귀, 분류) / 비지도학습(군집) 유형
       - 알고리즘별 사례 학습
       - 교과서 실습 3개 (선형회귀 / 분류 / K-평균 군집)
       - AI 체크포인트 + 이해 확인 퀴즈

2단계  아이디어 구상 및 요구분석 [핵심 단계]
       - 분석 주제 선정
       - 기계학습 유형 판별 (AI 튜터 유도)
       - 적합한 알고리즘 추천

3단계  문제 정의 및 데이터 수집/전처리
       - 공공데이터 수집 가이드
       - 코드 템플릿 제공 (변수명 직접 대입 방식)

4단계  기계학습 모델링 (핵심 비계 설정)
       - 훈련/테스트 데이터 분리
       - 일반화 코드 템플릿 제공

5단계  모델 학습 및 정확도 확인
       - 성능 지표 산출
       - 인지적 피드백 (스케일링 권장 등)

6단계  테스트 데이터를 이용한 예측
       - 예측 결과 도출
       - 시각화 구현 가이드

7단계  성능평가 및 최종 공유
       - 자기평가 체크리스트
       - 동료 평가 (체크리스트형)
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
│   ├── models.py              # DB 모델 (User, Progress, ChatLog 등)
│   ├── auth/                  # 로그인/로그아웃
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── student/               # 학생 학습 페이지
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── teacher/               # 교사 관리 페이지
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── ai_tutor/              # AI 튜터 API 연동
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── prompts.py         # 단계별 체크포인트 프롬프트
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── change_password.html
│   │   ├── student/
│   │   │   ├── dashboard.html
│   │   │   ├── stage1/        # 1단계 사전학습
│   │   │   ├── stage2/        # 2단계 아이디어 구상
│   │   │   ├── stage3/
│   │   │   ├── stage4/
│   │   │   ├── stage5/
│   │   │   ├── stage6/
│   │   │   └── stage7/        # 동료 평가
│   │   └── teacher/
│   │       ├── dashboard.html
│   │       ├── students.html
│   │       └── upload.html
│   │
│   └── static/
│       ├── css/
│       │   └── main.css
│       └── js/
│           └── main.js
│
├── instance/
│   └── ml_tutor.db            # SQLite DB 파일 (자동 생성)
│
└── uploads/                   # 학생 명단 엑셀 업로드 임시 저장
```

---

## 4. 데이터베이스 모델 요약

```
User                           # 학생 + 교사 계정
- id, name, student_id         # 학번
- class_name                   # 반
- password_hash
- role (student / teacher)
- is_first_login               # 첫 로그인 여부 (비밀번호 변경 유도)

Progress                       # 학생 학습 진도
- user_id
- stage (1~7)
- step (단계 내 세부 스텝)
- status (in_progress / completed)
- updated_at

ChatLog                        # AI 튜터 대화 기록
- user_id
- stage, step
- question                     # AI가 던진 질문
- answer                       # 학생 답변
- feedback                     # AI 피드백
- created_at

QuizResult                     # 퀴즈 결과
- user_id
- stage
- score
- total
- created_at

PeerReview                     # 동료 평가
- reviewer_id                  # 평가자
- reviewee_id                  # 피평가자
- checklist (JSON)
- created_at
```

---

## 5. 개발 시 지켜야 할 규칙과 주의사항

### API 키 보안
- Anthropic API 키는 반드시 `.env` 파일에만 저장
- `.env` 파일은 절대 git에 커밋하지 않는다
- 코드 어디에도 API 키를 하드코딩하지 않는다

```python
# .env 파일 예시
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=랜덤문자열
TEACHER_CODE=선생님전용코드
```

### AI 튜터 프롬프트 원칙
- 시스템 프롬프트에 반드시 포함할 것:
  "정답 코드를 직접 제공하지 마세요"
  "힌트와 유도 질문으로 학생이 스스로 생각하게 하세요"
  "차분하고 격식있는 어조를 유지하세요"
  "고등학생 수준에 맞는 언어를 사용하세요"
- 모델: claude-sonnet-4-6
- max_tokens: 1000

### Flask 개발 규칙
- 모든 학생 페이지는 @login_required 데코레이터 적용
- 교사 페이지는 role == 'teacher' 검증 필수
- 비밀번호는 반드시 werkzeug.security로 해시 처리
- DB 작업은 try/except로 오류 처리

### 프론트엔드 규칙
- 모바일 대응 불필요 (노트북 사용 환경)
- 최소한의 CSS로 가독성 확보
- JavaScript는 필요한 부분만 최소화
- 한국어 UI 통일

### 파일 명명 규칙
- Python 파일: snake_case
- HTML 템플릿: snake_case
- CSS 클래스: kebab-case

### 실행 방법 (선생님용)
```bash
# 1. 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 2. 서버 실행
python run.py

# 3. 학교 내부에서 접속
# 브라우저에서 → http://[선생님IP]:5000
# 선생님IP 확인: 터미널에서 ipconfig 입력
```

### 주의사항
- 수업 끝나고 서버 종료 시 DB는 자동 저장됨
- DB 파일(ml_tutor.db) 정기적으로 백업 권장
- 학생 30명 이상 동시 접속 시 Flask 개발 서버 한계 있음
  → 추후 gunicorn으로 전환 고려
