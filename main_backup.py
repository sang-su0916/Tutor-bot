import streamlit as st
import time
import uuid
import random  # random 모듈 추가
import traceback

# 페이지 설정 - 가장 먼저 호출되어야 함
st.set_page_config(
    page_title="GPT 학습 피드백 (우리 학원 전용 튜터)",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

import os
import sys

# 현재 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 모듈 임포트
try:
    from sheets_utils import connect_to_sheets, get_random_problem, save_student_answer, get_worksheet_records
    from gpt_feedback import generate_feedback
    import admin  # 관리자 모듈 추가
    import student_analytics  # 학생 분석 모듈
    try:
        from student_analytics import (
            get_problem_for_student,
            update_problem_stats,
            show_student_performance_dashboard
        )
    except ImportError:
        # 모듈 없을 경우 더미 함수 정의
        def get_problem_for_student(student_id, available_problems):
            import random
            return random.choice(available_problems) if available_problems else None
        
        def update_problem_stats(student_id, problem_id, keywords, is_correct):
            pass
        
        def show_student_performance_dashboard(student_id, student_name, grade, level):
            pass
except Exception as e:
    # 이미 streamlit이 임포트되어 있으므로 중복 임포트 제거
    st.error(f"모듈 임포트 오류: {str(e)}")

# OpenAI API 초기화
try:
    import google.generativeai as genai
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        print("Gemini API 키가 성공적으로 설정되었습니다.")
    else:
        st.warning("Gemini API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일에 GOOGLE_API_KEY를 설정해주세요.")
except ImportError:
    st.error("Google Generative AI 모듈을 불러올 수 없습니다. 'pip install google-generativeai' 명령어로 설치해주세요.")
except Exception as e:
    st.error(f"Gemini API 초기화 오류: {str(e)}")

# URL 파라미터 확인 - 재시작 명령 처리
def check_reset_command():
    """URL 파라미터에서 리셋 명령을 확인합니다."""
    try:
        query_params = st.query_params
        if "reset" in query_params and query_params["reset"] == "true":
            # 세션 상태 초기화
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # 쿼리 파라미터 제거
            st.query_params.clear()
            return True
    except:
        # 쿼리 파라미터 처리 중 오류 발생시 무시
        pass
    return False

def check_api_connections():
    """API 연결 상태를 확인합니다."""
    status = {
        "google_sheets": False,
        "gemini": False,
        "error_messages": []
    }
    
    # Google Sheets API 연결 확인
    try:
        # .streamlit/secrets.toml 파일이 존재하는지 확인
        if not hasattr(st, 'secrets') or not st.secrets:
            status["error_messages"].append("secrets.toml 파일이 없거나 읽을 수 없습니다. .streamlit/secrets.toml 파일을 생성해주세요.")
            return status
            
        if "gcp_service_account" not in st.secrets or "spreadsheet_id" not in st.secrets:
            status["error_messages"].append("Google Sheets 설정 누락: gcp_service_account 또는 spreadsheet_id가 없습니다.")
        else:
            # 서비스 계정 정보 확인
            service_account_info = st.secrets["gcp_service_account"]
            required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
            missing_fields = [field for field in required_fields if field not in service_account_info]
            
            if missing_fields:
                missing_fields_str = ", ".join(missing_fields)
                status["error_messages"].append(f"서비스 계정 정보 누락: {missing_fields_str}")
            else:
                # 연결 시도
                sheet = connect_to_sheets()
                if sheet:
                    # 테스트 워크시트 접근 시도
                    try:
                        worksheets = sheet.worksheets()
                        if worksheets:
                            status["google_sheets"] = True
                            print(f"구글 스프레드시트에 성공적으로 연결되었습니다. 워크시트: {[ws.title for ws in worksheets]}")
                    except Exception as e:
                        status["error_messages"].append(f"Google Sheets 워크시트 접근 오류: {str(e)}")
                else:
                    status["error_messages"].append("Google Sheets 연결 실패")
    except Exception as e:
        status["error_messages"].append(f"Google Sheets 연결 오류: {str(e)}")
    
    # Gemini API 연결 확인
    try:
        if not hasattr(st, 'secrets') or not st.secrets:
            status["error_messages"].append("secrets.toml 파일이 없거나 읽을 수 없습니다.")
            return status
            
        if "GOOGLE_API_KEY" in st.secrets:
            try:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                # 간단한 프롬프트로 테스트
                response = model.generate_content("Hello")
                if response:
                    status["gemini"] = True
            except Exception as e:
                status["error_messages"].append(f"Gemini API 호출 오류: {str(e)}")
        else:
            status["error_messages"].append("Gemini API 키가 설정되지 않음")
    except Exception as e:
        status["error_messages"].append(f"Gemini API 초기화 오류: {str(e)}")
    
    return status

def initialize_session_state():
    """세션 상태를 초기화합니다."""
    if check_reset_command() or "initialized" not in st.session_state:
        st.session_state.student_id = None
        st.session_state.student_name = None
        st.session_state.student_grade = None
        st.session_state.student_level = None
        st.session_state.current_problem = None
        st.session_state.submitted = False
        st.session_state.feedback = None
        st.session_state.score = None
        st.session_state.show_result = False
        st.session_state.is_multiple_choice = False
        st.session_state.previous_problems = set()
        st.session_state.current_round = 1
        st.session_state.initialized = True
        st.session_state.page = "intro"
        st.session_state.student_answer = None
        # 초기화 완료 표시
        st.session_state.setup_complete = True

def intro_page():
    """시작 페이지"""
    # 화면 초기화 방지를 위한 세션 상태 확인
    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = True
        
    st.title("GPT 학습 피드백 시스템")
    st.markdown("#### 우리 학원 전용 AI 튜터")
    
    # secrets.toml 파일 존재 여부 확인
    if not hasattr(st, 'secrets') or not st.secrets:
        st.error("⚠️ 구성 파일이 없습니다: .streamlit/secrets.toml 파일을 생성해주세요.")
        st.markdown("""
        ### .streamlit/secrets.toml 파일 설정 방법
        
        1. 프로젝트 루트 디렉토리에 `.streamlit` 폴더를 생성하세요.
        2. 그 안에 `secrets.toml` 파일을 생성하세요.
        3. 다음 내용을 추가하세요:
        
        ```toml
        [gcp_service_account]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "key-id"
        private_key = "-----BEGIN PRIVATE KEY-----\\nPrivateKeyContents\\n-----END PRIVATE KEY-----\\n"
        client_email = "service-account-email@project-id.iam.gserviceaccount.com"
        client_id = "client-id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/service-account-email%40project-id.iam.gserviceaccount.com"
        
        # 스프레드시트 ID 설정
        spreadsheet_id = "your-spreadsheet-id-here"
        
        # Gemini API 키 설정
        GOOGLE_API_KEY = "your-gemini-api-key-here"
        ```
        
        4. 자세한 설정 방법은 아래 API 연결 상태 섹션의 가이드를 참고하세요.
        """)
    
    # API 연결 상태 확인 및 자세한 정보 표시
    with st.expander("API 연결 상태", expanded=True):
        try:
            api_status = check_api_connections()
            
            col1, col2 = st.columns(2)
            with col1:
                if api_status["google_sheets"]:
                    st.success("Google Sheets: 연결됨 ✅")
                else:
                    st.error("Google Sheets: 연결 안됨 ❌")
                    st.warning("⚠️ 구글 시트 연결이 필요합니다. 아래 가이드를 참고하세요.")
            
            with col2:
                if api_status["gemini"]:
                    st.success("Gemini API: 연결됨 ✅")
                else:
                    st.error("Gemini API: 연결 안됨 ❌")
                    st.warning("⚠️ Gemini API 키 설정이 필요합니다.")
            
            if api_status["error_messages"]:
                st.markdown("#### 오류 메시지")
                for msg in api_status["error_messages"]:
                    st.warning(msg)
                
                # 설정 가이드 제공
                st.markdown("### Google Sheets 연결 가이드")
                st.markdown("""
                #### 1. 구글 클라우드에서 서비스 계정 생성하기
                1. [Google Cloud Console](https://console.cloud.google.com/)에 로그인하세요.
                2. 프로젝트를 생성하거나 기존 프로젝트를 선택하세요.
                3. 좌측 메뉴에서 "IAM 및 관리자" > "서비스 계정"으로 이동하세요.
                4. "서비스 계정 만들기"를 클릭하세요.
                5. 서비스 계정 이름과 설명을 입력하고 "만들기"를 클릭하세요.
                6. 권한 설정 단계에서 "편집자" 역할을 선택하고 "계속"을 클릭하세요.
                7. 완료를 클릭하세요.
                
                #### 2. 서비스 계정 키 생성하기
                1. 방금 생성한 서비스 계정을 클릭하세요.
                2. "키" 탭으로 이동하세요.
                3. "키 추가" > "새 키 만들기"를 클릭하세요.
                4. JSON 키 유형을 선택하고 "만들기"를 클릭하세요.
                5. JSON 키 파일이 컴퓨터에 다운로드됩니다. 이 파일은 안전하게 보관하세요.
                
                #### 3. 구글 스프레드시트 생성 및 공유하기
                1. [Google Sheets](https://sheets.google.com/)에서 새 스프레드시트를 생성하세요.
                2. 스프레드시트의 URL에서 ID를 복사하세요. 
                   (예: `https://docs.google.com/spreadsheets/d/`**여기가 스프레드시트 ID**`/edit`)
                3. 스프레드시트의 "공유" 버튼을 클릭하세요.
                4. 서비스 계정 이메일 주소(예: `something@project-id.iam.gserviceaccount.com`)를 추가하고, 
                   "편집자" 권한을 부여하세요.
                
                #### 4. Streamlit Secrets 설정하기
                1. 프로젝트 루트 디렉토리에 `.streamlit` 폴더를 생성하세요.
                2. 그 안에 `secrets.toml` 파일을 생성하세요.
                3. 다음 내용을 추가하세요 (다운로드한 JSON 키 내용과 스프레드시트 ID를 사용):
                
                ```toml
                [gcp_service_account]
                type = "service_account"
                project_id = "your-project-id"
                private_key_id = "key-id"
                private_key = "-----BEGIN PRIVATE KEY-----\\nPrivateKeyContents\\n-----END PRIVATE KEY-----\\n"
                client_email = "service-account-email@project-id.iam.gserviceaccount.com"
                client_id = "client-id"
                auth_uri = "https://accounts.google.com/o/oauth2/auth"
                token_uri = "https://oauth2.googleapis.com/token"
                auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
                client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/service-account-email%40project-id.iam.gserviceaccount.com"
                
                # 스프레드시트 ID 설정
                spreadsheet_id = "your-spreadsheet-id-here"
                
                # Gemini API 키 설정
                GOOGLE_API_KEY = "your-gemini-api-key-here"
                ```
                
                > ⚠️ 주의: `private_key` 값은 `\\n`을 사용하여 실제 개행을 이스케이프 처리해야 합니다.
                
                설정이 완료되면 애플리케이션을 다시 시작하세요.
                """)
        except Exception as e:
            st.error(f"API 연결 상태 확인 중 오류 발생: {str(e)}")
            st.info("오류를 해결하려면 개발자에게 문의하세요.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👨‍🎓 학생 로그인", use_container_width=True):
            st.session_state.page = "student_login"
            st.rerun()
    
    with col2:
        if st.button("👨‍🏫 교사 관리자", use_container_width=True):
            st.session_state.page = "admin"
            st.rerun()
            
    st.markdown("---")
    st.markdown("##### 시스템 소개")
    st.markdown("""
    이 시스템은 학생들의 학습을 도와주는 AI 기반 피드백 시스템입니다.
    - 학생들은 개인화된 문제를 풀고 즉각적인 피드백을 받을 수 있습니다.
    - 교사들은 학생들의 진도와 성적을 관리할 수 있습니다.
    - 취약점 분석을 통해 학생별 맞춤형 문제가 제공됩니다.
    """)

def student_login_page():
    """학생 로그인 페이지"""
    # 화면 초기화 방지를 위한 세션 상태 확인
    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = True
        
    st.title("학생 로그인")
    
    # 등록된 학생 목록 가져오기
    try:
        sheet = connect_to_sheets()
        if sheet:
            try:
                worksheet = sheet.worksheet("students")
                students = worksheet.get_all_records()
                if students:
                    # 학생 선택 옵션
                    st.markdown("#### 등록된 학생 선택")
                    
                    # 학년별 필터링
                    grade_filter = st.selectbox(
                        "학년 선택", 
                        options=["전체"] + admin.GRADE_OPTIONS
                    )
                    
                    # 필터링된 학생 목록
                    if grade_filter == "전체":
                        filtered_students = students
                    else:
                        filtered_students = [s for s in students if s["학년"] == grade_filter]
                    
                    if filtered_students:
                        student_options = [f"{s['이름']} ({s['학년']}, {s['실력등급']})" for s in filtered_students]
                        selected_student = st.selectbox("학생 선택", options=student_options)
                        
                        if st.button("로그인", use_container_width=True):
                            if selected_student:
                                idx = student_options.index(selected_student)
                                student_data = filtered_students[idx]
                                
                                # 학생 정보 설정
                                st.session_state.student_id = student_data["학생ID"]
                                st.session_state.student_name = student_data["이름"]
                                st.session_state.student_grade = student_data["학년"]
                                st.session_state.student_level = student_data["실력등급"]
                                st.session_state.submitted = False
                                st.session_state.show_result = False
                                
                                # 문제 관련 상태 초기화
                                st.session_state.current_problem = None
                                st.session_state.feedback = None
                                st.session_state.score = None
                                st.session_state.previous_problems = set()
                                st.session_state.current_round = 1
                                st.session_state.page = "student_dashboard"
                                
                                # 세션 지속을 위한 플래그
                                st.session_state.login_complete = True
                                
                                st.rerun()
                    else:
                        st.info("선택한 학년에 등록된 학생이 없습니다.")
                else:
                    st.warning("등록된 학생이 없습니다. 교사 관리자에게 문의하세요.")
            except Exception as e:
                st.error("학생 정보를 불러오는데 실패했습니다.")
                st.markdown("### 직접 입력하기")
                manual_login()
        else:
            st.error("데이터베이스 연결에 실패했습니다.")
            st.markdown("### 직접 입력하기")
            manual_login()
    except Exception as e:
        st.error("데이터베이스 연결에 실패했습니다.")
        st.markdown("### 직접 입력하기")
        manual_login()
    
    # 뒤로 가기 버튼
    if st.button("← 뒤로 가기", key="back_btn"):
        st.session_state.page = "intro"
        st.rerun()

def manual_login():
    """직접 입력하여 로그인"""
    with st.form("manual_login_form"):
        student_name = st.text_input("이름을 입력하세요")
        
        # 학년 선택
        grade = st.selectbox("학년", options=admin.GRADE_OPTIONS)
        
        # 실력 등급 선택
        level = st.selectbox("실력 등급", options=admin.LEVEL_OPTIONS)
        
        submit_button = st.form_submit_button("로그인")
        
        if submit_button and student_name:
            # 학생 정보 설정
            st.session_state.student_id = str(uuid.uuid4())
            st.session_state.student_name = student_name
            st.session_state.student_grade = grade
            st.session_state.student_level = level
            st.session_state.submitted = False
            st.session_state.show_result = False
            
            # 문제 관련 상태 초기화
            st.session_state.current_problem = None
            st.session_state.feedback = None
            st.session_state.score = None
            st.session_state.previous_problems = set()
            st.session_state.current_round = 1
            st.session_state.page = "student_dashboard"
            
            st.rerun()

def student_dashboard():
    """학생 대시보드 페이지"""
    # 화면 초기화 방지를 위한 세션 상태 확인
    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = True
    
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
        
    st.title(f"환영합니다, {st.session_state.get('student_name', '학생')}님!")
    st.markdown(f"**학년**: {st.session_state.get('student_grade', 'N/A')} | **실력등급**: {st.session_state.get('student_level', 'N/A')}")
    
    # 두 개의 메인 옵션 제공
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 문제 풀기 (20문제 시험)", use_container_width=True):
            # 문제 풀기 세션 완전 초기화
            for key in list(st.session_state.keys()):
                if key.startswith("exam_") or key in ["student_answers", "used_problem_ids", "all_problems_loaded", 
                                                     "problem_count", "max_problems", "start_time", "time_limit"]:
                    if key in st.session_state:
                        del st.session_state[key]
            
            # 기본값 설정
            st.session_state.problem_count = 0
            st.session_state.max_problems = 20
            st.session_state.start_time = time.time()
            st.session_state.time_limit = 50 * 60  # 50분(초 단위)
            st.session_state.student_answers = {}
            st.session_state.used_problem_ids = set()  # 사용된 문제 ID 추적
            
            # 시험 관련 상태 초기화
            if 'exam_initialized' in st.session_state:
                del st.session_state.exam_initialized
            if 'exam_problems' in st.session_state:
                del st.session_state.exam_problems
            if 'exam_submitted' in st.session_state:
                del st.session_state.exam_submitted
            if 'exam_results' in st.session_state:
                del st.session_state.exam_results
            if 'feedback_data' in st.session_state:
                del st.session_state.feedback_data
                
            st.session_state.all_problems_loaded = False
            st.session_state.page = "exam_page"
            
            # 시험 시작 표시 - 세션 유지 플래그
            st.session_state.exam_start_flag = True
            
            st.rerun()
    
    with col2:
        if st.button("📊 나의 성적 분석", use_container_width=True):
            st.session_state.page = "my_performance"
            # 성적 분석 페이지 전환 플래그
            st.session_state.perf_page_active = True
            st.rerun()
    
    # 로그아웃 버튼
    if st.button("로그아웃", key="logout_dashboard_btn"):
        # 세션 상태 초기화
        for key in list(st.session_state.keys()):
            if key != "initialized" and key != "page":
                del st.session_state[key]
        st.session_state.page = "intro"
        st.session_state.setup_complete = True
        st.rerun()

def normalize_grade(grade_str):
    """
    학년 문자열을 표준 형식(중1, 중2, 중3, 고1, 고2, 고3)으로 정규화합니다.
    """
    if not grade_str:
        return ""
    
    # 문자열 정리
    normalized = grade_str.replace("학년", "").strip()
    
    # 학교급 처리
    if "중학교" in grade_str or "중" in grade_str:
        grade_prefix = "중"
    elif "고등학교" in grade_str or "고" in grade_str:
        grade_prefix = "고"
    else:
        # 학교급 정보가 없으면 중학교로 가정
        grade_prefix = "중"
    
    # 학년 숫자 추출
    grade_number = None
    for char in normalized:
        if char.isdigit():
            grade_number = char
            break
    
    # 학년 숫자가 1~3이 아니면 기본값 1로 설정
    if grade_number not in ["1", "2", "3"]:
        grade_number = "1"
    
    # 정규화된 형식 반환
    return f"{grade_prefix}{grade_number}"

def generate_dummy_problems(student_grade, count=20):
    """학생 학년에 맞는 더미 문제를 여러 개 생성합니다."""
    from sheets_utils import get_dummy_problem
    problems = []
    for i in range(count):
        dummy_problem = get_dummy_problem(student_grade)
        dummy_problem["문제ID"] = f"dummy-{uuid.uuid4()}"  # 고유 ID 생성
        problems.append(dummy_problem)
    return problems

def load_exam_problems(student_id, student_grade, problem_count=20):
    """학생 학년에 맞는 시험 문제를 불러옵니다"""
    if 'used_problem_ids' not in st.session_state:
        st.session_state.used_problem_ids = set()
    
    attempts = 0
    max_attempts = 50  # 무한 루프 방지
    
    # 학년 정규화
    normalized_student_grade = normalize_grade(student_grade)
    
    try:
        # 구글 시트에 연결
        connection = connect_to_sheets()
        if not connection:
            st.error("구글 시트에 연결할 수 없습니다.")
            return generate_dummy_problems(student_grade, problem_count)
        
        # 문제 가져오기
        all_problems = get_worksheet_records(connection, "problems")
        if not all_problems:
            st.warning("문제를 불러올 수 없습니다. 더미 문제를 사용합니다.")
            return generate_dummy_problems(student_grade, problem_count)
        
        # 학년에 맞는 문제 필터링
        filtered_problems = []
        problem_type_count = {}
        
        for p in all_problems:
            # 기본 유효성 검사
            is_valid = True
            
            # 필수 필드 확인
            required_fields = ["문제ID", "문제내용", "정답", "문제유형", "학년"]
            for field in required_fields:
                if field not in p or not p[field]:
                    is_valid = False
                    break
            
            # 학년 확인 (정규화된 학년으로 비교)
            problem_grade = normalize_grade(p.get("학년", ""))
            if problem_grade != normalized_student_grade:
                is_valid = False
            
            # 문제 유형별 추가 유효성 검사
            problem_type = p.get("문제유형", "")
            
            # 객관식 문제 유효성 검사
            if problem_type == "객관식" and is_valid:
                # 보기 정보 처리
                if "보기정보" not in p:
                    p["보기정보"] = {}
                
                # 보기 옵션(1번, 2번 등) 정보 추출 및 구조화
                for key in list(p.keys()):
                    if key.startswith("보기") and key != "보기정보":
                        option_key = key.replace("보기", "")
                        if option_key and p[key]:
                            p["보기정보"][option_key] = p[key].strip()
                
                # 보기가 최소 2개 이상 있어야 함
                if len(p.get("보기정보", {})) < 2:
                    is_valid = False
            
            # 주관식 문제 유효성 검사
            elif problem_type == "단답형" or problem_type == "서술형":
                # 정답이 반드시 있어야 함
                if not p.get("정답", "").strip():
                    is_valid = False
            
            # 이미 사용된 ID 제외
            if p["문제ID"] in st.session_state.used_problem_ids:
                is_valid = False
            
            if is_valid:
                # 문제 유형 카운트 증가
                problem_type_count[problem_type] = problem_type_count.get(problem_type, 0) + 1
                filtered_problems.append(p)
        
        # 유형별 통계 정보 출력
        st.info(f"학년 '{normalized_student_grade}'에 맞는 문제 {len(filtered_problems)}개를 찾았습니다.")
        if problem_type_count:
            type_info = ", ".join([f"{t}: {c}개" for t, c in problem_type_count.items()])
            st.info(f"문제 유형 분포: {type_info}")
        
        # 만약 충분한 문제가 없다면 더미 문제로 보충
        if len(filtered_problems) < problem_count:
            dummy_count = problem_count - len(filtered_problems)
            st.warning(f"유효한 문제가 부족하여 {dummy_count}개의 더미 문제를 추가합니다.")
            dummy_problems = generate_dummy_problems(student_grade, dummy_count)
            filtered_problems.extend(dummy_problems)
        
        # 문제 유형별로 분류
        problems_by_type = {}
        for p in filtered_problems:
            problem_type = p.get("문제유형", "기타")
            if problem_type not in problems_by_type:
                problems_by_type[problem_type] = []
            problems_by_type[problem_type].append(p)
        
        # 각 유형별로 균등하게 문제 선택 (유형별 비율 계산)
        selected_problems = []
        remaining_count = problem_count
        
        # 모든 유형에서 최소 1문제씩 선택
        for problem_type, type_problems in problems_by_type.items():
            if remaining_count <= 0:
                break
                
            # 각 유형에서 1문제 선택
            selected = random.choice(type_problems)
            selected_problems.append(selected)
            st.session_state.used_problem_ids.add(selected["문제ID"])
            
            # 선택된 문제는 제외
            type_problems.remove(selected)
            remaining_count -= 1
        
        # 남은 문제 수를 유형별 비율에 따라 배분
        if remaining_count > 0 and problems_by_type:
            # 각 유형별 남은 문제 수 계산
            total_remaining = sum(len(probs) for probs in problems_by_type.values())
            
            if total_remaining > 0:
                # 유형별 비율 계산 및 문제 선택
                for problem_type, type_problems in problems_by_type.items():
                    if not type_problems or remaining_count <= 0:
                        continue
                    
                    # 이 유형에서 선택할 문제 수 (최소 1개, 비율 기반 계산)
                    type_ratio = len(type_problems) / total_remaining
                    type_count = min(remaining_count, max(1, round(remaining_count * type_ratio)))
                    
                    # 실제 선택 가능한 문제 수로 제한
                    type_count = min(type_count, len(type_problems))
                    
                    # 해당 유형에서 무작위로 선택
                    for _ in range(type_count):
                        if type_problems and remaining_count > 0:
                            selected = random.choice(type_problems)
                            selected_problems.append(selected)
                            st.session_state.used_problem_ids.add(selected["문제ID"])
                            type_problems.remove(selected)
                            remaining_count -= 1
        
        # 여전히 부족하다면 남은 문제들 중에서 무작위로 선택
        remaining_problems = [p for p in filtered_problems if p["문제ID"] not in st.session_state.used_problem_ids]
        
        while remaining_count > 0 and remaining_problems and attempts < max_attempts:
            selected = random.choice(remaining_problems)
            selected_problems.append(selected)
            st.session_state.used_problem_ids.add(selected["문제ID"])
            remaining_problems.remove(selected)
            remaining_count -= 1
            attempts += 1
        
        # 여전히 부족하다면 더미 문제로 추가
        if remaining_count > 0:
            dummy_problems = generate_dummy_problems(student_grade, remaining_count)
            selected_problems.extend(dummy_problems)
            
            # 더미 문제 ID 추적
            for p in dummy_problems:
                if "문제ID" in p:
                    st.session_state.used_problem_ids.add(p["문제ID"])
        
        # 선택된 문제 목록을 무작위로 섞기
        random.shuffle(selected_problems)
        
        # 문제 유형 분포 확인 - 로그용
        final_type_count = {}
        for p in selected_problems:
            problem_type = p.get("문제유형", "기타")
            final_type_count[problem_type] = final_type_count.get(problem_type, 0) + 1
        
        type_distribution = ", ".join([f"{t}: {c}개" for t, c in final_type_count.items()])
        st.info(f"최종 선택된 문제 유형 분포: {type_distribution}")
        
        return selected_problems[:problem_count]
    
    except Exception as e:
        st.error(f"문제 로드 중 오류 발생: {str(e)}")
        # 오류 발생 시 더미 문제 반환
        return generate_dummy_problems(student_grade, problem_count)

def check_student_login():
    """학생 로그인 상태를 확인합니다."""
    return hasattr(st.session_state, 'student_id') and st.session_state.student_id is not None

def my_performance_page():
    """학생 성적 및 진척도 페이지"""
    # 새 페이지 전환을 위한 세션 상태 확인
    if "perf_page_active" not in st.session_state:
        st.session_state.perf_page_active = True
    
    if not check_student_login():
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    st.title("내 성적 분석")
    st.markdown(f"**학생**: {st.session_state.student_name} | **학년**: {st.session_state.student_grade} | **실력등급**: {st.session_state.student_level}")
    
    # 학생 진척도 대시보드 표시
    try:
        show_student_performance_dashboard(
            st.session_state.student_id,
            st.session_state.student_name,
            st.session_state.student_grade,
            st.session_state.student_level
        )
    except Exception as e:
        st.error(f"성적 데이터를 불러오는데 실패했습니다: {str(e)}")
        st.info("아직 시험 결과가 없거나 데이터를 불러오는데 문제가 있습니다.")
    
    # 대시보드로 돌아가기 버튼
    if st.button("← 대시보드로 돌아가기", use_container_width=True):
        st.session_state.page = "student_dashboard"
        st.rerun()

def exam_page():
    """시험 페이지 - 모든 문제를 한 페이지에 표시합니다."""
    # 화면 초기화 방지를 위한 세션 상태 확인
    if "exam_start_flag" not in st.session_state:
        st.session_state.exam_start_flag = True
    
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 로딩 스피너 표시
    with st.spinner("시험 준비 중..."):
        # 시험 상태 확인
        if 'exam_initialized' not in st.session_state or not st.session_state.exam_initialized:
            # 시험 초기화
            st.session_state.exam_initialized = True
            st.session_state.student_answers = {}
            st.session_state.exam_problems = None  # 이미 로드된 문제가 있으면 초기화
            st.session_state.exam_answered_count = 0
            st.session_state.exam_start_time = time.time()
            
            # 시험 문제 로드
            try:
                st.session_state.exam_problems = load_exam_problems(
                    st.session_state.student_id, 
                    st.session_state.student_grade, 
                    20
                )
            except Exception as e:
                st.error(f"문제 로드 중 오류: {str(e)}")
                st.session_state.exam_problems = []
            
            # 문제 로드 확인
            if not st.session_state.exam_problems:
                st.error("문제를 로드하지 못했습니다. 다시 시도해주세요.")
                if st.button("대시보드로 돌아가기", key="go_back_dashboard_error"):
                    st.session_state.page = "student_dashboard"
                    st.rerun()
                return
    
    # 헤더 표시
    st.title("시험지")
    
    # 학생 정보 표시 (타이머 제거)
    st.markdown(f"학생: {st.session_state.student_name} | 학년: {st.session_state.student_grade} | 실력등급: {st.session_state.student_level}")
    
    # 시험 진행 상태
    actual_problem_count = len(st.session_state.exam_problems)
    st.info(f"총 {actual_problem_count}개의 문제가 있습니다. 모든 문제를 풀고 제출하세요.")
    
    # 문제 수 확인
    if actual_problem_count < 20:
        st.warning(f"현재 {actual_problem_count}개의 문제만 로드되었습니다.")
    
    # 폼 생성
    with st.form("exam_form", clear_on_submit=False):
        # 각 문제 표시
        for idx, problem in enumerate(st.session_state.exam_problems, 1):
            # 문제 ID
            problem_id = problem["문제ID"]
            
            # 문제 박스 생성
            with st.container(border=True):
                # 문제 헤더
                st.markdown(f"## 문제 {idx}/{actual_problem_count}")
                st.markdown(f"과목: {problem.get('과목', '영어')} | 학년: {problem.get('학년', '')} | 유형: {problem.get('문제유형', '객관식')} | 난이도: {problem.get('난이도', '중')}")
                
                # 문제 내용
                st.markdown(problem["문제내용"])
                
                # 저장된 답안 불러오기
                saved_answer = st.session_state.student_answers.get(problem_id, {})
                student_answer = saved_answer.get("제출답안", "")
                
                # 보기가 있는 경우 라디오 버튼으로 표시
                has_options = False
                if "보기정보" in problem and problem["보기정보"]:
                    options = []
                    option_texts = {}
                    
                    # 보기 중복 확인을 위한 집합
                    seen_options_text = set()
                    
                    try:
                        for key, text in problem["보기정보"].items():
                            # 중복된 보기 텍스트 제거
                            if text and text not in seen_options_text:
                                options.append(key)
                                option_texts[key] = text
                                seen_options_text.add(text)
                        
                        # 보기가 있는지 확인
                        if options:
                            has_options = True
                            # 선택 라디오 버튼
                            st.markdown("### 정답 선택:")
                            
                            # 인덱스 확인 로직 개선
                            index = None
                            if student_answer in options:
                                index = options.index(student_answer)
                            
                            selected = st.radio(
                                f"문제 {idx}",
                                options,
                                format_func=lambda x: f"{x}: {option_texts[x]}",
                                index=index,  # 저장된 답안이 없으면 선택하지 않음
                                key=f"radio_{problem_id}",
                                label_visibility="collapsed"
                            )
                            
                            # 학생 답안 저장
                            if selected is not None:  # 선택된 경우에만 저장
                                if problem_id not in st.session_state.student_answers:
                                    st.session_state.student_answers[problem_id] = problem.copy()
                                st.session_state.student_answers[problem_id]["제출답안"] = selected
                    except Exception as e:
                        st.error(f"보기 처리 중 오류: {str(e)}")
                
                # 보기가 없거나 처리 오류면 텍스트 입력으로 대체
                if not has_options:
                    # 선택형이지만 보기 정보가 없는 경우
                    if problem.get("문제유형") == "객관식":
                        st.error("이 문제에 대한 보기 정보가 없습니다. 직접 답안을 입력해주세요.")
                    
                    # 주관식인 경우 텍스트 입력
                    st.markdown("### 답안 입력:")
                    answer = st.text_input(
                        f"문제 {idx} 답안",
                        value=student_answer,
                        key=f"text_{problem_id}",
                        max_chars=200
                    )
                    
                    # 학생 답안 저장
                    if answer.strip():  # 입력된 경우에만 저장
                        if problem_id not in st.session_state.student_answers:
                            st.session_state.student_answers[problem_id] = problem.copy()
                        st.session_state.student_answers[problem_id]["제출답안"] = answer
        
        # 제출 버튼
        submit_button = st.form_submit_button("시험지 제출하기", use_container_width=True)
        
    # 폼 제출 후 처리 - 폼 바깥에서 처리하여 재렌더링 문제 해결
    if submit_button:
        with st.spinner("답안 제출 중..."):
            # 결과 처리 - 별도 함수로 추출
            success = process_exam_results()
            if success:
                st.session_state.exam_submitted = True
                st.session_state.page = "exam_score"
                st.rerun()
            else:
                st.error("결과 처리 중 오류가 발생했습니다. 다시 시도해주세요.")
    
    # 대시보드로 돌아가기
    if st.button("← 대시보드로 돌아가기", use_container_width=True):
        if st.session_state.student_answers:
            # 작성 중인 답안이 있는 경우 확인
            confirm = st.button("정말 나가시겠습니까? 저장되지 않은 답안은 사라집니다.", key="confirm_exit")
            if confirm:
                st.session_state.page = "student_dashboard"
                st.rerun()
        else:
            st.session_state.page = "student_dashboard"
            st.rerun()

def process_exam_results():
    """시험 결과를 처리하고 세션 상태에 저장합니다."""
    try:
        # 학생 답안 확인
        student_answers = st.session_state.student_answers
        if not student_answers:
            st.warning("제출된 답안이 없습니다. 적어도 하나 이상의 문제를 풀어주세요.")
            return False
        
        # 시험 결과 계산
        correct_count = 0
        total_problems = len(st.session_state.exam_problems)
        problem_details = {}
        
        # 각 문제별 정답 확인
        for problem in st.session_state.exam_problems:
            problem_id = problem["문제ID"]
            
            # 답안 정보
            student_answer_data = student_answers.get(problem_id, {})
            student_answer = student_answer_data.get("제출답안", "")
            correct_answer = problem.get("정답", "")
            
            # 정답 여부 확인
            if not student_answer:
                is_correct = False  # 답안 미제출은 오답 처리
            elif problem.get("문제유형") == "객관식":
                # 객관식: 정확히 일치해야 함
                is_correct = (student_answer == correct_answer)
            else:
                # 단답형/서술형: 대소문자 및 공백 무시하고 비교
                normalized_student = student_answer.lower().strip()
                normalized_correct = correct_answer.lower().strip()
                is_correct = (normalized_student == normalized_correct)
            
            # 정답 카운트 증가
            if is_correct:
                correct_count += 1
            
            # 문제별 상세 정보
            problem_details[problem_id] = {
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct
            }
        
        # 총점 계산 (100점 만점)
        if total_problems > 0:
            total_score = (correct_count / total_problems) * 100
        else:
            total_score = 0
        
        # 결과 저장
        st.session_state.exam_results = {
            "total_score": total_score,
            "correct_count": correct_count,
            "total_problems": total_problems,
            "details": problem_details,
            "exam_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 결과 서버에 저장 (옵션)
        try:
            # 스프레드시트에 저장 시도
            save_exam_result_to_sheets()
        except Exception as e:
            st.warning(f"결과 저장 중 오류 발생: {str(e)}")
            # 결과 저장 실패는 프로세스 진행에 영향 없음
        
        return True
    
    except Exception as e:
        st.error(f"시험 결과 처리 중 오류 발생: {str(e)}")
        return False

def save_exam_result_to_sheets():
    """시험 결과를 구글 시트에 저장합니다."""
    # 스프레드시트 연결
    sheet = connect_to_sheets()
    if not sheet:
        raise Exception("구글 시트에 연결할 수 없습니다.")
    
    try:
        # 학생 답안 워크시트
        answers_ws = sheet.worksheet("student_answers")
        
        # 각 문제별로 학생 답안 저장
        for problem_id, problem_data in st.session_state.student_answers.items():
            # 시험 정보
            result_data = st.session_state.exam_results["details"].get(problem_id, {})
            
            # 데이터 준비
            row_data = {
                "학생ID": st.session_state.student_id,
                "학생이름": st.session_state.student_name,
                "학년": st.session_state.student_grade,
                "문제ID": problem_id,
                "과목": problem_data.get("과목", ""),
                "문제유형": problem_data.get("문제유형", ""),
                "난이도": problem_data.get("난이도", ""),
                "제출답안": result_data.get("student_answer", ""),
                "정답여부": "O" if result_data.get("is_correct", False) else "X",
                "제출일시": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 행 추가
            answers_ws.append_row(list(row_data.values()))
        
        # 성적 분석 데이터 업데이트 (옵션)
        try:
            # 키워드 추출 및 약점 분석
            for problem_id, result in st.session_state.exam_results["details"].items():
                problem_data = st.session_state.student_answers.get(problem_id, {})
                
                # 키워드 추출 (없는 경우 빈 리스트)
                keywords = []
                if "키워드" in problem_data and problem_data["키워드"]:
                    if isinstance(problem_data["키워드"], str):
                        keywords = [k.strip() for k in problem_data["키워드"].split(',') if k.strip()]
                
                # 약점 분석 업데이트
                if keywords:
                    update_problem_stats(
                        st.session_state.student_id,
                        problem_id,
                        keywords,
                        result["is_correct"]
                    )
        except Exception as e:
            # 약점 분석 실패는 저장 프로세스 진행에 영향 없음
            st.warning(f"약점 분석 중 오류 발생: {str(e)}")
        
        return True
    
    except Exception as e:
        raise Exception(f"시험 결과 저장 중 오류: {str(e)}")

def exam_score_page():
    """시험 결과 페이지를 표시합니다."""
    
    if not check_student_login() or 'exam_results' not in st.session_state:
        st.error("시험 결과가 없습니다.")
        if st.button("대시보드로 돌아가기"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    # 학생 정보 표시
    st.title("📝 시험 결과")
    
    # 학생 정보 표시
    st.markdown(f"**학생**: {st.session_state.student_name} | **학년**: {st.session_state.student_grade} | **실력등급**: {st.session_state.student_level}")
    
    # 총점과 성적 표시
    results = st.session_state.exam_results
    total_score = results.get('total_score', 0)
    correct_count = results.get('correct_count', 0)
    total_problems = results.get('total_problems', 0)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총점", f"{total_score:.1f}점")
    
    with col2:
        st.metric("정답 개수", f"{correct_count}/{total_problems}")
    
    with col3:
        if total_problems > 0:
            correct_rate = (correct_count / total_problems) * 100
            st.metric("정답률", f"{correct_rate:.1f}%")
        else:
            st.metric("정답률", "0%")
    
    # 총점에 따른 메시지
    if total_score >= 90:
        st.success("🌟 훌륭합니다! 아주 좋은 성적입니다.")
    elif total_score >= 70:
        st.success("👍 잘했습니다! 조금 더 노력하면 더 좋은 결과를 얻을 수 있을 거예요.")
    elif total_score >= 50:
        st.warning("🔍 기본기를 다지는 것이 필요합니다. 어려웠던 부분을 중심으로 복습해보세요.")
    else:
        st.error("💪 더 많은 연습이 필요합니다. 포기하지 말고 꾸준히 공부해봅시다!")
    
    # 피드백 데이터 생성
    feedback_data = []
    for problem_id, detail in results.get('details', {}).items():
        problem_data = st.session_state.student_answers.get(problem_id, {})
        if not problem_data:
            continue
            
        # 문제 정보 추출
        question = problem_data.get('문제내용', '문제 정보 없음')
        student_answer = detail.get('student_answer', '답안 정보 없음')
        is_correct = detail.get('is_correct', False)
        correct_answer = detail.get('correct_answer', '정답 정보 없음')
        explanation = problem_data.get('해설', '')
        
        # 피드백 생성 또는 가져오기
        feedback = problem_data.get('피드백', '')
        
        if not feedback and student_answer:
            try:
                # API에서 피드백 생성
                from gpt_feedback import generate_feedback
                
                # 문제 정보 딕셔너리 생성
                problem_dict = {
                    "문제내용": question,
                    "정답": correct_answer,
                    "해설": explanation,
                    "문제유형": problem_data.get("문제유형", "객관식"),
                    "과목": problem_data.get("과목", ""),
                    "학년": problem_data.get("학년", ""),
                    "난이도": problem_data.get("난이도", ""),
                    "보기정보": problem_data.get("보기정보", {})
                }
                
                score, api_feedback = generate_feedback(problem_dict, student_answer)
                feedback = api_feedback
                
                # 결과 저장
                problem_data['피드백'] = feedback
                st.session_state.student_answers[problem_id] = problem_data
            except Exception as e:
                feedback = f"피드백 생성 중 오류: {str(e)}"
        
        # 문제 정보와 피드백 추가
        feedback_data.append({
            "problem_id": problem_id,
            "question": question,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": explanation,
            "feedback": feedback,
            "problem_data": problem_data
        })
    
    # 탭으로 결과 표시
    tab1, tab2, tab3 = st.tabs(["모든 문제", "정답 문제", "오답 문제"])
    
    # 보기 정보를 텍스트로 변환하는 함수
    def get_options_text(problem_data):
        options_text = ""
        if "보기정보" in problem_data and problem_data["보기정보"]:
            options = problem_data["보기정보"]
            for key in sorted(options.keys()):
                # 보기 글자만 추출 (예: "보기1" -> "1")
                option_num = key.replace("보기", "")
                options_text += f"**보기{option_num}**: {options[key]}\n\n"
        return options_text
    
    # 모든 문제 탭
    with tab1:
        st.header("모든 문제 결과")
        
        for idx, item in enumerate(feedback_data, 1):
            with st.expander(f"문제 {idx}: {'✅ 정답' if item['is_correct'] else '❌ 오답'}", expanded=False):
                st.markdown(f"**문제**: {item['question']}")
                
                # 보기 정보 표시
                options_text = get_options_text(item['problem_data'])
                if options_text:
                    st.markdown("### 보기:")
                    st.markdown(options_text)
                
                # 정답과 선택한 답안 표시
                student_answer_display = item['student_answer'] if item['student_answer'] else "제출한 답안 없음"
                
                # 객관식인지 확인
                is_objective = item['correct_answer'].startswith('보기')
                
                # 표 형식으로 정보 표시
                data = {
                    "": ["제출한 답안", "정답"],
                    "내용": [student_answer_display, item['correct_answer']]
                }
                st.table(data)
                
                # 선택지에 대한 설명 표시
                if is_objective and "보기정보" in item['problem_data']:
                    st.markdown("### 선택지 설명:")
                    
                    # 선택한 답안과 정답 강조
                    for key, value in sorted(item['problem_data']["보기정보"].items()):
                        option_num = key.replace("보기", "")
                        
                        # 선택한 답안과 정답 표시 형식 결정
                        prefix = ""
                        if key == item['student_answer']:
                            prefix = "🔍 " if not item['is_correct'] else "✅ "
                        elif key == item['correct_answer']:
                            prefix = "✅ " if not item['is_correct'] else ""
                        
                        st.markdown(f"{prefix}**보기{option_num}**: {value}")
                
                # 해설과 피드백 표시
                if item['explanation']:
                    st.markdown("### 해설:")
                    st.markdown(item['explanation'])
                
                st.markdown("### 첨삭 피드백:")
                if item['feedback']:
                    st.markdown(item['feedback'])
                else:
                    st.markdown("피드백이 생성되지 않았습니다.")
    
    # 정답 문제 탭
    with tab2:
        st.header("정답 문제")
        correct_items = [item for item in feedback_data if item['is_correct']]
        
        if not correct_items:
            st.warning("정답인 문제가 없습니다.")
        else:
            for idx, item in enumerate(correct_items, 1):
                with st.expander(f"문제 {idx}: ✅ 정답", expanded=False):
                    st.markdown(f"**문제**: {item['question']}")
                    
                    # 보기 정보 표시
                    options_text = get_options_text(item['problem_data'])
                    if options_text:
                        st.markdown("### 보기:")
                        st.markdown(options_text)
                    
                    # 정답과 선택한 답안 표시
                    student_answer_display = item['student_answer'] if item['student_answer'] else "제출한 답안 없음"
                    
                    # 표 형식으로 정보 표시
                    data = {
                        "": ["제출한 답안", "정답"],
                        "내용": [student_answer_display, item['correct_answer']]
                    }
                    st.table(data)
                    
                    # 해설과 피드백 표시
                    if item['explanation']:
                        st.markdown("### 해설:")
                        st.markdown(item['explanation'])
                    
                    st.markdown("### 첨삭 피드백:")
                    if item['feedback']:
                        st.markdown(item['feedback'])
                    else:
                        st.markdown("피드백이 생성되지 않았습니다.")
    
    # 오답 문제 탭
    with tab3:
        st.header("오답 문제")
        incorrect_items = [item for item in feedback_data if not item['is_correct']]
        
        if not incorrect_items:
            st.success("오답이 없습니다! 완벽합니다. 👏")
        else:
            for idx, item in enumerate(incorrect_items, 1):
                with st.expander(f"문제 {idx}: ❌ 오답", expanded=False):
                    st.markdown(f"**문제**: {item['question']}")
                    
                    # 보기 정보 표시
                    options_text = get_options_text(item['problem_data'])
                    if options_text:
                        st.markdown("### 보기:")
                        st.markdown(options_text)
                    
                    # 정답과 선택한 답안 표시
                    student_answer_display = item['student_answer'] if item['student_answer'] else "제출한 답안 없음"
                    
                    # 객관식인지 확인
                    is_objective = item['correct_answer'].startswith('보기')
                    
                    # 표 형식으로 정보 표시
                    data = {
                        "": ["제출한 답안", "정답"],
                        "내용": [student_answer_display, item['correct_answer']]
                    }
                    st.table(data)
                    
                    # 선택지에 대한 설명 표시
                    if is_objective and "보기정보" in item['problem_data']:
                        st.markdown("### 선택지 설명:")
                        
                        # 선택한 답안과 정답 강조
                        for key, value in sorted(item['problem_data']["보기정보"].items()):
                            option_num = key.replace("보기", "")
                            
                            # 선택한 답안과 정답 표시 형식 결정
                            prefix = ""
                            if key == item['student_answer']:
                                prefix = "🔍 "
                            elif key == item['correct_answer']:
                                prefix = "✅ "
                            
                            st.markdown(f"{prefix}**보기{option_num}**: {value}")
                    
                    # 해설과 피드백 표시
                    if item['explanation']:
                        st.markdown("### 해설:")
                        st.markdown(item['explanation'])
                    
                    st.markdown("### 첨삭 피드백:")
                    if item['feedback']:
                        st.markdown(item['feedback'])
                    else:
                        st.markdown("피드백이 생성되지 않았습니다.")
    
    # 대시보드로 돌아가기 버튼
    if st.button("← 대시보드로 돌아가기", use_container_width=True):
        st.session_state.page = "student_dashboard"
        st.rerun()

def main():
    """메인 애플리케이션 함수"""
    # 세션 상태 초기화
    initialize_session_state()
    
    # 타이머 시간 제한 설정 (50분 = 3000초) - 이 부분은 남겨두거나 필요에 따라 제거
    if 'exam_time_limit' not in st.session_state:
        st.session_state.exam_time_limit = 50 * 60  # 50분
    
    # CSS 스타일
    hide_streamlit_style = """
    <style>
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        div.block-container {padding-top: 2rem;}
        div.block-container {max-width: 1000px;}
        
        /* 버튼 스타일 */
        .stButton > button {
            font-weight: bold;
            padding: 8px 16px;
            width: 100%;
            border-radius: 6px;
        }
        
        /* 문제 컨테이너 */
        .question-container {
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* 진행 상태 표시 */
        .progress-container {
            background-color: #f0f0f0;
            border-radius: 6px;
            padding: 10px 15px;
            margin-bottom: 20px;
        }
    </style>
    """
    
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # 현재 페이지에 따라 내용 표시
    if st.session_state.page == "intro":
        intro_page()
    elif st.session_state.page == "admin":
        admin.admin_main()
    elif st.session_state.page == "student_login":
        student_login_page()
    elif st.session_state.page == "student_dashboard":
        student_dashboard()
    elif st.session_state.page == "problem":
        # problem_page 함수가 정의되지 않았으므로 학생 대시보드로 리디렉션
        st.session_state.page = "student_dashboard"
        st.rerun()
    elif st.session_state.page == "exam_page":
        exam_page()
    elif st.session_state.page == "my_performance":
        my_performance_page()
    elif st.session_state.page == "exam_result":
        # exam_result_page 함수가 정의되지 않았으므로 exam_score_page로 대체
        exam_score_page()
    elif st.session_state.page == "exam_score":
        exam_score_page()
    else:
        intro_page()

if __name__ == "__main__":
    main() 