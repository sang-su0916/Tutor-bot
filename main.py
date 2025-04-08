import streamlit as st
import time
import uuid
import random  # random 모듈 추가

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

# 세션 상태 초기화
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

def intro_page():
    """시작 페이지"""
    st.title("GPT 학습 피드백 시스템")
    st.markdown("#### 우리 학원 전용 AI 튜터")
    
    # API 연결 상태 확인 (옵션)
    with st.expander("API 연결 상태"):
        api_status = check_api_connections()
        
        col1, col2 = st.columns(2)
        with col1:
            if api_status["google_sheets"]:
                st.success("Google Sheets: 연결됨 ✅")
            else:
                st.error("Google Sheets: 연결 안됨 ❌")
        
        with col2:
            if api_status["gemini"]:
                st.success("Gemini API: 연결됨 ✅")
            else:
                st.error("Gemini API: 연결 안됨 ❌")
        
        if api_status["error_messages"]:
            st.markdown("#### 오류 메시지")
            for msg in api_status["error_messages"]:
                st.warning(msg)
    
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
            # 문제 풀기 세션 초기화
            st.session_state.problem_count = 0
            st.session_state.max_problems = 20
            st.session_state.start_time = time.time()
            st.session_state.time_limit = 50 * 60  # 50분(초 단위)
            st.session_state.student_answers = {}
            st.session_state.all_problems_loaded = False
            st.session_state.page = "exam_page"
            st.rerun()
    
    with col2:
        if st.button("📊 나의 성적 분석", use_container_width=True):
            st.session_state.page = "my_performance"
            st.rerun()
    
    # 로그아웃 버튼
    if st.button("로그아웃", key="logout_dashboard_btn"):
        # 세션 상태 초기화
        for key in list(st.session_state.keys()):
            if key != "initialized" and key != "page":
                del st.session_state[key]
        st.session_state.page = "intro"
        st.rerun()

def load_exam_problems(student_id, student_grade, problem_count=20):
    """
    시험에 사용할 문제를 학생 학년과 다양한 유형을 고려하여 로드합니다.
    """
    problems = []
    used_problem_ids = set()
    attempts = 0
    max_attempts = 100  # 최대 시도 횟수 (문제가 충분하지 않은 경우 무한 루프 방지)
    
    sheet = connect_to_sheets()
    if not sheet:
        st.error("Google Sheets 연결에 실패했습니다.")
        return problems
    
    # 문제 워크시트에서 모든 문제 가져오기
    try:
        problems_ws = sheet.worksheet("problems")
        all_problems = problems_ws.get_all_records()
    except Exception as e:
        st.error(f"문제 데이터를 가져오는데 실패했습니다: {str(e)}")
        return problems
    
    # 학년에 맞는 문제만 필터링
    valid_problems = []
    for p in all_problems:
        if ("문제ID" in p and "학년" in p and "문제내용" in p and "정답" in p and 
            p["학년"] == student_grade.replace("학년", "").strip()):
            valid_problems.append(p)
    
    if not valid_problems:
        st.warning(f"{student_grade} 학년에 맞는 문제가 없습니다. 모든 문제를 사용합니다.")
        valid_problems = all_problems
    
    # 문제 유형별로 분류
    problem_types = {}
    for p in valid_problems:
        if "문제유형" in p and p["문제유형"]:
            ptype = p["문제유형"]
            if ptype not in problem_types:
                problem_types[ptype] = []
            problem_types[ptype].append(p)
    
    # 각 유형별로 골고루 문제 선택
    remaining_count = problem_count
    if problem_types:
        # 각 유형별로 최소 문제 수 계산
        type_counts = {}
        min_per_type = max(1, problem_count // len(problem_types))
        
        for ptype, type_problems in problem_types.items():
            # 유형별 문제 수와 최소 요구 수 중 작은 값 선택
            type_counts[ptype] = min(len(type_problems), min_per_type)
            remaining_count -= type_counts[ptype]
        
        # 유형별로 문제 선택
        for ptype, count in type_counts.items():
            type_problems = problem_types[ptype]
            # 무작위로 선택
            selected = random.sample(type_problems, count) if len(type_problems) > count else type_problems
            
            for p in selected:
                if p["문제ID"] not in used_problem_ids:
                    problems.append(process_problem(p))
                    used_problem_ids.add(p["문제ID"])
    
    # 나머지 문제 수는 무작위로 선택
    remaining_valid_problems = [p for p in valid_problems if p["문제ID"] not in used_problem_ids]
    
    while len(problems) < problem_count and remaining_valid_problems and attempts < max_attempts:
        random_problem = random.choice(remaining_valid_problems)
        if random_problem["문제ID"] not in used_problem_ids:
            problems.append(process_problem(random_problem))
            used_problem_ids.add(random_problem["문제ID"])
            remaining_valid_problems.remove(random_problem)
        attempts += 1
    
    # 충분한 문제가 없는 경우 더미 문제로 채우기
    while len(problems) < problem_count:
        dummy_problem = get_dummy_problem(student_grade)
        dummy_problem["문제ID"] = f"dummy-{uuid.uuid4()}"  # 고유 ID 생성
        if dummy_problem["문제ID"] not in used_problem_ids:
            problems.append(dummy_problem)
            used_problem_ids.add(dummy_problem["문제ID"])
    
    return problems[:problem_count]  # 최대 problem_count개 반환

def process_problem(problem):
    """문제 데이터를 정리하여 반환합니다."""
    processed = {
        "문제ID": problem["문제ID"],
        "과목": problem.get("과목", "영어"),
        "학년": problem.get("학년", ""),
        "문제유형": problem.get("문제유형", "객관식"),
        "난이도": problem.get("난이도", "중"),
        "문제내용": problem["문제내용"],
        "정답": problem["정답"],
        "키워드": problem.get("키워드", ""),
        "해설": problem.get("해설", "")
    }
    
    # 보기 정보 처리
    processed["보기정보"] = {}
    for i in range(1, 6):
        option_key = f"보기{i}"
        if option_key in problem and problem[option_key]:
            processed["보기정보"][option_key] = problem[option_key]
    
    return processed

def exam_page():
    """시험 페이지 - 모든 문제를 한 페이지에 표시합니다."""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 시험 상태 확인
    if 'exam_initialized' not in st.session_state or not st.session_state.exam_initialized:
        st.session_state.exam_initialized = True
        st.session_state.student_answers = {}
        st.session_state.exam_answered_count = 0
        st.session_state.exam_start_time = time.time()
        st.session_state.exam_time_limit = 50 * 60  # 50분
        
        # 시험 문제 로드
        st.session_state.exam_problems = load_exam_problems(
            st.session_state.student_id, 
            st.session_state.student_grade, 
            20
        )
    
    # 헤더 표시
    st.title("시험지")
    
    # 남은 시간 계산
    elapsed_time = time.time() - st.session_state.exam_start_time
    remaining_time = max(0, st.session_state.exam_time_limit - elapsed_time)
    minutes, seconds = divmod(int(remaining_time), 60)
    
    # 학생 정보 및 남은 시간 표시
    st.markdown(f"남은 시간: {minutes:02d}:{seconds:02d}")
    st.markdown(f"학생: {st.session_state.student_name} | 학년: {st.session_state.student_grade} | 실력등급: {st.session_state.student_level}")
    
    # 남은 시간이 0이면 자동 제출
    if remaining_time <= 0 and 'exam_submitted' not in st.session_state:
        st.session_state.exam_submitted = True
        st.session_state.page = "exam_score"
        st.rerun()
    
    # 시험 진행 상태
    st.info(f"총 20개의 문제가 있습니다. 모든 문제를 풀고 제출하세요.")
    
    # 폼 생성
    with st.form("exam_form"):
        for idx, problem in enumerate(st.session_state.exam_problems, 1):
            # 문제 ID
            problem_id = problem["문제ID"]
            
            # 문제 박스 생성
            with st.container(border=True):
                # 문제 헤더
                st.markdown(f"## 문제 {idx}/20")
                st.markdown(f"과목: {problem['과목']} | 학년: {problem['학년']} | 유형: {problem['문제유형']} | 난이도: {problem['난이도']}")
                
                # 문제 내용
                st.markdown(problem["문제내용"])
                
                # 저장된 답안 불러오기
                saved_answer = st.session_state.student_answers.get(problem_id, {}).get("제출답안", "")
                
                # 보기가 있는 경우 라디오 버튼으로 표시
                if "보기정보" in problem and problem["보기정보"]:
                    options = []
                    option_texts = {}
                    
                    # 보기 중복 확인을 위한 집합
                    seen_options_text = set()
                    
                    for key, text in problem["보기정보"].items():
                        # 중복된 보기 텍스트 제거
                        if text not in seen_options_text:
                            options.append(key)
                            option_texts[key] = text
                            seen_options_text.add(text)
                    
                    # 선택 라디오 버튼
                    st.markdown("### 정답 선택:")
                    selected = st.radio(
                        f"문제 {idx}",
                        options,
                        format_func=lambda x: f"{x}: {option_texts[x]}",
                        index=options.index(saved_answer) if saved_answer in options else 0,
                        key=f"radio_{problem_id}",
                        label_visibility="collapsed"
                    )
                    
                    # 학생 답안 저장
                    if problem_id not in st.session_state.student_answers:
                        st.session_state.student_answers[problem_id] = problem.copy()
                    st.session_state.student_answers[problem_id]["제출답안"] = selected
                    
                else:
                    # 주관식인 경우 텍스트 입력
                    st.markdown("### 답안 입력:")
                    answer = st.text_input(
                        f"문제 {idx} 답안",
                        value=saved_answer,
                        key=f"text_{problem_id}",
                        max_chars=200
                    )
                    
                    # 학생 답안 저장
                    if problem_id not in st.session_state.student_answers:
                        st.session_state.student_answers[problem_id] = problem.copy()
                    st.session_state.student_answers[problem_id]["제출답안"] = answer
        
        # 제출 버튼
        submit_button = st.form_submit_button("시험지 제출하기", use_container_width=True)
        
        if submit_button:
            # 제출 처리
            st.session_state.exam_submitted = True
            st.session_state.page = "exam_score"
            st.rerun()
    
    # 대시보드로 돌아가기
    if st.button("← 대시보드", use_container_width=True):
        st.session_state.page = "student_dashboard"
        st.rerun()

def my_performance_page():
    """학생 성적 분석 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
        
    # 학생 성적 대시보드 표시
    show_student_performance_dashboard(
        st.session_state.student_id,
        st.session_state.get("student_name", "학생"),
        st.session_state.get("student_grade", ""),
        st.session_state.get("student_level", "")
    )
    
    # 대시보드로 돌아가기 버튼
    if st.button("← 대시보드로 돌아가기"):
        st.session_state.page = "student_dashboard"
        st.rerun()

def result_page():
    """결과 페이지"""
    st.title("채점 결과")
    
    if not hasattr(st.session_state, 'current_problem') or st.session_state.current_problem is None:
        st.error("문제 정보를 찾을 수 없습니다.")
        if st.button("대시보드로 돌아가기"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    problem = st.session_state.current_problem
    student_answer = st.session_state.get("student_answer", "")
    
    # 문제 정보 표시
    st.markdown(f"**과목**: {problem['과목']} | **학년**: {problem['학년']} | **유형**: {problem['문제유형']} | **난이도**: {problem['난이도']}")
    
    # 진행 상태 표시
    if 'problem_count' in st.session_state and 'max_problems' in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**진행상황**: {st.session_state.problem_count}/{st.session_state.max_problems} 문제")
            
        with col2:
            # 남은 시간 표시 (있는 경우)
            if 'start_time' in st.session_state and 'time_limit' in st.session_state:
                elapsed_time = time.time() - st.session_state.start_time
                remaining_time = max(0, st.session_state.time_limit - elapsed_time)
                mins, secs = divmod(int(remaining_time), 60)
                time_str = f"{mins:02d}:{secs:02d}"
                st.markdown(f"**남은 시간**: {time_str}")
    
    # 문제 내용
    st.subheader("문제")
    st.markdown(problem.get("문제내용", "문제 내용을 불러올 수 없습니다."))
    
    # 문제 유형 확인 (객관식 또는 단답형)
    is_multiple_choice = st.session_state.get("is_multiple_choice", False)
    
    # 점수에 따른 색상 설정
    score = st.session_state.get("score", 0)
    score_color = "success" if score == 100 else "error"
    
    # 정답/오답 표시
    if is_multiple_choice:
        # 객관식 문제의 경우 보기 텍스트 찾기
        answer_text = ""
        correct_text = ""
        correct_option = problem.get("정답", "")
        
        for i in range(1, 6):
            option_key = f"보기{i}"
            if option_key in problem and problem[option_key]:
                if option_key == student_answer:
                    answer_text = problem[option_key]
                if option_key == correct_option:
                    correct_text = problem[option_key]
        
        # 학생 답안 표시 컨테이너
        st.container(height=None, border=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 제출한 답안")
            st.markdown(f"**{student_answer}**: {answer_text}")
        with col2:
            st.markdown("#### 정답")
            st.markdown(f"**{correct_option}**: {correct_text}")
        
        # 점수 표시
        if score == 100:
            st.success("정답입니다! 100점")
        else:
            st.error(f"틀렸습니다. {score}점")
    else:
        # 단답형 문제
        correct_answer = problem.get("정답", "")
        
        # 학생 답안 표시 컨테이너
        st.container(height=None, border=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 제출한 답안")
            st.markdown(f"**{student_answer}**")
        with col2:
            st.markdown("#### 정답")
            st.markdown(f"**{correct_answer}**")
        
        # 점수 표시
        if score == 100:
            st.success("정답입니다! 100점")
        else:
            st.error(f"틀렸습니다. {score}점")
    
    # 해설과 피드백
    st.subheader("문제 해설")
    st.markdown(problem.get("해설", ""))
    
    # AI 피드백
    feedback = st.session_state.feedback
    if feedback:
        st.subheader("AI 튜터 피드백")
        with st.container(height=None, border=True):
            st.markdown(feedback)
    
    # 키워드 표시
    if "키워드" in problem and problem["키워드"]:
        st.markdown(f"**학습 키워드**: {problem['키워드']}")
    
    # 버튼들
    st.write("")  # 공백 추가
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("다음 문제", key="next_problem_btn", use_container_width=True):
            # 다음 문제를 위한 상태 초기화
            st.session_state.current_problem = None
            st.session_state.submitted = False
            st.session_state.feedback = None
            st.session_state.score = None
            st.session_state.show_result = False
            
            # 문제 카운트 증가
            if 'problem_count' in st.session_state:
                st.session_state.problem_count += 1
                
            st.rerun()
    
    with col2:
        if st.button("나의 성적 분석", key="view_perf_btn", use_container_width=True):
            st.session_state.page = "my_performance"
            st.rerun()
    
    with col3:
        if st.button("대시보드", key="to_dashboard_btn", use_container_width=True):
            st.session_state.page = "student_dashboard"
            st.rerun()

def exam_result_page():
    """시험 결과 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    st.title("시험 완료!")
    
    # 시간 및 문제 수 표시
    if 'start_time' in st.session_state and 'time_limit' in st.session_state:
        elapsed_time = time.time() - st.session_state.start_time
        mins, secs = divmod(int(min(elapsed_time, st.session_state.time_limit)), 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        st.markdown(f"### 시험 시간: {time_str}")
        
    st.markdown(f"### 총 문제 수: {len(st.session_state.get('student_answers', {}))}/{st.session_state.get('max_problems', 20)}")
    
    # 시험지 제출 확인
    st.subheader("시험지를 제출하시겠습니까?")
    st.markdown("모든 답안을 제출하고 채점을 진행합니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("시험지 제출하기", use_container_width=True, key="final_submit"):
            # 모든 문제 채점 및 결과 저장
            with st.spinner("채점 중..."):
                try:
                    results = {}
                    total_score = 0
                    correct_count = 0
                    
                    # 모든 답안 채점
                    for problem_id, problem_data in st.session_state.student_answers.items():
                        student_answer = problem_data['제출답안']
                        correct_answer = problem_data['정답']
                        
                        # 단답형 또는 객관식 여부 확인
                        is_objective = correct_answer.startswith("보기")
                        
                        if is_objective:
                            # 객관식 문제는 정확히 일치해야 함
                            is_correct = (student_answer == correct_answer)
                        else:
                            # 단답형 문제는 대소문자, 공백 무시
                            normalized_student = student_answer.lower().strip() if student_answer else ""
                            normalized_correct = correct_answer.lower().strip()
                            is_correct = (normalized_student == normalized_correct)
                        
                        score = 100 if is_correct else 0
                        
                        if is_correct:
                            correct_count += 1
                        
                        results[problem_id] = {
                            'score': score,
                            'is_correct': is_correct,
                            'student_answer': student_answer,
                            'correct_answer': correct_answer
                        }
                        
                        # 학생 취약점 업데이트
                        keywords = problem_data['키워드'].split(',')
                        update_problem_stats(
                            st.session_state.student_id,
                            problem_id,
                            problem_data['키워드'],
                            is_correct
                        )
                    
                    # 총점 계산 (백분율)
                    if results:
                        total_score = (correct_count / len(results)) * 100
                    
                    # 결과 저장
                    st.session_state.exam_results = {
                        'details': results,
                        'total_score': total_score,
                        'correct_count': correct_count,
                        'total_problems': len(results)
                    }
                    
                    # 성적 분석 페이지로 이동
                    st.session_state.page = "exam_score"
                    st.rerun()
                except Exception as e:
                    st.error(f"채점 중 오류가 발생했습니다: {str(e)}")
    
    with col2:
        if st.button("취소하고 계속 풀기", use_container_width=True):
            # 다음 문제로 이동
            st.session_state.page = "problem"
            st.session_state.submitted = False
            st.session_state.exam_completed = False
            st.rerun()
    
    # 학생 답안 리스트 표시
    st.markdown("### 제출할 답안")
    
    for idx, (problem_id, problem_data) in enumerate(st.session_state.student_answers.items(), 1):
        with st.expander(f"문제 {idx}: {problem_data['과목']} ({problem_data['문제유형']})"):
            st.markdown(problem_data['문제'])
            
            if '보기정보' in problem_data and any(problem_data['보기정보'].values()):
                st.markdown("#### 보기:")
                for option_key, option_text in problem_data['보기정보'].items():
                    if option_text:
                        st.markdown(f"**{option_key}**: {option_text}")
            
            st.markdown(f"**제출한 답안**: {problem_data['제출답안']}")

def exam_score_page():
    """시험 점수 결과 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    if 'exam_submitted' not in st.session_state or not st.session_state.exam_submitted:
        st.warning("시험을 먼저 제출해야 합니다.")
        if st.button("시험 페이지로 돌아가기"):
            st.session_state.page = "exam_page"
            st.rerun()
        return
    
    st.title("시험 결과")
    
    # 학생 정보
    st.markdown(f"**학생**: {st.session_state.get('student_name', '학생')} | **학년**: {st.session_state.get('student_grade', 'N/A')} | **실력등급**: {st.session_state.get('student_level', 'N/A')}")
    
    results = st.session_state.exam_results
    
    # 총점 표시
    score = results['total_score']
    st.markdown(f"### 총점: {score:.1f}점")
    
    # 점수에 따른 메시지
    if score >= 90:
        st.success("축하합니다! 아주 우수한 성적입니다. 👏👏👏")
    elif score >= 80:
        st.success("잘했습니다! 좋은 성적입니다. 👏👏")
    elif score >= 70:
        st.info("괜찮은 성적입니다. 조금만 더 노력해보세요! 👍")
    elif score >= 60:
        st.warning("더 노력이 필요합니다. 틀린 문제를 복습해보세요.")
    else:
        st.error("많은 노력이 필요합니다. 기초부터 다시 공부해보세요.")
    
    # 결과 요약
    st.markdown(f"### 정답률: {results['correct_count']}/{results['total_problems']} 문제")
    
    # 피드백 데이터 생성
    if 'feedback_data' not in st.session_state:
        with st.spinner("문제 해설 및 피드백 생성 중..."):
            feedback_data = {}
            
            for problem_id, result in results['details'].items():
                problem_data = st.session_state.student_answers.get(problem_id, {})
                if not problem_data:
                    continue
                
                # 기본 피드백 정보 구성
                feedback = {
                    "학생답안": result['student_answer'],
                    "정답": result['correct_answer'],
                    "해설": problem_data.get('해설', ""),
                    "첨삭": ""
                }
                
                # Gemini 첨삭 생성 시도 (옵션)
                try:
                    if "GOOGLE_API_KEY" in st.secrets:
                        score, feedback_text = generate_feedback(
                            problem_data.get('문제', ''),
                            result['student_answer'],
                            result['correct_answer'],
                            problem_data.get('해설', '')
                        )
                        feedback["첨삭"] = feedback_text
                except Exception as e:
                    # Gemini 피드백 생성 실패 시 기본 피드백 사용
                    st.warning(f"첨삭 생성 중 오류 발생: {str(e)}")
                    if result['is_correct']:
                        feedback["첨삭"] = "정답입니다! 해설을 통해 개념을 확실히 이해해 보세요."
                    else:
                        feedback["첨삭"] = "오답입니다. 해설을 잘 읽고 왜 틀렸는지 파악해 보세요."
                
                feedback_data[problem_id] = feedback
            
            st.session_state.feedback_data = feedback_data
    
    # 각 문제별 결과 - 모든 문제를 펼쳐서 표시
    st.subheader("상세 결과")
    
    # 탭으로 정답/오답 구분
    tab1, tab2, tab3 = st.tabs(["모든 문제", "정답 문제", "오답 문제"])
    
    with tab1:
        # 모든 문제 결과
        for idx, (problem_id, result) in enumerate(results['details'].items(), 1):
            problem_data = st.session_state.student_answers.get(problem_id, {})
            feedback_data = st.session_state.feedback_data.get(problem_id, {})
            
            # 아이콘으로 정답/오답 표시
            if result['is_correct']:
                icon = "✅"
            else:
                icon = "❌"
            
            with st.container(border=True):
                st.markdown(f"### {icon} 문제 {idx}: {problem_data.get('과목', '과목 없음')} ({problem_data.get('문제유형', '유형 없음')})")
                st.markdown(problem_data.get('문제', '문제 없음'))
                
                if '보기정보' in problem_data and any(problem_data['보기정보'].values()):
                    # 보기 정보를 표로 표시
                    option_data = []
                    for option_key, option_text in problem_data['보기정보'].items():
                        if option_text:
                            if option_key == result['student_answer'] and option_key == result['correct_answer']:
                                # 정답이고 학생도 맞춤
                                row = [f"{option_key} 🟢", option_text]
                            elif option_key == result['student_answer']:
                                # 학생이 선택했지만 오답
                                row = [f"{option_key} 🔴", option_text]
                            elif option_key == result['correct_answer']:
                                # 정답이지만 학생이 선택하지 않음
                                row = [f"{option_key} ⭕", option_text]
                            else:
                                # 일반 보기
                                row = [option_key, option_text]
                            option_data.append(row)
                    
                    if option_data:
                        st.table(option_data)
                
                # 정답 비교 영역 (2개 열로 표시)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 제출한 답안")
                    if result['is_correct']:
                        st.success(f"**{result['student_answer']}**")
                    else:
                        st.error(f"**{result['student_answer']}**")
                with col2:
                    st.markdown("#### 정답")
                    st.success(f"**{result['correct_answer']}**")
                
                # 해설 및 첨삭 피드백
                st.markdown("#### 해설")
                st.markdown(feedback_data.get('해설', '해설 정보가 없습니다.'))
                
                if feedback_data.get('첨삭'):
                    st.markdown("#### 첨삭 피드백")
                    st.markdown(feedback_data.get('첨삭', ''))
    
    with tab2:
        # 정답 문제만 표시
        correct_problems = [(problem_id, result) for problem_id, result in results['details'].items() if result['is_correct']]
        
        if not correct_problems:
            st.info("정답인 문제가 없습니다.")
        
        for idx, (problem_id, result) in enumerate(correct_problems, 1):
            problem_data = st.session_state.student_answers.get(problem_id, {})
            feedback_data = st.session_state.feedback_data.get(problem_id, {})
            
            with st.container(border=True):
                st.markdown(f"### ✅ 문제 {idx}: {problem_data.get('과목', '과목 없음')} ({problem_data.get('문제유형', '유형 없음')})")
                st.markdown(problem_data.get('문제', '문제 없음'))
                
                # 정답 확인
                st.success(f"**정답**: {result['correct_answer']}")
                
                # 해설 및 첨삭 피드백
                st.markdown("#### 해설")
                st.markdown(feedback_data.get('해설', '해설 정보가 없습니다.'))
                
                if feedback_data.get('첨삭'):
                    st.markdown("#### 첨삭 피드백")
                    st.markdown(feedback_data.get('첨삭', ''))
    
    with tab3:
        # 오답 문제만 표시
        wrong_problems = [(problem_id, result) for problem_id, result in results['details'].items() if not result['is_correct']]
        
        if not wrong_problems:
            st.info("틀린 문제가 없습니다. 모든 문제를 맞혔습니다!")
        
        for idx, (problem_id, result) in enumerate(wrong_problems, 1):
            problem_data = st.session_state.student_answers.get(problem_id, {})
            feedback_data = st.session_state.feedback_data.get(problem_id, {})
            
            with st.container(border=True):
                st.markdown(f"### ❌ 문제 {idx}: {problem_data.get('과목', '과목 없음')} ({problem_data.get('문제유형', '유형 없음')})")
                st.markdown(problem_data.get('문제', '문제 없음'))
                
                # 정답 비교 영역
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 제출한 답안")
                    st.error(f"**{result['student_answer']}**")
                with col2:
                    st.markdown("#### 정답")
                    st.success(f"**{result['correct_answer']}**")
                
                # 해설 및 첨삭 피드백
                st.markdown("#### 해설")
                st.markdown(feedback_data.get('해설', '해설 정보가 없습니다.'))
                
                if feedback_data.get('첨삭'):
                    st.markdown("#### 첨삭 피드백")
                    st.markdown(feedback_data.get('첨삭', ''))
    
    # 성적 분석 버튼
    if st.button("나의 성적 분석 보기", use_container_width=True):
        st.session_state.page = "my_performance"
        st.rerun()
    
    # 대시보드로 돌아가기 버튼
    if st.button("대시보드로 돌아가기", use_container_width=True):
        st.session_state.page = "student_dashboard"
        st.rerun()

def check_api_connections():
    """Google Sheets와 Gemini API 연결 상태를 확인합니다."""
    connections = {
        "google_sheets": False,
        "gemini": False,
        "error_messages": []
    }
    
    # Google Sheets 연결 확인
    try:
        sheet = connect_to_sheets()
        if sheet:
            try:
                # 실제로 데이터 읽기 시도
                worksheet = sheet.worksheet("problems")
                # 새로운 래퍼 함수 사용
                records = get_worksheet_records(worksheet, limit=1)  # 첫 번째 행만 읽기
                connections["google_sheets"] = True
            except Exception as e:
                connections["error_messages"].append(f"Google Sheets 접근 오류: {str(e)}")
        else:
            connections["error_messages"].append("Google Sheets 연결에 실패했습니다.")
    except Exception as e:
        connections["error_messages"].append(f"Google Sheets 연결 오류: {str(e)}")
    
    # Gemini API 연결 확인
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            import google.generativeai as genai
            
            try:
                # Gemini API 초기화
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                
                # 안전 설정 및 생성 설정
                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
                
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 100,
                }
                
                # 간단한 API 호출 테스트 - gemini-1.5-flash 모델 사용
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                response = model.generate_content("Hello!")
                
                # 응답이 있으면 연결 성공
                if response and hasattr(response, 'text'):
                    connections["gemini"] = True
                else:
                    connections["error_messages"].append("Gemini API 응답이 예상과 다릅니다.")
            except Exception as e:
                connections["error_messages"].append(f"Gemini API 오류: {str(e)}")
        else:
            connections["error_messages"].append("Gemini API 키가 설정되지 않았습니다.")
    except Exception as e:
        connections["error_messages"].append(f"Gemini API 연결 오류: {str(e)}")
    
    return connections

def problem_page():
    """개별 문제 풀이 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 문제 로드 (현재 문제가 없는 경우)
    if 'current_problem' not in st.session_state or st.session_state.current_problem is None:
        try:
            # 이전에 풀었던 문제 ID 기록
            previous_problems = st.session_state.get('previous_problems', set())
            
            # 학생 맞춤형 문제 추천
            sheet = connect_to_sheets()
            if sheet:
                try:
                    worksheet = sheet.worksheet("problems")
                    all_problems = worksheet.get_all_records()
                    if all_problems:
                        # 학생 수준에 맞는 문제 필터링
                        student_grade = st.session_state.student_grade
                        available_problems = [p for p in all_problems if p["학년"] == student_grade]
                        
                        if available_problems:
                            # 이전에 안 풀었던 문제 중에서 추천
                            available_problems = [p for p in available_problems if p["문제ID"] not in previous_problems]
                            
                            if not available_problems:
                                # 모든 문제를 다 풀었다면 다시 처음부터
                                available_problems = [p for p in all_problems if p["학년"] == student_grade]
                                previous_problems.clear()
                            
                            # 학생 취약점을 고려한 문제 추천
                            problem = get_problem_for_student(
                                st.session_state.student_id,
                                available_problems
                            )
                            
                            if problem:
                                st.session_state.current_problem = problem
                                st.session_state.previous_problems.add(problem["문제ID"])
                except Exception as e:
                    st.error(f"문제 추천 중 오류 발생: {str(e)}")
                    # 오류 발생 시 랜덤 문제 선택
                    problem = get_random_problem()
                    st.session_state.current_problem = problem
        except Exception as e:
            st.error(f"문제 로드 중 오류 발생: {str(e)}")
            # 오류 발생 시 랜덤 문제 선택
            problem = get_random_problem()
            st.session_state.current_problem = problem
    
    # 문제가 성공적으로 로드되었는지 확인
    if 'current_problem' not in st.session_state or st.session_state.current_problem is None:
        st.error("문제를 불러오는데 실패했습니다.")
        if st.button("대시보드로 돌아가기", key="error_to_dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    problem = st.session_state.current_problem
    
    # 문제 표시
    st.title("문제 풀기")
    
    # 진행 상태 표시
    col1, col2 = st.columns(2)
    with col1:
        if 'problem_count' in st.session_state and 'max_problems' in st.session_state:
            st.info(f"문제 {st.session_state.problem_count}/{st.session_state.max_problems}")
    
    with col2:
        # 남은 시간 표시 (있는 경우)
        if 'start_time' in st.session_state and 'time_limit' in st.session_state:
            elapsed_time = time.time() - st.session_state.start_time
            remaining_time = max(0, st.session_state.time_limit - elapsed_time)
            
            # 시간 표시
            mins, secs = divmod(int(remaining_time), 60)
            time_str = f"{mins:02d}:{secs:02d}"
            st.info(f"남은 시간: {time_str}")
            
            # 시간 제한 확인
            if remaining_time <= 0:
                st.warning("시간이 초과되었습니다. 결과 페이지로 이동합니다.")
                st.session_state.page = "exam_result"
                st.rerun()
    
    # 문제 정보 표시
    subject = problem.get("과목", "")
    grade = problem.get("학년", "")
    difficulty = problem.get("난이도", "")
    
    st.markdown(f"**과목**: {subject} | **학년**: {grade} | **난이도**: {difficulty}")
    
    # 문제 내용
    st.subheader(problem.get("문제내용", "문제 내용을 불러올 수 없습니다."))
    
    # 보기가 있는지 확인
    has_options = False
    options = []
    
    for i in range(1, 6):
        option_key = f"보기{i}"
        if option_key in problem and problem[option_key]:
            has_options = True
            options.append((option_key, problem[option_key]))
    
    # 객관식 또는 주관식 문제 처리
    with st.form(key='problem_form'):
        if has_options:
            # 객관식 문제
            st.session_state.is_multiple_choice = True
            selected_option = st.radio(
                "정답을 선택하세요:",
                options=options,
                format_func=lambda x: f"{x[0]}: {x[1]}"
            )
            student_answer = selected_option[0] if selected_option else None
        else:
            # 주관식 문제
            st.session_state.is_multiple_choice = False
            student_answer = st.text_input("답을 입력하세요:")
        
        submit_button = st.form_submit_button("제출")
    
    # 제출 처리
    if submit_button and student_answer:
        st.session_state.student_answer = student_answer
        st.session_state.submitted = True
        
        # 정답 확인
        correct_answer = problem.get("정답", "")
        
        # 정답 처리
        if st.session_state.is_multiple_choice:
            # 객관식 문제는 정확히 일치해야 함
            is_correct = (student_answer == correct_answer)
        else:
            # 주관식 문제는 대소문자 무시, 공백 제거 후 비교
            normalized_student = student_answer.lower().strip()
            normalized_correct = correct_answer.lower().strip()
            is_correct = (normalized_student == normalized_correct)
        
        # 점수 계산
        score = 100 if is_correct else 0
        
        # GPT 피드백 생성
        try:
            feedback_score, feedback_text = generate_feedback(
                problem.get("문제내용", ""),
                student_answer,
                correct_answer,
                problem.get("해설", "")
            )
            
            # 피드백 저장
            st.session_state.feedback = feedback_text
            st.session_state.score = score
            
            # 학생 답안 저장
            save_student_answer(
                st.session_state.student_id,
                st.session_state.student_name,
                problem["문제ID"],
                student_answer,
                score,
                feedback_text
            )
            
            # 학생 키워드 취약점 업데이트
            keywords = problem.get("키워드", "")
            update_problem_stats(
                st.session_state.student_id,
                problem["문제ID"],
                keywords,
                is_correct
            )
            
            # 결과 페이지로 이동
            st.session_state.show_result = True
            st.session_state.page = "result"
            st.rerun()
        except Exception as e:
            st.error(f"피드백 생성 중 오류가 발생했습니다: {str(e)}")
    
    # 대시보드로 돌아가기 버튼
    if st.button("← 대시보드", key="back_btn"):
        st.session_state.page = "student_dashboard"
        st.rerun()

def main():
    """메인 함수"""
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
        problem_page()
    elif st.session_state.page == "exam_page":
        exam_page()
    elif st.session_state.page == "my_performance":
        my_performance_page()
    elif st.session_state.page == "exam_result":
        exam_result_page()
    elif st.session_state.page == "exam_score":
        exam_score_page()
    else:
        intro_page()

if __name__ == "__main__":
    main() 