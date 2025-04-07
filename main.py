import streamlit as st
import uuid
import os
import sys

# 현재 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 모듈 임포트
try:
    from sheets_utils import connect_to_sheets, get_random_problem, save_student_answer
    from gpt_feedback import generate_feedback
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
    st.session_state.current_problem = None
    st.session_state.submitted = False
    st.session_state.feedback = None
    st.session_state.score = None
    st.session_state.show_result = False
    st.session_state.initialized = True

def login_page():
    """학생 로그인 페이지"""
    st.title("GPT 학습 피드백 시스템")
    st.markdown("#### 우리 학원 전용 AI 튜터")
    
    with st.form("login_form"):
        student_name = st.text_input("이름을 입력하세요")
        submit_button = st.form_submit_button("로그인")
        
        if submit_button and student_name:
            st.session_state.student_id = str(uuid.uuid4())
            st.session_state.student_name = student_name
            st.rerun()

def problem_page():
    """문제 페이지"""
    st.title(f"안녕하세요, {st.session_state.student_name}님!")
    
    # 처음 페이지가 로드될 때 또는 다음 문제 버튼을 눌렀을 때 문제를 가져옴
    if not st.session_state.current_problem or st.session_state.submitted:
        with st.spinner("문제를 불러오는 중..."):
            try:
                # 이전 문제 정보 저장
                previous_problem = st.session_state.current_problem if hasattr(st.session_state, 'current_problem') else None
                
                # 새 문제 가져오기
                problem = get_random_problem()
                
                # 문제가 이전 문제와 같은지 확인
                if previous_problem and problem and problem["문제ID"] == previous_problem["문제ID"]:
                    problem = get_random_problem()
                
                if problem:
                    st.session_state.current_problem = problem
                    st.session_state.submitted = False
                    st.session_state.feedback = None
                    st.session_state.score = None
                    st.session_state.show_result = False
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
    
    # 보기 준비
    options = []
    for i in range(1, 6):
        option_key = f"보기{i}"
        if option_key in problem and problem[option_key]:
            options.append((option_key, problem[option_key]))
    
    with st.form(key="answer_form"):
        st.write("정답을 선택하세요:")
        # 보기를 라디오 버튼으로 표시
        selected_option = st.radio(
            label="",
            options=options,
            format_func=lambda x: f"{x[0]}: {x[1]}",
            key=f"answer_radio_{problem['문제ID']}"  # 문제별 고유 키 사용
        )
        
        # 제출 버튼
        submit_button = st.form_submit_button("정답 제출하기")
        
        if submit_button:
            try:
                # 학생이 선택한 답변 (보기1, 보기2 등)
                student_answer = selected_option[0]
                
                # GPT를 사용하여 채점 및 피드백 생성
                score, feedback = generate_feedback(
                    problem.get("문제내용", ""),
                    student_answer,
                    problem.get("정답", ""),
                    problem.get("해설", "")
                )
                
                # 세션 상태에 결과 저장
                st.session_state.submitted = True
                st.session_state.feedback = feedback
                st.session_state.score = score
                st.session_state.show_result = True
                
                # Google Sheets에 저장
                save_student_answer(
                    st.session_state.student_id,
                    st.session_state.student_name,
                    problem.get("문제ID", ""),
                    student_answer,
                    score,
                    feedback
                )
                
                st.rerun()
            except Exception as e:
                st.error("채점 중 오류가 발생했습니다.")

def result_page():
    """결과 페이지"""
    st.title("채점 결과")
    
    problem = st.session_state.current_problem
    
    # 문제 정보 표시
    st.markdown(f"**과목**: {problem['과목']} | **학년**: {problem['학년']} | **유형**: {problem['문제유형']} | **난이도**: {problem['난이도']}")
    
    # 문제 내용
    st.subheader("문제")
    st.markdown(problem.get("문제내용", "문제 내용을 불러올 수 없습니다."))
    
    # 정답과 점수
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**정답**: {problem.get('정답', '')}")
    
    with col2:
        score = st.session_state.score
        if score is None:
            st.error("**점수**: 채점 중 오류가 발생했습니다.")
        elif score == 100:
            st.success("**점수**: 100점")
        else:
            st.error(f"**점수**: {score}점")
    
    # 해설과 피드백
    st.subheader("문제 해설")
    st.markdown(problem.get("해설", ""))
    
    st.subheader("AI 튜터 피드백")
    feedback = st.session_state.feedback
    if feedback:
        st.markdown(feedback)
    else:
        st.warning("피드백을 생성하는 중 오류가 발생했습니다.")
    
    # 키워드 표시
    if "키워드" in problem and problem["키워드"]:
        st.markdown(f"**학습 키워드**: {problem['키워드']}")
    
    # 버튼들
    st.write("")  # 공백 추가
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("다음 문제", key="next_problem_btn", use_container_width=True):
            # 다음 문제를 위한 상태 초기화
            st.session_state.current_problem = None
            st.session_state.submitted = False
            st.session_state.feedback = None
            st.session_state.score = None
            st.session_state.show_result = False
            st.rerun()
    
    with col2:
        if st.button("로그아웃", key="logout_btn", use_container_width=True):
            # 세션 상태 초기화
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # 초기 상태 설정
            st.session_state.initialized = True
            st.session_state.student_id = None
            st.session_state.student_name = None
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
            button[kind="primaryFormSubmit"] {width: 100% !important;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # 로그인 상태에 따라 페이지 표시
    if not st.session_state.student_id:
        login_page()
    elif st.session_state.show_result:
        result_page()
    else:
        problem_page()

if __name__ == "__main__":
    main() 