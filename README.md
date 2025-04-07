# GPT 학습 피드백 시스템 (우리 학원 전용 AI 튜터)

영어 학습 문제를 풀고 AI로부터 즉각적인 피드백을 받을 수 있는 웹 애플리케이션입니다. 학생들이 로그인하여 문제를 풀면 GPT가 실시간으로 채점하고 피드백을 제공하며, 결과는 자동으로 Google Sheets에 저장됩니다.

## 주요 기능

- **학생 로그인**: 학생 이름을 입력하여 세션 시작
- **문제 제공**: Google Sheets에서 무작위로 문제 불러오기
- **답안 제출**: 객관식 문제의 정답 선택 및 제출
- **AI 채점 및 피드백**: GPT를 통한 채점 및 개인화된 피드백 생성
- **결과 저장**: 모든 답변 및 점수를 Google Sheets에 자동 저장

## 설치 방법

### 요구 사항

- Python 3.7 이상
- Google Cloud 서비스 계정 (Google Sheets API 사용)
- OpenAI API 키

### 설치 단계

1. 저장소 클론
```bash
git clone https://github.com/your-username/gpt-academy-bot.git
cd gpt-academy-bot
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 필요한 라이브러리 설치
```bash
pip install -r requirements.txt
```

## 환경 설정

1. OpenAI API 키 발급
   - [OpenAI 웹사이트](https://platform.openai.com/)에서 API 키 발급

2. Google Cloud 서비스 계정 생성
   - [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
   - Google Sheets API 활성화
   - 서비스 계정 생성 및 JSON 키 파일 다운로드
   - JSON 키 파일을 프로젝트 루트에 `service_account.json`으로 저장

3. `.streamlit/secrets.toml` 파일 설정
   ```toml
   # OpenAI API 설정
   OPENAI_API_KEY = "your-openai-api-key"
   
   # Google Sheets 설정
   GSHEETS_ID = "your-google-sheets-id"
   ```

4. Google Sheets 초기 설정
   ```bash
   python setup_sheets.py
   ```
   - 서비스 계정 JSON 파일 경로와 스프레드시트 ID를 입력하여 문제 및 답변 시트 자동 생성

## 사용 방법

1. Streamlit 앱 실행
```bash
streamlit run main.py
```

2. 웹 브라우저에서 앱 접속 (기본: http://localhost:8501)

3. 학생 이름 입력하여 로그인

4. 문제를 읽고 답안 선택 후 제출

5. AI 채점 결과 및 피드백 확인

## 프로젝트 구조

- `main.py`: Streamlit 앱의 메인 파일
- `gpt_feedback.py`: OpenAI API 연동 및 피드백 생성 기능
- `sheets_utils.py`: Google Sheets 연동 및 데이터 관리 기능
- `setup_sheets.py`: Google Sheets 초기 설정 스크립트
- `test_app.py`: 애플리케이션 테스트 스크립트
- `requirements.txt`: 필요한 Python 라이브러리 목록
- `.streamlit/secrets.toml.example`: 설정 파일 예시

## Google Sheets 설정

### 문제 시트 구조 (problems)
| 문제ID | 문제내용 | 보기1 | 보기2 | 보기3 | 보기4 | 보기5 | 정답 | 해설 |
|--------|----------|-------|-------|-------|-------|-------|------|------|

### 학생 답변 시트 구조 (student_answers)
| 학생ID | 이름 | 문제ID | 제출답안 | 점수 | 피드백 | 제출시간 |
|--------|------|--------|----------|------|--------|----------| 