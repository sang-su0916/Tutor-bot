import streamlit as st
import pandas as pd
import hashlib
import uuid
from sheets_utils import connect_to_sheets

# 학년 정보
GRADE_OPTIONS = [
    "중학교 1학년", "중학교 2학년", "중학교 3학년",
    "고등학교 1학년", "고등학교 2학년", "고등학교 3학년"
]

# 실력 등급
LEVEL_OPTIONS = ["초급", "중급", "고급"]

def hash_password(password):
    """비밀번호를 해시하여 반환합니다."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, input_password):
    """입력된 비밀번호와 저장된 해시값을 비교합니다."""
    input_hash = hash_password(input_password)
    return stored_hash == input_hash

def create_teacher_account(username, password, name, school):
    """교사 계정을 생성합니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False, "Google Sheets 연결에 실패했습니다."
        
        # 'teachers' 워크시트 열기
        try:
            worksheet = sheet.worksheet("teachers")
        except:
            # 워크시트가 없으면 생성
            worksheet = sheet.add_worksheet("teachers", 1000, 6)
            worksheet.append_row([
                "교사ID", "사용자이름", "비밀번호(해시)", "이름", "학교", "생성일시"
            ])
        
        # 기존 사용자 확인
        existing_users = worksheet.col_values(2)[1:]  # 첫 번째 행은 헤더이므로 제외
        if username in existing_users:
            return False, "이미 사용 중인 사용자 이름입니다."
        
        # 새 계정 추가
        import datetime
        teacher_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        worksheet.append_row([
            teacher_id,
            username,
            hashed_password,
            name,
            school,
            current_time
        ])
        
        return True, "교사 계정이 성공적으로 생성되었습니다."
        
    except Exception as e:
        return False, f"계정 생성 중 오류가 발생했습니다: {str(e)}"

def get_teacher_by_username(username):
    """사용자 이름으로 교사 정보를 가져옵니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return None
        
        try:
            worksheet = sheet.worksheet("teachers")
            records = worksheet.get_all_records()
            
            for record in records:
                if record["사용자이름"] == username:
                    return record
            
            return None
            
        except Exception as e:
            return None
            
    except Exception as e:
        return None

def register_student(teacher_id, name, grade, level, notes=""):
    """학생을 등록합니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False, "Google Sheets 연결에 실패했습니다."
        
        # 'students' 워크시트 열기
        try:
            worksheet = sheet.worksheet("students")
        except:
            # 워크시트가 없으면 생성
            worksheet = sheet.add_worksheet("students", 1000, 7)
            worksheet.append_row([
                "학생ID", "이름", "학년", "실력등급", "교사ID", "메모", "등록일시"
            ])
        
        # 새 학생 추가
        import datetime
        student_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        worksheet.append_row([
            student_id,
            name,
            grade,
            level,
            teacher_id,
            notes,
            current_time
        ])
        
        return True, "학생이 성공적으로 등록되었습니다."
        
    except Exception as e:
        return False, f"학생 등록 중 오류가 발생했습니다: {str(e)}"

def get_teacher_students(teacher_id):
    """교사가 등록한 학생 목록을 가져옵니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return []
        
        try:
            worksheet = sheet.worksheet("students")
            records = worksheet.get_all_records()
            
            # 해당 교사의 학생만 필터링
            teacher_students = [record for record in records if record["교사ID"] == teacher_id]
            return teacher_students
            
        except Exception as e:
            return []
            
    except Exception as e:
        return []

def update_student(student_id, name, grade, level, notes):
    """학생 정보를 업데이트합니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False, "Google Sheets 연결에 실패했습니다."
        
        try:
            worksheet = sheet.worksheet("students")
            records = worksheet.get_all_records()
            all_students = worksheet.get_all_values()
            header = all_students[0]
            
            # 학생ID 열 인덱스 찾기
            student_id_idx = header.index("학생ID")
            
            # 해당 학생 행 찾기
            row_idx = None
            for i, row in enumerate(all_students[1:], start=2):  # 헤더 다음부터 시작, 1-indexed
                if row[student_id_idx] == student_id:
                    row_idx = i
                    break
            
            if not row_idx:
                return False, "학생을 찾을 수 없습니다."
            
            # 열 인덱스 찾기
            name_idx = header.index("이름")
            grade_idx = header.index("학년")
            level_idx = header.index("실력등급")
            notes_idx = header.index("메모")
            
            # 값 업데이트
            worksheet.update_cell(row_idx, name_idx + 1, name)  # 0-indexed에서 1-indexed로 변환
            worksheet.update_cell(row_idx, grade_idx + 1, grade)
            worksheet.update_cell(row_idx, level_idx + 1, level)
            worksheet.update_cell(row_idx, notes_idx + 1, notes)
            
            return True, "학생 정보가 성공적으로 업데이트되었습니다."
            
        except Exception as e:
            return False, f"학생 정보 업데이트 중 오류가 발생했습니다: {str(e)}"
            
    except Exception as e:
        return False, f"학생 정보 업데이트 중 오류가 발생했습니다: {str(e)}"

def delete_student(student_id):
    """학생을 삭제합니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False, "Google Sheets 연결에 실패했습니다."
        
        try:
            worksheet = sheet.worksheet("students")
            records = worksheet.get_all_records()
            all_students = worksheet.get_all_values()
            header = all_students[0]
            
            # 학생ID 열 인덱스 찾기
            student_id_idx = header.index("학생ID")
            
            # 해당 학생 행 찾기
            row_idx = None
            for i, row in enumerate(all_students[1:], start=2):  # 헤더 다음부터 시작, 1-indexed
                if row[student_id_idx] == student_id:
                    row_idx = i
                    break
            
            if not row_idx:
                return False, "학생을 찾을 수 없습니다."
            
            # 행 삭제
            worksheet.delete_rows(row_idx)
            
            return True, "학생이 성공적으로 삭제되었습니다."
            
        except Exception as e:
            return False, f"학생 삭제 중 오류가 발생했습니다: {str(e)}"
            
    except Exception as e:
        return False, f"학생 삭제 중 오류가 발생했습니다: {str(e)}"

def admin_signup_page():
    """교사 회원가입 페이지"""
    st.title("교사 회원가입")
    
    with st.form("signup_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        name = st.text_input("이름")
        school = st.text_input("학교")
        
        submit_button = st.form_submit_button("회원가입")
        
        if submit_button:
            if not username or not password or not name or not school:
                st.error("모든 필드를 입력해주세요.")
            elif password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                success, message = create_teacher_account(username, password, name, school)
                if success:
                    st.success(message)
                    st.session_state.admin_action = "login"
                    st.rerun()
                else:
                    st.error(message)

def admin_login_page():
    """교사 로그인 페이지"""
    st.title("교사 로그인")
    
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("로그인")
        with col2:
            if st.form_submit_button("회원가입"):
                st.session_state.admin_action = "signup"
                st.rerun()
        
        if submit_button:
            if not username or not password:
                st.error("아이디와 비밀번호를 입력해주세요.")
            else:
                try:
                    teacher = get_teacher_by_username(username)
                    if teacher and verify_password(teacher["비밀번호(해시)"], password):
                        # 세션 상태 설정
                        if "admin_logged_in" not in st.session_state:
                            st.session_state.admin_logged_in = False
                        st.session_state.admin_logged_in = True
                        
                        if "admin_id" not in st.session_state:
                            st.session_state.admin_id = ""
                        st.session_state.admin_id = teacher["교사ID"]
                        
                        if "admin_name" not in st.session_state:
                            st.session_state.admin_name = ""
                        st.session_state.admin_name = teacher["이름"]
                        
                        if "admin_school" not in st.session_state:
                            st.session_state.admin_school = ""
                        st.session_state.admin_school = teacher["학교"]
                        
                        if "admin_username" not in st.session_state:
                            st.session_state.admin_username = ""
                        st.session_state.admin_username = teacher["사용자이름"]
                        
                        if "admin_action" not in st.session_state:
                            st.session_state.admin_action = "login"
                        st.session_state.admin_action = "dashboard"
                        
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
                except Exception as e:
                    st.error(f"로그인 처리 중 오류가 발생했습니다: {str(e)}")
                    st.info("아직 계정이 없다면 회원가입을 진행해주세요.")

def admin_student_form(teacher_id, edit_mode=False, student_data=None):
    """학생 등록/수정 폼"""
    if edit_mode:
        st.subheader("학생 정보 수정")
    else:
        st.subheader("새 학생 등록")
    
    with st.form("student_form"):
        name = st.text_input("이름", value=student_data["이름"] if edit_mode else "")
        grade = st.selectbox("학년", options=GRADE_OPTIONS, index=GRADE_OPTIONS.index(student_data["학년"]) if edit_mode else 0)
        level = st.selectbox("실력등급", options=LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(student_data["실력등급"]) if edit_mode else 0)
        notes = st.text_area("메모", value=student_data["메모"] if edit_mode else "")
        
        submit_label = "수정하기" if edit_mode else "등록하기"
        submit_button = st.form_submit_button(submit_label)
        
        if submit_button:
            if not name:
                st.error("이름을 입력해주세요.")
            else:
                if edit_mode:
                    success, message = update_student(student_data["학생ID"], name, grade, level, notes)
                else:
                    success, message = register_student(teacher_id, name, grade, level, notes)
                
                if success:
                    st.success(message)
                    st.session_state.admin_action = "dashboard"
                    st.rerun()
                else:
                    st.error(message)

def student_performance_stats(teacher_id):
    """학생들의 성적 통계를 표시합니다."""
    try:
        sheet = connect_to_sheets()
        if not sheet:
            st.error("학생 성적 데이터를 불러올 수 없습니다.")
            return
        
        # 교사의 학생 목록 가져오기
        students = get_teacher_students(teacher_id)
        student_ids = [student["학생ID"] for student in students]
        
        if not student_ids:
            st.info("등록된 학생이 없습니다.")
            return
        
        try:
            # 학생 답안 데이터 가져오기
            worksheet = sheet.worksheet("student_answers")
            all_answers = worksheet.get_all_records()
            
            # 해당 학생들의 답안만 필터링
            student_answers = []
            for answer in all_answers:
                if answer["학생ID"] in student_ids:
                    student_answers.append(answer)
            
            if not student_answers:
                st.info("제출된 답안이 없습니다.")
                return
            
            # 학생별 성적 데이터 계산
            student_scores = {}
            for student in students:
                student_scores[student["학생ID"]] = {
                    "이름": student["이름"],
                    "학년": student["학년"],
                    "실력등급": student["실력등급"],
                    "정답수": 0,
                    "오답수": 0,
                    "총점": 0,
                    "문제수": 0
                }
            
            for answer in student_answers:
                student_id = answer["학생ID"]
                if student_id in student_scores:
                    score = answer["점수"]
                    student_scores[student_id]["문제수"] += 1
                    student_scores[student_id]["총점"] += score
                    if score == 100:
                        student_scores[student_id]["정답수"] += 1
                    else:
                        student_scores[student_id]["오답수"] += 1
            
            # 결과를 DataFrame으로 변환
            data = []
            for student_id, stats in student_scores.items():
                if stats["문제수"] > 0:
                    avg_score = stats["총점"] / stats["문제수"]
                    correct_rate = (stats["정답수"] / stats["문제수"]) * 100 if stats["문제수"] > 0 else 0
                    data.append({
                        "이름": stats["이름"],
                        "학년": stats["학년"],
                        "실력등급": stats["실력등급"],
                        "문제수": stats["문제수"],
                        "정답률(%)": round(correct_rate, 1),
                        "평균점수": round(avg_score, 1)
                    })
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("학생들의 답안 정보가 없습니다.")
            
        except Exception as e:
            st.error(f"성적 데이터를 처리하는 중 오류가 발생했습니다: {str(e)}")
            
    except Exception as e:
        st.error(f"성적 통계를 불러오는 중 오류가 발생했습니다: {str(e)}")

def admin_dashboard(teacher_id, teacher_name, school):
    """교사 대시보드"""
    st.title(f"{teacher_name} 선생님의 관리 대시보드")
    st.markdown(f"**학교**: {school}")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["학생 관리", "성적 통계"])
    
    # 학생 관리 탭
    with tab1:
        # 학생 등록 버튼
        if st.button("새 학생 등록", key="new_student_btn", use_container_width=True):
            st.session_state.admin_action = "register_student"
            st.rerun()
        
        # 학생 목록 가져오기
        students = get_teacher_students(teacher_id)
        
        if not students:
            st.info("등록된 학생이 없습니다. '새 학생 등록' 버튼을 클릭하여 학생을 추가해주세요.")
        else:
            st.subheader("등록된 학생 목록")
            
            # 실력등급별 필터링
            level_filter = st.multiselect("실력등급 필터", options=LEVEL_OPTIONS, default=LEVEL_OPTIONS)
            
            # 학년별 필터링
            grade_filter = st.multiselect("학년 필터", options=GRADE_OPTIONS, default=GRADE_OPTIONS)
            
            # 필터링된 학생 목록
            filtered_students = [s for s in students if s["실력등급"] in level_filter and s["학년"] in grade_filter]
            
            # 테이블로 학생 목록 표시
            if filtered_students:
                # 테이블 데이터 준비
                student_data = []
                for student in filtered_students:
                    student_data.append({
                        "이름": student["이름"],
                        "학년": student["학년"],
                        "실력등급": student["실력등급"],
                        "메모": student["메모"],
                        "등록일시": student["등록일시"]
                    })
                
                df = pd.DataFrame(student_data)
                st.dataframe(df, use_container_width=True)
                
                # 학생 선택 및 관리
                st.subheader("학생 관리")
                selected_student = st.selectbox("학생 선택", options=[s["이름"] for s in filtered_students])
                
                if selected_student:
                    # 선택된 학생 정보
                    student_info = next((s for s in filtered_students if s["이름"] == selected_student), None)
                    
                    if student_info:
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("정보 수정", key="edit_student_btn", use_container_width=True):
                                st.session_state.admin_action = "edit_student"
                                st.session_state.edit_student_data = student_info
                                st.rerun()
                        
                        with col2:
                            if st.button("학생 삭제", key="delete_student_btn", use_container_width=True):
                                st.session_state.admin_action = "confirm_delete"
                                st.session_state.delete_student_data = student_info
                                st.rerun()
            else:
                st.info("필터 조건에 맞는 학생이 없습니다.")
    
    # 성적 통계 탭
    with tab2:
        student_performance_stats(teacher_id)

def confirm_delete_student(student_data):
    """학생 삭제 확인"""
    st.title("학생 삭제 확인")
    
    st.warning(f"'{student_data['이름']}' 학생을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", key="cancel_delete_btn", use_container_width=True):
            st.session_state.admin_action = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("삭제", key="confirm_delete_btn", use_container_width=True):
            success, message = delete_student(student_data["학생ID"])
            if success:
                st.success(message)
                st.session_state.admin_action = "dashboard"
                st.rerun()
            else:
                st.error(message)

def admin_logout():
    """관리자 로그아웃"""
    # 세션 상태 초기화
    for key in list(st.session_state.keys()):
        if key.startswith("admin_"):
            del st.session_state[key]
    
    # 시작 페이지로 초기화
    st.session_state.admin_action = "login"
    st.rerun()

def admin_main():
    """관리자 메인 페이지"""
    # CSS 스타일
    st.markdown("""
    <style>
        .stButton>button {
            font-weight: bold;
            padding: 8px 16px;
        }
        div.block-container {padding-top: 2rem;}
        .stForm>div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if "admin_action" not in st.session_state:
        st.session_state.admin_action = "login"
    
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    
    # 사이드바 로그아웃 버튼
    if st.session_state.get("admin_logged_in"):
        with st.sidebar:
            st.write(f"안녕하세요, {st.session_state.admin_name} 선생님!")
            if st.button("로그아웃", key="logout_btn"):
                admin_logout()
    
    # 현재 액션에 따라 페이지 표시
    if st.session_state.admin_action == "signup":
        admin_signup_page()
    elif st.session_state.admin_logged_in:
        if st.session_state.admin_action == "register_student":
            admin_student_form(st.session_state.admin_id)
        elif st.session_state.admin_action == "edit_student":
            admin_student_form(st.session_state.admin_id, edit_mode=True, student_data=st.session_state.edit_student_data)
        elif st.session_state.admin_action == "confirm_delete":
            confirm_delete_student(st.session_state.delete_student_data)
        else:  # dashboard
            admin_dashboard(st.session_state.admin_id, st.session_state.admin_name, st.session_state.admin_school)
    else:
        admin_login_page()

if __name__ == "__main__":
    admin_main() 