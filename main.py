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

def load_exam_problems():
    """학생 학년에 맞는 시험 문제 20개를 로드합니다."""
    if 'exam_problems' not in st.session_state or not st.session_state.exam_problems:
        st.session_state.exam_problems = []
        
        try:
            # 학생 취약점 기반 문제 추천
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
                                # 중복되지 않는 문제 20개 선택
                                selected_problems = []
                                max_attempts = 50  # 최대 시도 횟수
                                
                                for _ in range(min(20, len(available_problems))):
                                    for _ in range(max_attempts):
                                        # 취약점 기반 문제 추천
                                        problem = get_problem_for_student(
                                            st.session_state.student_id,
                                            available_problems
                                        )
                                        
                                        # 이미 선택된 문제인지 확인
                                        if problem and problem not in selected_problems:
                                            selected_problems.append(problem)
                                            # 사용한 문제는 available_problems에서 제거
                                            if problem in available_problems:
                                                available_problems.remove(problem)
                                            break
                                
                                st.session_state.exam_problems = selected_problems
                    except Exception as e:
                        st.error(f"문제 로드 중 오류 발생: {str(e)}")
        except Exception as e:
            st.error(f"문제 로드 중 오류 발생: {str(e)}")
        
        # 문제가 부족하면 더미 문제로 채우기
        while len(st.session_state.exam_problems) < 20:
            dummy_problem = get_random_problem()
            # 학년 수정 - 학생 학년에 맞추기
            if hasattr(st.session_state, 'student_grade'):
                dummy_problem["학년"] = st.session_state.student_grade
            st.session_state.exam_problems.append(dummy_problem)
    
    return st.session_state.exam_problems

def exam_page():
    """시험 페이지 - 20문제를 한 페이지에 모두 표시"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    # 시간 제한 설정
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    
    if 'time_limit' not in st.session_state:
        st.session_state.time_limit = 50 * 60  # 50분(초 단위)
    
    if 'student_answers' not in st.session_state:
        st.session_state.student_answers = {}
    
    # 현재 시간으로 경과 시간 계산
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, st.session_state.time_limit - elapsed_time)
    
    # 남은 시간 표시
    mins, secs = divmod(int(remaining_time), 60)
    time_str = f"{mins:02d}:{secs:02d}"
    
    # 제한 시간이 끝났는지 확인
    if remaining_time <= 0:
        st.success("시험 시간이 종료되었습니다! 시험지를 제출해주세요.")
        
        if st.button("시험지 제출하기", use_container_width=True, key="final_submit_timeout"):
            # 시험 결과 처리
            st.session_state.exam_completed = True
            st.session_state.page = "exam_result"
            st.rerun()
        
        if st.button("대시보드로 돌아가기", key="back_to_dashboard_timeout"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        
        return
    
    st.title(f"시험지")
    
    # 진행 상황 표시
    st.markdown(f"**남은 시간**: {time_str}")
    st.markdown(f"**학생**: {st.session_state.get('student_name', '학생')} | **학년**: {st.session_state.get('student_grade', 'N/A')} | **실력등급**: {st.session_state.get('student_level', 'N/A')}")
    
    # 대시보드로 돌아가기 버튼
    if st.button("← 대시보드", key="back_to_dashboard_btn"):
        st.session_state.page = "student_dashboard"
        st.rerun()
    
    # 문제 로드
    problems = load_exam_problems()
    
    if not problems:
        st.error("문제를 불러오는데 실패했습니다.")
        return
    
    # 문제 폼 - 모든 문제를 한 페이지에 표시
    with st.form(key="exam_form"):
        for idx, problem in enumerate(problems, 1):
            st.markdown(f"### 문제 {idx}/20")
            st.markdown(f"**과목**: {problem['과목']} | **학년**: {problem['학년']} | **유형**: {problem['문제유형']} | **난이도**: {problem['난이도']}")
            
            # 문제 내용
            st.markdown(problem.get("문제내용", "문제 내용을 불러올 수 없습니다."))
            
            # 보기가 있는지 확인
            has_options = False
            options = []
            for i in range(1, 6):
                option_key = f"보기{i}"
                if option_key in problem and problem[option_key] and problem[option_key].strip():
                    has_options = True
                    options.append((option_key, problem[option_key].strip()))
            
            # 문제 ID를 키로 사용
            problem_id = problem['문제ID']
            answer_key = f"answer_{problem_id}"
            
            if has_options:
                # 객관식 문제
                selected_option = st.radio(
                    "정답 선택:",
                    options=options,
                    format_func=lambda x: f"{x[0]}: {x[1]}",
                    key=f"radio_{problem_id}",
                    index=None
                )
                
                if selected_option:
                    st.session_state[answer_key] = selected_option[0]
            else:
                # 주관식 문제
                text_answer = st.text_input(
                    "답 입력:",
                    key=f"text_{problem_id}",
                    value=st.session_state.get(f"text_{problem_id}", "")
                )
                if text_answer.strip():
                    st.session_state[answer_key] = text_answer.strip()
            
            # 문제 구분선
            if idx < len(problems):
                st.markdown("---")
        
        # 제출 버튼
        submit_button = st.form_submit_button("시험지 제출하기", use_container_width=True)
    
    # 제출 처리
    if submit_button:
        # 모든 답변 저장
        for problem in problems:
            problem_id = problem['문제ID']
            answer_key = f"answer_{problem_id}"
            
            if answer_key in st.session_state and st.session_state[answer_key]:
                st.session_state.student_answers[problem_id] = {
                    '문제': problem.get("문제내용", ""),
                    '학생답안': st.session_state[answer_key],
                    '정답': problem.get("정답", ""),
                    '보기정보': {f"보기{i}": problem.get(f"보기{i}", "") for i in range(1, 6) if f"보기{i}" in problem},
                    '키워드': problem.get("키워드", ""),
                    '문제유형': problem.get("문제유형", ""),
                    '과목': problem.get("과목", ""),
                    '학년': problem.get("학년", "")
                }
        
        # 시험 결과 페이지로 이동
        st.session_state.exam_completed = True
        st.session_state.page = "exam_result"
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
                        student_answer = problem_data['학생답안']
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
            
            st.markdown(f"**제출한 답안**: {problem_data['학생답안']}")

def exam_score_page():
    """시험 점수 결과 페이지"""
    if not hasattr(st.session_state, 'student_id') or st.session_state.student_id is None:
        st.error("로그인 정보가 없습니다.")
        if st.button("로그인 페이지로 돌아가기"):
            st.session_state.page = "intro"
            st.rerun()
        return
    
    if 'exam_results' not in st.session_state:
        st.error("시험 결과를 찾을 수 없습니다.")
        if st.button("대시보드로 돌아가기"):
            st.session_state.page = "student_dashboard"
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
    
    # 각 문제별 결과
    st.subheader("상세 결과")
    
    for idx, (problem_id, result) in enumerate(results['details'].items(), 1):
        problem_data = st.session_state.student_answers.get(problem_id, {})
        
        if result['is_correct']:
            icon = "✅"
        else:
            icon = "❌"
        
        with st.expander(f"{icon} 문제 {idx}: {problem_data.get('과목', '과목 없음')} ({problem_data.get('문제유형', '유형 없음')})"):
            st.markdown(problem_data.get('문제', '문제 없음'))
            
            if '보기정보' in problem_data and any(problem_data['보기정보'].values()):
                st.markdown("#### 보기:")
                for option_key, option_text in problem_data['보기정보'].items():
                    if option_text:
                        st.markdown(f"**{option_key}**: {option_text}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 제출한 답안")
                st.markdown(f"**{result['student_answer']}**")
            with col2:
                st.markdown("#### 정답")
                st.markdown(f"**{result['correct_answer']}**")
    
    # 성적 분석 버튼
    if st.button("나의 성적 분석 보기", use_container_width=True):
        st.session_state.page = "my_performance"
        st.rerun()
    
    # 대시보드로 돌아가기 버튼
    if st.button("대시보드로 돌아가기", use_container_width=True):
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