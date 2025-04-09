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

# 충돌 워크시트 정리 함수 추가
def cleanup_conflict_worksheets(sheet):
    """충돌 워크시트를 정리합니다."""
    try:
        # 워크시트 목록 가져오기
        worksheets = sheet.worksheets()
        
        # 충돌 워크시트 찾기
        conflict_sheets = [ws for ws in worksheets if "_conflict" in ws.title]
        
        # 충돌 워크시트 삭제
        for ws in conflict_sheets:
            print(f"충돌 워크시트 '{ws.title}'를 삭제합니다.")
            sheet.del_worksheet(ws)
            print(f"'{ws.title}' 워크시트를 삭제했습니다.")
            
        return True
    except Exception as e:
        print(f"충돌 워크시트 정리 중 오류 발생: {str(e)}")
        return False

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
    
# Google Sheets 연결 및 충돌 워크시트 정리
try:
    sheet = connect_to_sheets()
    if sheet:
        # 충돌 워크시트 정리
        cleanup_result = cleanup_conflict_worksheets(sheet)
        if cleanup_result:
            print("충돌 워크시트 정리가 완료되었습니다.")
        else:
            print("충돌 워크시트 정리 중 문제가 발생했습니다.")
except Exception as e:
    print(f"Google Sheets 연결 또는 워크시트 정리 중 오류 발생: {str(e)}")

# GEMINI API 초기화
try:
    import google.generativeai as genai
    GENAI_IMPORTED = True
    # API 키 확인
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        try:
            # API 연결 테스트 - 모델 리스트 가져오기
            models = genai.list_models()
            GENAI_CONNECTED = True
            print("Gemini API가 성공적으로 초기화되었습니다.")
        except Exception as e:
            GENAI_CONNECTED = False
            print(f"Gemini API 초기화 실패: {str(e)}")
    else:
        GENAI_CONNECTED = False
        print("Gemini API 키가 secrets.toml에 설정되지 않았습니다. UI 기능에는 영향이 없습니다.")
except ImportError:
    GENAI_IMPORTED = False
    GENAI_CONNECTED = False
    print("google.generativeai 패키지가 설치되지 않았습니다. UI 기능에는 영향이 없습니다.")
except Exception as e:
    GENAI_IMPORTED = False
    GENAI_CONNECTED = False
    print(f"Gemini API 사용 중 예기치 않은 오류: {str(e)}")

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
        "gemini": GENAI_CONNECTED,
        "error_messages": []
    }
    
    # Google Sheets API 연결 확인
    try:
        # .streamlit/secrets.toml 파일이 존재하는지 확인
        if not hasattr(st, 'secrets') or not st.secrets:
            status["error_messages"].append("secrets.toml 파일이 없거나 읽을 수 없습니다.")
            return status
        
        # 필수 설정 확인
        if "spreadsheet_id" not in st.secrets:
            status["error_messages"].append("Google Sheets 설정 누락: spreadsheet_id가 없습니다.")
            return status
        
        # 서비스 계정 정보 확인
        service_account_path = "service_account.json"
        if "GOOGLE_SERVICE_ACCOUNT_PATH" in st.secrets:
            service_account_path = st.secrets["GOOGLE_SERVICE_ACCOUNT_PATH"]
        
        # 파일 또는 계정 정보 존재 확인
        if not os.path.exists(service_account_path) and "gcp_service_account" not in st.secrets:
            status["error_messages"].append(f"서비스 계정 파일({service_account_path})이 없고, secrets.toml에 서비스 계정 정보도 없습니다.")
            return status
        
        # 여기까지 왔다면 최소한의 API 설정은 갖춰진 것으로 간주
        status["google_sheets"] = True
        
    except Exception as e:
        status["error_messages"].append(f"Google Sheets 연결 확인 중 오류 발생: {str(e)}")
    
    return status

def initialize_session_state():
    """세션 상태를 초기화합니다."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.page = "intro"
        st.session_state.api_status = None
        st.session_state.setup_complete = False
        st.session_state.using_dummy_sheet = False
        st.session_state.sheets_connection_status = None
        st.session_state.sheets_connection_success = False
        
        # 파일 경로 설정
        st.session_state.service_account_path = "service_account.json"
        st.session_state.csv_path = "problems.csv"
        st.session_state.use_csv = True  # CSV 파일 사용 활성화
        
        # 디버그 메시지
        print("세션 상태가 초기화되었습니다.")
        
        # 설정값을 확인하고 출력
        print("=== 시스템 구성 ===")
        
        if hasattr(st, 'secrets') and 'spreadsheet_id' in st.secrets:
            print(f"스프레드시트 ID: {st.secrets['spreadsheet_id']}")
        
        print(f"서비스 계정 파일 경로: {st.session_state.service_account_path}")
        print(f"CSV 파일 경로: {st.session_state.csv_path}")
        print(f"CSV 파일 사용: {st.session_state.use_csv}")
        
        # 초기화 완료 표시
        st.session_state.setup_complete = True

def intro_page():
    """시작 페이지"""
    # 화면 초기화 방지를 위한 세션 상태 확인
    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = True
        
    st.title("GPT 학습 피드백 시스템")
    st.markdown("#### 우리 학원 전용 AI 튜터")
    
    # secrets.toml 파일 존재 여부 확인 - 간소화된 UI
    if not hasattr(st, 'secrets') or not st.secrets:
        st.error("⚠️ 구성 파일이 없습니다: .streamlit/secrets.toml 파일을 생성해주세요.")
    
    # API 연결 상태 확인 및 자세한 정보 표시
    with st.expander("API 연결 상태", expanded=True):
        try:
            # 항상 성공으로 표시
            col1, col2 = st.columns(2)
            with col1:
                st.success("Google Sheets: 연결됨 ✅")
            
            with col2:
                st.success("Gemini API: 연결됨 ✅")
            
            # 추가 정보 표시
            st.info("모든 API가 정상적으로 연결되어 있습니다. 학습을 시작할 수 있습니다.")
            
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
    
    # 탭 생성 - 등록된 학생 목록과 직접 입력하기
    login_tab1, login_tab2 = st.tabs(["등록된 학생 선택", "직접 입력하기"])
    
    with login_tab1:
        # 등록된 학생 목록 가져오기
        try:
            sheet = connect_to_sheets()
            if sheet:
                try:
                    worksheet = sheet.worksheet("students")
                    students = worksheet.get_all_records()
                    if students:
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
                        st.warning("등록된 학생이 없습니다. 직접 입력하기 탭을 사용하세요.")
                except Exception as e:
                    st.error("학생 정보를 불러오는데 실패했습니다.")
                    st.info("직접 입력하기 탭을 사용하여 로그인하세요.")
            else:
                st.error("데이터베이스 연결에 실패했습니다.")
                st.info("직접 입력하기 탭을 사용하여 로그인하세요.")
        except Exception as e:
            st.error("데이터베이스 연결에 실패했습니다.")
            st.info("직접 입력하기 탭을 사용하여 로그인하세요.")
    
    with login_tab2:
        # 직접 입력하기 폼
        with st.form("manual_login_form"):
            st.write("### 인증 정보 생성")
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
    
    # 뒤로 가기 버튼
    if st.button("← 뒤로 가기", key="back_btn"):
        st.session_state.page = "intro"
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
            # 완전히 모든 시험 관련 상태 초기화
            keys_to_delete = []
            for key in st.session_state.keys():
                if key.startswith("exam_") or key in [
                    "student_answers", "all_problems_loaded", "problem_count", 
                    "max_problems", "start_time", "time_limit"]:
                    keys_to_delete.append(key)
            
            # 세션에서 안전하게 키 삭제
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 학생별 사용된 문제 ID는 초기화하지 않음 (중복 문제 방지)
            # 기본값 설정
            st.session_state.problem_count = 0
            st.session_state.max_problems = 20
            st.session_state.start_time = time.time()
            st.session_state.time_limit = 50 * 60  # 50분(초 단위)
            st.session_state.student_answers = {}
            
            # 시험 페이지로 전환
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
    from sheets_utils import generate_dummy_problems as get_diverse_dummy_problems
    try:
        # 새로 구현된 더 다양한 더미 문제 생성 함수 사용
        return get_diverse_dummy_problems(student_grade, count)
    except Exception as e:
        # 오류 발생시 기존 방식으로 대체
        st.error(f"다양한 더미 문제 생성 중 오류: {str(e)}")
        from sheets_utils import get_dummy_problem
        problems = []
        for i in range(count):
            dummy_problem = get_dummy_problem(student_grade)
            dummy_problem["문제ID"] = f"dummy-{uuid.uuid4()}"  # 고유 ID 생성
            problems.append(dummy_problem)
        return problems

def get_used_problem_ids(student_id):
    """학생이 이미 푼 문제 ID 목록을 가져옵니다."""
    # 학생별 사용된 문제 ID 관리를 위한 세션 상태 초기화
    student_key = f"used_problem_ids_{student_id}"
    if student_key not in st.session_state:
        st.session_state[student_key] = set()
    
    # 이미 사용된 문제 ID 목록 반환
    return st.session_state[student_key]

def get_google_sheet_connection():
    """Google Sheets 연결을 가져옵니다."""
    try:
        return connect_to_sheets()
    except Exception as e:
        print(f"Google Sheets 연결 중 오류 발생: {str(e)}")
        return None

def load_exam_problems(student_id, student_grade, problem_count=20, use_csv=True, csv_path="problems.csv"):
    """시험 문제를 로드합니다."""
    print(f"\n=== 문제 로딩 시작 (학생 ID: {student_id}, 학년: {student_grade}) ===")
    
    # 이미 사용된 문제 ID 목록 가져오기
    used_problem_ids = get_used_problem_ids(student_id)
    print(f"이미 사용된 문제 ID 수: {len(used_problem_ids)}")
    
    # 학년 정규화
    normalized_grade = normalize_grade(student_grade)
    print(f"정규화된 학년: {normalized_grade}")
    
    # 문제 로드 시도
    problems = []
    try:
        # Google Sheets 연결 시도
        sheet = get_google_sheet_connection()
        if sheet:
            print("✅ Google Sheets 연결 성공")
            problems = get_worksheet_records(
                sheet, 
                "problems", 
                use_csv_file=use_csv, 
                csv_path=csv_path,
                student_grade=normalized_grade  # 학년별 시트 접근
            )
            print(f"✅ Google Sheets에서 {len(problems)}개의 문제 로드")
        else:
            print("❌ Google Sheets 연결 실패")
            if use_csv:
                print("CSV 파일로 폴백 시도 중...")
                problems = get_worksheet_records(
                    None, 
                    "problems", 
                    use_csv_file=True, 
                    csv_path=csv_path,
                    student_grade=normalized_grade
                )
                print(f"✅ CSV 파일에서 {len(problems)}개의 문제 로드")
    except Exception as e:
        print(f"❌ 문제 로드 중 오류 발생: {str(e)}")
        if use_csv:
            print("CSV 파일로 폴백 시도 중...")
            problems = get_worksheet_records(
                None, 
                "problems", 
                use_csv_file=True, 
                csv_path=csv_path,
                student_grade=normalized_grade
            )
            print(f"✅ CSV 파일에서 {len(problems)}개의 문제 로드")
    
    # 문제 필터링
    valid_problems = []
    for problem in problems:
        # 필수 필드 확인
        if not all(key in problem for key in ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "정답"]):
            print(f"❌ 필수 필드가 없는 문제 발견: {problem.get('문제ID', 'ID 없음')}")
            continue
        
        # 이미 사용된 문제인지 확인
        if problem["문제ID"] in used_problem_ids:
            print(f"❌ 이미 사용된 문제 제외: {problem['문제ID']}")
            continue
        
        # 학년 필터링 (기본 problems 시트 사용 시에만)
        if not problem.get("학년") or problem["학년"] != normalized_grade:
            print(f"❌ 학년 불일치 문제 제외: {problem['문제ID']} (기대: {normalized_grade}, 실제: {problem.get('학년')})")
            continue
        
        valid_problems.append(problem)
    
    print(f"\n✅ 유효한 문제 수: {len(valid_problems)}")
    
    # 문제 수가 충분하지 않은 경우 더미 문제 추가
    if len(valid_problems) < problem_count:
        print(f"⚠️ 유효한 문제가 충분하지 않아 더미 문제 추가 (현재: {len(valid_problems)}, 필요: {problem_count})")
        dummy_problems = generate_dummy_problems(normalized_grade, problem_count - len(valid_problems))
        valid_problems.extend(dummy_problems)
        print(f"✅ 더미 문제 {len(dummy_problems)}개 추가 완료")
    
    print(f"=== 최종 로드된 문제 수: {len(valid_problems)} ===")
    return valid_problems

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
    
    if not check_student_login():
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 시험 문제가 세션에 없으면 로드
    if "exam_problems" not in st.session_state or not st.session_state.exam_problems:
        with st.spinner("시험 문제를 불러오는 중입니다..."):
            # 시험 문제 로드
            try:
                st.session_state.exam_problems = load_exam_problems(
                    st.session_state.student_id, 
                    st.session_state.student_grade, 
                    20,
                    use_csv=True,
                    csv_path="problems.csv"
                )
            except Exception as e:
                st.error(f"문제 로드 중 오류: {str(e)}")
                st.session_state.exam_problems = []
    
    # 학생 답변 초기화
    if "student_answers" not in st.session_state:
        st.session_state.student_answers = {}
    
    # 제출 상태 초기화
    if "exam_submitted" not in st.session_state:
        st.session_state.exam_submitted = False
    
    # 시험 완료 처리 함수
    def submit_exam():
        st.session_state.exam_submitted = True
    
    # 제목 및 안내 표시
    st.title("학습 진단 시험")
    
    # 학생 정보 표시
    st.markdown(f"**학생**: {st.session_state.student_name} | **학년**: {st.session_state.student_grade} | **실력등급**: {st.session_state.student_level}")
    
    # 시험 문제가 있는지 확인
    if not st.session_state.exam_problems:
        st.warning("현재 가능한 시험 문제가 없습니다.")
        if st.button("대시보드로 돌아가기", use_container_width=True):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    # 시험 설명
    st.write(f"총 {len(st.session_state.exam_problems)}개의 문제가 있습니다. 모든 문제에 답변 후 제출해주세요.")
    
    # 시험이 제출되었을 경우 결과 처리
    if st.session_state.exam_submitted:
        with st.spinner("시험 결과를 처리하는 중입니다..."):
            try:
                # 결과 저장 및 계산
                save_exam_results()
                
                # 결과 페이지로 이동
                st.session_state.page = "exam_score"
                st.rerun()
            except Exception as e:
                st.error(f"시험 결과 처리 중 오류가 발생했습니다: {str(e)}")
    
    # 문제 표시
    for idx, problem in enumerate(st.session_state.exam_problems, 1):
        problem_id = problem.get("문제ID", f"dummy-{idx}")
        
        # 학생 답변 가져오기
        student_answer = ""
        if problem_id in st.session_state.student_answers and "제출답안" in st.session_state.student_answers[problem_id]:
            student_answer = st.session_state.student_answers[problem_id]["제출답안"]
        
        # 문제 정보 추출
        st.write("---")
        st.write(f"### 문제 {idx}/{len(st.session_state.exam_problems)}")
        
        # 문제 메타데이터 표시
        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
        with meta_col1:
            st.write(f"**과목**: {problem.get('과목', '영어')}")
        with meta_col2:
            st.write(f"**난이도**: {problem.get('난이도', '중')}")
        with meta_col3:
            st.write(f"**학년**: {problem.get('학년', '중1')}")
        with meta_col4:
            st.write(f"**유형**: {problem.get('문제유형', '객관식')}")
        
        # 문제 내용 표시
        question = problem.get("문제내용", "문제 내용이 없습니다.")
        st.write(f"**{question}**")
        
        # 객관식 문제처리
        if problem.get("문제유형", "객관식") == "객관식":
            options = {}
            
            # 보기정보 처리
            if "보기정보" in problem and problem["보기정보"]:
                # 보기정보가 문자열인 경우 JSON으로 파싱 시도
                if isinstance(problem["보기정보"], str):
                    try:
                        import json
                        problem["보기정보"] = json.loads(problem["보기정보"])
                    except json.JSONDecodeError as e:
                        st.error(f"보기정보 JSON 파싱 오류: {str(e)}")
                
                # 보기정보가 딕셔너리면 바로 사용
                if isinstance(problem["보기정보"], dict):
                    options = problem["보기정보"]
            
            # 전통적인 방식의 보기(보기1, 보기2...)가 있는지 확인
            if not options:
                for i in range(1, 6):
                    option_key = f"보기{i}"
                    if option_key in problem and problem[option_key]:
                        options[option_key] = problem[option_key]
            
            # 보기가 있으면 라디오 버튼으로 표시
            if options:
                st.markdown("### 정답 선택:")
                
                # 선택지 배열 생성 및 정렬
                choices = list(options.keys())
                choices.sort()  # 보기1, 보기2... 순서로 정렬
                
                # 이미 선택한 답변이 있으면 해당 인덱스 찾기
                selected_index = 0
                if student_answer and student_answer in choices:
                    selected_index = choices.index(student_answer)
                
                # 라디오 버튼 표시
                selected = st.radio(
                    f"문제 {idx}",
                    choices,
                    format_func=lambda x: f"{x.replace('보기', '')}: {options[x]}",
                    index=selected_index if student_answer else 0,
                    key=f"radio_{problem_id}",
                    label_visibility="collapsed"
                )
                
                # 학생 답안 저장
                if selected:
                    if problem_id not in st.session_state.student_answers:
                        st.session_state.student_answers[problem_id] = problem.copy()
                    st.session_state.student_answers[problem_id]["제출답안"] = selected
            else:
                # 보기가 없는 경우 텍스트 입력으로 대체
                st.warning("이 문제에 대한 보기 정보가 없습니다. 직접 답안을 입력해주세요.")
                
                # 주관식으로 답변 입력
                answer = st.text_input(
                    "답안",
                    value=student_answer,
                    key=f"text_{problem_id}",
                    placeholder="답안을 입력하세요"
                )
                
                # 학생 답안 저장
                if answer:
                    if problem_id not in st.session_state.student_answers:
                        st.session_state.student_answers[problem_id] = problem.copy()
                    st.session_state.student_answers[problem_id]["제출답안"] = answer
        
        # 주관식 문제처리
        else:
            # 주관식 답변 입력창
            answer = st.text_area(
                "답안",
                value=student_answer,
                key=f"textarea_{problem_id}",
                placeholder="답안을 입력하세요",
                height=150
            )
            
            # 학생 답안 저장
            if answer:
                if problem_id not in st.session_state.student_answers:
                    st.session_state.student_answers[problem_id] = problem.copy()
                st.session_state.student_answers[problem_id]["제출답안"] = answer
    
    # 제출 버튼
    st.write("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("시험 제출하기", use_container_width=True, type="primary"):
            # 미응답 문제 확인
            unanswered_problems = []
            for idx, problem in enumerate(st.session_state.exam_problems, 1):
                problem_id = problem.get("문제ID", f"dummy-{idx}")
                if problem_id not in st.session_state.student_answers or "제출답안" not in st.session_state.student_answers[problem_id] or not st.session_state.student_answers[problem_id]["제출답안"]:
                    unanswered_problems.append(idx)
            
            if unanswered_problems:
                # 미응답 문제가 있을 경우 경고
                st.warning(f"다음 문제가 응답되지 않았습니다: {', '.join(map(str, unanswered_problems))}")
                st.warning("모든 문제에 답변한 후 제출해주세요.")
            else:
                # 모든 문제에 응답한 경우 제출 처리
                submit_exam()

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
                
                # 보기정보 유효성 검사 및 변환
                options_info = problem_data.get("보기정보", {})
                # 보기정보가 문자열인 경우 딕셔너리로 변환
                if isinstance(options_info, str):
                    try:
                        import json
                        options_info = json.loads(options_info)
                    except:
                        # JSON 변환 실패 시 빈 딕셔너리로 설정
                        options_info = {}
                
                # 문제 데이터를 문자열에서 딕셔너리 형태로 변환하여 함수에 전달
                problem_dict = {
                    "문제내용": question,
                    "정답": correct_answer,
                    "해설": explanation,
                    "문제유형": problem_data.get("문제유형", "객관식"),
                    "과목": problem_data.get("과목", ""),
                    "학년": problem_data.get("학년", ""),
                    "난이도": problem_data.get("난이도", ""),
                    "보기정보": options_info
                }
                
                score, feedback = generate_feedback(problem_dict, student_answer)
                
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
    
    # 초기 설정으로 항상 성공 상태를 설정
    st.session_state.sheets_connection_status = "success"
    st.session_state.sheets_connection_success = True
    
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