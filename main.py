import streamlit as st
import uuid
import os
import sys
import time

# 현재 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 모듈 임포트
try:
    from sheets_utils import connect_to_sheets, get_random_problem, save_student_answer
    from gpt_feedback import generate_feedback
    import admin  # 관리자 모듈 추가
    from student_analytics import get_problem_for_student, update_problem_stats, show_student_performance_dashboard  # 취약점 분석 모듈 추가
except ImportError as e:
    st.error(f"모듈을 불러올 수 없습니다: {e}")
    
    # 대체 함수 정의
    def get_random_problem():
        return {
            "문제ID": "dummy-1",
            "과목": "영어",
            "학년": "중1",
            "문제유형": "객관식",
            "난이도": "하",
            "문제내용": "Pick the correct word to complete: The cat ___ to school.",
            "보기1": "went",
            "보기2": "gone",
            "보기3": "going",
            "보기4": "goes",
            "보기5": "go",
            "정답": "보기4",
            "키워드": "동사 시제",
            "해설": "현재 시제를 사용해야 합니다. 주어가 'The cat'으로 3인칭 단수이므로 'goes'가 정답입니다."
        }
    
    def save_student_answer(student_id, student_name, problem_id, submitted_answer, score, feedback):
        return True
    
    def generate_feedback(question, student_answer, correct_answer, explanation):
        if student_answer == correct_answer:
            return 100, "정답입니다! 해설을 읽고 개념을 더 깊이 이해해보세요."
        else:
            return 0, "틀렸습니다. 해설을 잘 읽고 다시 한 번 풀어보세요."
    
    def get_problem_for_student(student_id, available_problems):
        return get_random_problem()
    
    def update_problem_stats(student_id, problem_id, keywords, is_correct):
        return True
    
    def show_student_performance_dashboard(student_id, student_name, grade, level):
        st.info("학생 성적 대시보드를 표시할 수 없습니다.")

# 페이지 설정
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
        if st.button("📝 문제 풀기 (20문제 / 50분)", use_container_width=True):
            # 문제 풀기 세션 초기화
            st.session_state.problem_count = 0
            st.session_state.max_problems = 20
            st.session_state.start_time = time.time()
            st.session_state.time_limit = 50 * 60  # 50분(초 단위)
            st.session_state.page = "problem"
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

def problem_page():
    """문제 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 시간 제한 및 문제 수 체크
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    
    if 'problem_count' not in st.session_state:
        st.session_state.problem_count = 0
    
    if 'max_problems' not in st.session_state:
        st.session_state.max_problems = 20
    
    if 'time_limit' not in st.session_state:
        st.session_state.time_limit = 50 * 60  # 50분(초 단위)
    
    # 현재 시간으로 경과 시간 계산
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, st.session_state.time_limit - elapsed_time)
    
    # 남은 시간 표시
    mins, secs = divmod(int(remaining_time), 60)
    time_str = f"{mins:02d}:{secs:02d}"
    
    # 제한 시간이 끝났는지 또는 최대 문제 수에 도달했는지 확인
    if remaining_time <= 0 or st.session_state.problem_count >= st.session_state.max_problems:
        st.success("시험이 종료되었습니다!")
        st.markdown(f"**풀이한 문제 수**: {st.session_state.problem_count}/{st.session_state.max_problems}")
        
        if st.button("결과 확인", use_container_width=True):
            st.session_state.page = "my_performance"
            st.rerun()
        
        if st.button("대시보드로 돌아가기", use_container_width=True):
            st.session_state.page = "student_dashboard"
            st.rerun()
        
        return
    
    st.title(f"문제 풀기")
    
    # 진행 상황 표시
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**문제**: {st.session_state.problem_count + 1}/{st.session_state.max_problems}")
    with col2:
        st.markdown(f"**남은 시간**: {time_str}")
    
    st.markdown(f"**학생**: {st.session_state.get('student_name', '학생')} | **학년**: {st.session_state.get('student_grade', 'N/A')} | **실력등급**: {st.session_state.get('student_level', 'N/A')}")
    
    # 대시보드로 돌아가기 버튼
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← 대시보드", key="back_to_dashboard_btn"):
            st.session_state.page = "student_dashboard"
            st.rerun()
    
    # 처음 페이지가 로드될 때 또는 다음 문제 버튼을 눌렀을 때 문제를 가져옴
    if not hasattr(st.session_state, 'current_problem') or st.session_state.current_problem is None or st.session_state.submitted:
        with st.spinner("문제를 불러오는 중..."):
            try:
                # 이전 문제 정보 저장
                previous_problem = st.session_state.current_problem if hasattr(st.session_state, 'current_problem') else None
                
                # 기본 문제 가져오기
                try:
                    # 학생 취약점 기반 문제 추천
                    problem = None
                    if hasattr(st.session_state, 'student_id'):
                        # 문제 목록 가져오기
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
                                        # 학생 취약점 기반 문제 추천
                                        problem = get_problem_for_student(
                                            st.session_state.student_id,
                                            available_problems
                                        )
                            except:
                                pass
                    
                    # 추천 실패시 랜덤 문제 가져오기
                    if not problem:
                        problem = get_random_problem()
                except:
                    problem = get_random_problem()
                
                # 문제가 이전 문제와 같은지 확인
                if previous_problem and problem and problem["문제ID"] == previous_problem["문제ID"]:
                    problem = get_random_problem()
                
                if problem:
                    # 세션 상태 정리 (이전 문제 관련 상태 제거)
                    for key in list(st.session_state.keys()):
                        if key.startswith("radio_") or key.startswith("answer_text_"):
                            del st.session_state[key]
                    
                    st.session_state.current_problem = problem
                    st.session_state.submitted = False
                    st.session_state.feedback = None
                    st.session_state.score = None
                    st.session_state.show_result = False
                    
                    # 보기가 있는지 확인하여 문제 유형 결정
                    has_options = False
                    for i in range(1, 6):
                        option_key = f"보기{i}"
                        if option_key in problem and problem[option_key] and problem[option_key].strip():
                            has_options = True
                            break
                    
                    st.session_state.is_multiple_choice = has_options
                else:
                    st.error("문제를 불러오는데 실패했습니다.")
                    return
            except Exception as e:
                st.error("문제를 불러오는데 실패했습니다.")
                return
    
    problem = st.session_state.current_problem
    
    # 문제 정보 표시
    st.markdown(f"**과목**: {problem['과목']} | **학년**: {problem['학년']} | **유형**: {problem['문제유형']} | **난이도**: {problem['난이도']}")
    
    # 문제 내용
    st.subheader("문제")
    st.markdown(problem.get("문제내용", "문제 내용을 불러올 수 없습니다."))
    
    # 문제 유형 확인 (객관식 또는 단답형)
    is_multiple_choice = st.session_state.is_multiple_choice
    
    # 학생 답변 변수 초기화
    student_answer = None
    
    # 고유한 폼 ID 생성
    form_id = f"answer_form_{problem['문제ID']}"
    
    # 폼 생성
    with st.form(key=form_id):
        if is_multiple_choice:
            # 객관식 문제: 보기를 라디오 버튼으로 표시
            st.write("정답을 선택하세요:")
            
            # 중복 없는 보기 목록 생성
            options = []
            seen_options = set()  # 중복 보기 추적용
            
            for i in range(1, 6):
                option_key = f"보기{i}"
                if option_key in problem and problem[option_key] and problem[option_key].strip():
                    option_text = problem[option_key].strip()
                    # 중복된 보기 내용 확인
                    if option_text not in seen_options:
                        options.append((option_key, option_text))
                        seen_options.add(option_text)
            
            # 보기 표시
            if options:
                radio_key = f"radio_{problem['문제ID']}"
                selected_option = st.radio(
                    label="",
                    options=options,
                    format_func=lambda x: f"{x[0]}: {x[1]}",
                    key=radio_key
                )
                
                # 선택된 옵션 (보기1, 보기2 등) 저장
                if selected_option:
                    student_answer = selected_option[0]
            else:
                st.warning("이 문제에 보기가 없습니다. 단답형으로 풀어주세요.")
                # 보기가 없으면 단답형으로 전환
                st.session_state.is_multiple_choice = False
                is_multiple_choice = False
        
        # 단답형 입력 (객관식이 아니거나 보기가 없는 경우)
        if not is_multiple_choice:
            st.write("답을 입력하세요:")
            # 텍스트 입력 필드 표시
            text_key = f"answer_text_{problem['문제ID']}"
            text_input = st.text_input(
                label="",
                value=st.session_state.get(text_key, ""),
                placeholder="답을 입력하세요", 
                key=text_key
            )
            student_answer = text_input.strip()
        
        # 제출 버튼
        submit_button = st.form_submit_button("정답 제출하기")
    
    # 제출 처리
    if submit_button:
        if not student_answer:
            st.error("답을 입력하거나 선택해주세요.")
        else:
            with st.spinner("채점 중..."):
                try:
                    # GPT를 사용하여 채점 및 피드백 생성
                    score, feedback = generate_feedback(
                        problem.get("문제내용", ""),
                        student_answer,
                        problem.get("정답", ""),
                        problem.get("해설", "")
                    )
                    
                    # 세션 상태에 결과 저장
                    if "submitted" not in st.session_state:
                        st.session_state.submitted = False
                    st.session_state.submitted = True
                    
                    if "feedback" not in st.session_state:
                        st.session_state.feedback = None
                    st.session_state.feedback = feedback
                    
                    if "score" not in st.session_state:
                        st.session_state.score = None
                    st.session_state.score = score
                    
                    if "show_result" not in st.session_state:
                        st.session_state.show_result = False
                    st.session_state.show_result = True
                    
                    if "student_answer" not in st.session_state:
                        st.session_state.student_answer = None
                    st.session_state.student_answer = student_answer
                    
                    # Google Sheets에 저장
                    save_student_answer(
                        st.session_state.student_id,
                        st.session_state.student_name,
                        problem.get("문제ID", ""),
                        student_answer,
                        score,
                        feedback
                    )
                    
                    # 학생 취약점 업데이트
                    is_correct = (score == 100)
                    update_problem_stats(
                        st.session_state.student_id,
                        problem.get("문제ID", ""),
                        problem.get("키워드", ""),
                        is_correct
                    )
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"채점 중 오류가 발생했습니다.")

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
    
    # 진행 상황 표시
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

def main():
    """메인 함수"""
    # CSS로 디버그 정보 숨기기
    hide_streamlit_style = """
        <style>
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            .stDeployButton {display:none !important;}
            div[data-testid="stToolbar"] {visibility: hidden !important;}
            div[data-testid="stDecoration"] {visibility: hidden !important;}
            div[data-testid="stStatusWidget"] {visibility: hidden !important;}
            div[data-testid="stHeader"] {visibility: hidden !important;}
            div.block-container {padding-top: 0rem !important;}
            div.block-container {padding-bottom: 0rem !important;}
            div[data-testid="stAppViewContainer"] > section:first-child {padding-top: 1rem !important;}
            div[data-testid="stVerticalBlock"] {gap: 1rem !important;}
            div[data-testid="stConnectionStatus"] {visibility: hidden !important;}
            div[data-testid="stSpinner"] {visibility: hidden !important;}
            div[data-testid="stDebugElement"] {visibility: hidden !important;}
            div[data-testid="stMarkdownContainer"] > div > p {margin-bottom: 0.5rem !important;}
            div.st-emotion-cache-16txtl3 {padding-top: 0rem !important;}
            div.st-emotion-cache-16txtl3 {padding-bottom: 0rem !important;}
            div.st-emotion-cache-ue6h4q {padding-top: 0rem !important;}
            div.stAlert {display: none !important;}
            div[data-baseweb="notification"] {display: none !important;}
            div[data-testid="stNotificationContainer"] {display: none !important;}
            div[data-testid="stAppViewBlockContainer"] > section[data-testid="stCaptionContainer"] {display: none !important;}
            iframe[name="stNotificationFrame"] {display: none !important;}
            div[data-testid="stForm"] {border: none !important; padding: 0 !important;}
            div.stRadio > div {flex-direction: column !important;}
            div.stRadio label {padding: 10px !important; border: 1px solid #f0f0f0 !important; border-radius: 5px !important; margin: 5px 0 !important;}
            div.stRadio label:hover {background-color: #f8f8f8 !important;}
            button[kind="primaryFormSubmit"] {width: 100% !important; padding: 10px !important; font-weight: bold !important;}
            div.stButton button {font-weight: bold !important; padding: 8px 16px !important;}
            div.stTextInput input {padding: 10px !important; font-size: 16px !important;}
            h3 {margin-top: 1rem !important; margin-bottom: 0.5rem !important;}
            div.element-container {margin-bottom: 0.5rem !important;}
            div.stForm [data-testid="stVerticalBlock"] > div:has(div.stButton) {margin-top: 1rem !important;}
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
        if st.session_state.show_result:
            result_page()
        else:
            problem_page()
    elif st.session_state.page == "my_performance":
        my_performance_page()
    else:
        intro_page()

if __name__ == "__main__":
    main() 