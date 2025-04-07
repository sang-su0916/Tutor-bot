import streamlit as st
import uuid
from sheets_utils import connect_to_sheets, get_random_problem, save_student_answer
from gpt_feedback import generate_feedback

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

# 세션 상태 초기화
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "current_problem" not in st.session_state:
    st.session_state.current_problem = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "score" not in st.session_state:
    st.session_state.score = None
if "show_result" not in st.session_state:
    st.session_state.show_result = False

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
    
    with st.form("answer_form"):
        # 보기를 라디오 버튼으로 표시
        selected_option = st.radio(
            "정답을 선택하세요:",
            options=options,
            format_func=lambda x: f"{x[0]}: {x[1]}",
            key=f"answer_radio_{problem['문제ID']}"  # 문제별 고유 키 사용
        )
        
        # 제출 버튼
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.form_submit_button("정답 제출하기")
        
        if submit_button:
            with st.spinner("채점 중..."):
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
    
    # 버튼
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("다음 문제"):
            st.session_state.current_problem = None
            st.rerun()
    
    with col3:
        show_logout()

def show_logout():
    """로그아웃 버튼"""
    if st.button("로그아웃"):
        # 세션 상태 초기화
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def main():
    """메인 함수"""
    # CSS로 디버그 정보 숨기기
    hide_streamlit_style = """
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display:none;}
            div[data-testid="stToolbar"] {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden;}
            div[data-testid="stStatusWidget"] {visibility: hidden;}
            div[data-testid="stHeader"] {visibility: hidden;}
            div.block-container {padding-top: 0rem;}
            div.block-container {padding-bottom: 0rem;}
            div[data-testid="stAppViewContainer"] > section:first-child {padding-top: 1rem;}
            div[data-testid="stVerticalBlock"] {gap: 1rem;}
            div[data-testid="stConnectionStatus"] {visibility: hidden;}
            div[data-testid="stSpinner"] {visibility: hidden;}
            div[data-testid="stDebugElement"] {visibility: hidden;}
            div[data-testid="stMarkdownContainer"] > div > p {margin-bottom: 0.5rem;}
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