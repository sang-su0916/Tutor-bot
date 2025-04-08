import streamlit as st
import os
import json
import time
import random
from datetime import datetime
import uuid

try:
    import gspread
    from google.oauth2.service_account import Credentials
    gspread_imported = True
except ImportError:
    gspread_imported = False
    st.error("gspread 패키지가 설치되지 않았습니다. 'pip install gspread' 명령으로 설치해주세요.")

# Google API 접근 범위 설정
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def connect_to_sheets():
    """구글 스프레드시트에 연결합니다."""
    if not gspread_imported:
        error_msg = "구글 시트 연결에 필요한 패키지가 설치되지 않았습니다. 'pip install gspread google-auth' 명령으로 설치해주세요."
        st.error(error_msg)
        print(error_msg)
        return None
    
    try:
        print("구글 스프레드시트 연결 시도 중...")
        
        # .streamlit/secrets.toml 파일 존재 확인
        if not hasattr(st, 'secrets') or not st.secrets:
            error_msg = "secrets.toml 파일이 없거나 접근할 수 없습니다. .streamlit 폴더에 secrets.toml 파일을 생성해주세요."
            st.error(error_msg)
            print(error_msg)
            return None
        
        # .streamlit/secrets.toml 파일에서 인증 정보 확인
        if "gcp_service_account" not in st.secrets:
            error_msg = "구글 서비스 계정 정보가 누락되었습니다. .streamlit/secrets.toml 파일에 gcp_service_account를 설정해주세요."
            st.error(error_msg)
            print(error_msg)
            return None
            
        if "spreadsheet_id" not in st.secrets:
            error_msg = "스프레드시트 ID가 누락되었습니다. .streamlit/secrets.toml 파일에 spreadsheet_id를 설정해주세요."
            st.error(error_msg)
            print(error_msg)
            return None
        
        # 서비스 계정 정보 확인
        service_account_info = st.secrets["gcp_service_account"]
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
        missing_fields = [field for field in required_fields if field not in service_account_info]
        
        if missing_fields:
            missing_fields_str = ", ".join(missing_fields)
            error_msg = f"서비스 계정 정보에 필수 필드가 누락되었습니다: {missing_fields_str}"
            st.error(error_msg)
            print(error_msg)
            return None
        
        # 개행 문자 확인 - 가장 일반적인 오류 중 하나
        if "private_key" in service_account_info:
            if "\\n" not in service_account_info["private_key"] and "\n" not in service_account_info["private_key"]:
                warning_msg = "private_key에 개행 문자가 없습니다. \\n 또는 실제 개행이 포함되어 있는지 확인하세요."
                st.warning(warning_msg)
                print(warning_msg)
            
        try:
            print("서비스 계정 인증 시도 중...")
            # API 인증
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES
            )
            gc = gspread.authorize(credentials)
            print("서비스 계정 인증 성공")
            
            # 스프레드시트 열기
            try:
                print(f"스프레드시트 열기 시도. ID: {st.secrets['spreadsheet_id']}")
                sheet = gc.open_by_key(st.secrets["spreadsheet_id"])
                print(f"스프레드시트 '{sheet.title}' 열기 성공!")
            except gspread.exceptions.APIError as e:
                error_message = str(e)
                if "404" in error_message:
                    error_msg = f"스프레드시트를 찾을 수 없습니다. ID를 확인해주세요: {st.secrets['spreadsheet_id']}"
                    st.error(error_msg)
                    print(error_msg)
                    print(f"세부 오류: {error_message}")
                    return None
                elif "403" in error_message:
                    client_email = service_account_info.get("client_email", "알 수 없음")
                    error_msg = f"스프레드시트 접근 권한이 없습니다. 서비스 계정({client_email})에 편집 권한을 부여해주세요."
                    st.error(error_msg)
                    print(error_msg)
                    print(f"세부 오류: {error_message}")
                    return None
                else:
                    error_msg = f"스프레드시트 열기 오류: {error_message}"
                    st.error(error_msg)
                    print(error_msg)
                    return None
            
            # 필수 워크시트 확인 및 생성
            try:
                required_worksheets = ["problems", "student_answers", "student_weaknesses", "students"]
                existing_worksheets = [ws.title for ws in sheet.worksheets()]
                print(f"기존 워크시트: {existing_worksheets}")
                
                for ws_name in required_worksheets:
                    if ws_name not in existing_worksheets:
                        # 워크시트가 없으면 생성
                        try:
                            print(f"워크시트 생성 시도: {ws_name}")
                            new_ws = sheet.add_worksheet(title=ws_name, rows=1000, cols=20)
                            
                            # 워크시트별 기본 헤더 설정
                            headers = []
                            if ws_name == "problems":
                                headers = ["문제ID", "과목", "학년", "문제유형", "난이도", "키워드", "문제내용", "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "해설"]
                            elif ws_name == "student_answers":
                                headers = ["학생ID", "학생이름", "학년", "문제ID", "과목", "문제유형", "난이도", "제출답안", "정답여부", "제출일시"]
                            elif ws_name == "student_weaknesses":
                                headers = ["학생ID", "키워드", "시도횟수", "정답횟수", "정답률", "최근시도일"]
                            elif ws_name == "students":
                                headers = ["학생ID", "이름", "학년", "실력등급", "등록일"]
                            
                            if headers:
                                new_ws.append_row(headers)
                                print(f"워크시트 '{ws_name}' 생성 및 헤더 추가 완료")
                        except Exception as ws_error:
                            warning_msg = f"워크시트 '{ws_name}' 생성 중 오류: {str(ws_error)}"
                            st.warning(warning_msg)
                            print(warning_msg)
                
                # 연결 성공 로그
                success_msg = f"구글 스프레드시트 '{sheet.title}'에 성공적으로 연결되었습니다."
                print(success_msg)
                return sheet
            except Exception as ws_error:
                error_msg = f"워크시트 관리 중 오류 발생: {str(ws_error)}"
                st.error(error_msg)
                print(error_msg)
                return None
        except Exception as auth_error:
            error_msg = f"인증 과정에서 오류 발생: {str(auth_error)}"
            st.error(error_msg)
            print(error_msg)
            return None
    except Exception as e:
        error_msg = f"구글 스프레드시트 연결 오류: {str(e)}"
        st.error(error_msg)
        print(error_msg)
        return None

def get_worksheet_records(sheet, worksheet_name):
    """특정 워크시트의 모든 레코드를 가져옵니다."""
    if not sheet:
        print("시트 객체가 없어 워크시트 레코드를 가져올 수 없습니다.")
        return []
    
    try:
        worksheet = sheet.worksheet(worksheet_name)
        # 전체 레코드 가져오기
        records = worksheet.get_all_records()
        print(f"워크시트 '{worksheet_name}'에서 {len(records)}개의 레코드를 가져왔습니다.")
        return records
    except Exception as e:
        print(f"워크시트 '{worksheet_name}' 데이터 불러오기 실패: {str(e)}")
        st.warning(f"워크시트 '{worksheet_name}' 데이터 불러오기 실패: {str(e)}")
        return []

def get_random_problem(student_id=None, student_grade=None, problem_type=None):
    """
    구글 스프레드시트에서 학생 수준에 맞는 문제를 가져옵니다.
    student_id가 제공되면 학생의 약점에 기반한 문제를 선택합니다.
    연결 실패 시 더미 문제를 제공합니다.
    """
    # 스프레드시트 연결
    sheet = connect_to_sheets()
    if not sheet:
        print(f"구글 시트 연결 실패. 학년 '{student_grade}'에 맞는 더미 문제를 생성합니다.")
        return get_dummy_problem(student_grade)
    
    try:
        # 문제 워크시트에서 모든 문제 가져오기
        problems_ws = sheet.worksheet("problems")
        all_problems = problems_ws.get_all_records()
        
        if not all_problems:
            print("문제 워크시트가 비어 있습니다. 더미 문제를 생성합니다.")
            return get_dummy_problem(student_grade)
        
        # 학생 약점 분석 (student_id가 제공된 경우)
        student_weaknesses = {}
        if student_id:
            try:
                weaknesses_ws = sheet.worksheet("student_weaknesses")
                weakness_records = weaknesses_ws.get_all_records()
                
                # 해당 학생의 약점 항목 찾기
                for record in weakness_records:
                    if record.get("학생ID") == student_id:
                        keyword = record.get("키워드")
                        # 정답률이 70% 미만인 키워드를 약점으로 간주
                        if record.get("정답률", 100) < 70 and keyword:
                            student_weaknesses[keyword] = record.get("정답률", 0)
            except Exception as e:
                print(f"학생 약점 분석 오류: {str(e)}")
        
        # 필터링된 문제 목록
        valid_problems = []
        
        # 문제 데이터 정제 및 필터링
        for p in all_problems:
            # 필수 필드 확인
            if not all(key in p and p[key] for key in ["문제ID", "문제내용", "정답"]):
                continue
            
            # 학년 필터링 (선택적)
            if student_grade and "학년" in p and p["학년"]:
                if p["학년"] != student_grade:
                    continue
            
            # 문제 유형 필터링 (선택적)
            if problem_type and "문제유형" in p and p["문제유형"]:
                if p["문제유형"] != problem_type:
                    continue
            
            # 객관식 문제인 경우 보기 정보 처리
            if "문제유형" in p and p["문제유형"] == "객관식":
                # 보기 정보 초기화
                p["보기정보"] = {}
                
                # 보기1~5 필드 확인 및 구조화
                for i in range(1, 6):
                    option_key = f"보기{i}"
                    if option_key in p and p[option_key] and p[option_key].strip():
                        p["보기정보"][option_key] = p[option_key].strip()
                
                # 보기가 최소 2개 이상 있어야 함
                if len(p["보기정보"]) < 2:
                    continue
            
            # 모든 조건을 통과한 문제 추가
            valid_problems.append(p)
        
        # 유효한 문제가 없으면 더미 문제 반환
        if not valid_problems:
            print(f"학년 '{student_grade}'에 맞는 유효한 문제가 없습니다. 더미 문제를 생성합니다.")
            return get_dummy_problem(student_grade)
        
        # 약점 기반 문제 선택 (약점이 있는 경우)
        weakness_based_problems = []
        if student_weaknesses:
            for p in valid_problems:
                # 키워드 확인
                keywords = []
                if "키워드" in p and p["키워드"]:
                    if isinstance(p["키워드"], str):
                        keywords = [k.strip() for k in p["키워드"].split(',')]
                
                # 약점 관련 키워드가 있는 문제 찾기
                for keyword in keywords:
                    if keyword in student_weaknesses:
                        weakness_based_problems.append(p)
                        break
        
        # 약점 기반 문제가 있으면 그 중에서 무작위 선택 (80% 확률)
        if weakness_based_problems and random.random() < 0.8:
            selected_problem = random.choice(weakness_based_problems)
            print(f"약점 기반 문제 선택: 문제ID {selected_problem.get('문제ID')}")
            return selected_problem
        
        # 그 외의 경우는 모든 유효한 문제 중에서 무작위 선택
        selected_problem = random.choice(valid_problems)
        print(f"무작위 문제 선택: 문제ID {selected_problem.get('문제ID')}")
        return selected_problem
        
    except Exception as e:
        print(f"문제 불러오기 오류: {str(e)}")
        return get_dummy_problem(student_grade)

def get_dummy_problem(student_grade=None):
    """기본 더미 문제를 반환합니다. 실제 문제를 불러올 수 없을 때 사용합니다."""
    # 학년에 맞는 문제 선택
    if not student_grade:
        student_grade = "중1"  # 기본값
    
    # 학년에 따른 문제 설정
    if "중1" in student_grade:
        question = "Pick the correct word to complete the sentence: A student ___ to school."
        options = {
            "보기1": "go",
            "보기2": "goes",
            "보기3": "going",
            "보기4": "went"
        }
        answer = "보기2"
        explanation = "'A student'는 3인칭 단수이므로 동사에 -s를 붙여 'goes'가 됩니다."
    elif "중2" in student_grade:
        question = "Choose the correct past tense: Yesterday, I ___ to the store."
        options = {
            "보기1": "go",
            "보기2": "goes",
            "보기3": "going",
            "보기4": "went"
        }
        answer = "보기4"
        explanation = "과거 시제를 나타내는 'Yesterday'가 있으므로 go의 과거형인 'went'를 사용합니다."
    elif "중3" in student_grade:
        question = "Select the correct passive form: The book ___ by the student."
        options = {
            "보기1": "read",
            "보기2": "reads",
            "보기3": "is read",
            "보기4": "reading"
        }
        answer = "보기3"
        explanation = "수동태는 'be동사 + 과거분사'의 형태입니다. 따라서 'is read'가 정답입니다."
    elif "고1" in student_grade:
        question = "Choose the correct comparative: This book is ___ than that one."
        options = {
            "보기1": "interesting",
            "보기2": "more interesting",
            "보기3": "most interesting",
            "보기4": "interestingly"
        }
        answer = "보기2"
        explanation = "두 개를 비교할 때는 비교급을 사용합니다. 긴 형용사는 'more + 원급'으로 비교급을 만듭니다."
    elif "고2" in student_grade:
        question = "Select the correct present perfect: She ___ in Korea for five years."
        options = {
            "보기1": "live",
            "보기2": "lives",
            "보기3": "living",
            "보기4": "has lived"
        }
        answer = "보기4"
        explanation = "현재완료는 'have/has + 과거분사'의 형태로, 과거부터 현재까지 지속되는 상황을 나타냅니다."
    else:  # 고3 또는 기타
        question = "Choose the correct conditional: If I ___ rich, I would buy a new car."
        options = {
            "보기1": "am",
            "보기2": "was",
            "보기3": "were",
            "보기4": "being"
        }
        answer = "보기3"
        explanation = "가정법 과거에서는 if절에 'were'를 사용합니다. 'If I were...'는 현재 사실과 반대되는 상황을 가정할 때 씁니다."
    
    # 더미 문제 데이터 구성
    dummy_problem = {
        "문제ID": f"dummy-{int(time.time())}",
        "과목": "영어",
        "학년": student_grade,
        "문제유형": "객관식",
        "난이도": "중",
        "문제내용": question,
        "정답": answer,
        "해설": explanation,
        "보기정보": options
    }
    
    # 보기 항목 추가
    for key, value in options.items():
        dummy_problem[key] = value
    
    return dummy_problem

def save_student_answer(student_id, student_name, student_grade, problem_id, problem_data, 
                      student_answer, is_correct):
    """학생의 문제 풀이 결과를 스프레드시트에 저장합니다."""
    if not student_id or not problem_id:
        return False
    
    # 스프레드시트 연결
    sheet = connect_to_sheets()
    if not sheet:
        return False
    
    try:
        # 학생 답안 워크시트
        answers_ws = sheet.worksheet("student_answers")
        
        # 답안 데이터 준비
        answer_data = [
            student_id,
            student_name,
            student_grade,
            problem_id,
            problem_data.get("과목", ""),
            problem_data.get("문제유형", ""),
            problem_data.get("난이도", ""),
            student_answer,
            "O" if is_correct else "X",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        # 답안 저장
        answers_ws.append_row(answer_data)
        
        # 키워드 기반 약점 분석 업데이트
        try:
            # 키워드 추출
            keywords = []
            if "키워드" in problem_data and problem_data["키워드"]:
                if isinstance(problem_data["키워드"], str):
                    keywords = [k.strip() for k in problem_data["키워드"].split(',') if k.strip()]
            
            if keywords:
                update_problem_stats(student_id, problem_id, keywords, is_correct)
        except Exception as e:
            print(f"약점 분석 업데이트 중 오류: {str(e)}")
        
        return True
    except Exception as e:
        print(f"학생 답안 저장 중 오류: {str(e)}")
        return False

def update_problem_stats(student_id, problem_id, keywords, is_correct):
    """학생의 문제 풀이 결과를 바탕으로 약점 분석 데이터를 업데이트합니다."""
    if not student_id or not keywords:
        return False
    
    # 스프레드시트 연결
    sheet = connect_to_sheets()
    if not sheet:
        return False
    
    try:
        # 약점 분석 워크시트
        weaknesses_ws = sheet.worksheet("student_weaknesses")
        weakness_records = weaknesses_ws.get_all_records()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 각 키워드에 대한 통계 업데이트
        for keyword in keywords:
            # 이미 존재하는 레코드 검색
            found = False
            for i, record in enumerate(weakness_records):
                if record.get("학생ID") == student_id and record.get("키워드") == keyword:
                    # 기존 레코드 업데이트
                    row_idx = i + 2  # 헤더가 1행, 인덱스는 0부터 시작하므로 +2
                    
                    # 현재 값 가져오기
                    attempts = int(record.get("시도횟수", 0)) + 1
                    correct_attempts = int(record.get("정답횟수", 0)) + (1 if is_correct else 0)
                    accuracy = round((correct_attempts / attempts) * 100, 1)
                    
                    # 레코드 업데이트
                    weaknesses_ws.update_cell(row_idx, 3, attempts)  # 시도횟수
                    weaknesses_ws.update_cell(row_idx, 4, correct_attempts)  # 정답횟수
                    weaknesses_ws.update_cell(row_idx, 5, accuracy)  # 정답률
                    weaknesses_ws.update_cell(row_idx, 6, now)  # 최근시도일
                    
                    found = True
                    break
            
            if not found:
                # 새 레코드 추가
                new_record = [
                    student_id,
                    keyword,
                    1,  # 시도횟수
                    1 if is_correct else 0,  # 정답횟수
                    100 if is_correct else 0,  # 정답률
                    now  # 최근시도일
                ]
                weaknesses_ws.append_row(new_record)
        
        return True
    except Exception as e:
        print(f"문제 통계 업데이트 중 오류: {str(e)}")
        return False

def save_exam_result(student_id, student_name, student_grade, results):
    """시험 결과를 학년별로 정리하여 저장합니다."""
    if not student_id or not results:
        return False
    
    # 스프레드시트 연결
    sheet = connect_to_sheets()
    if not sheet:
        return False
    
    try:
        # 학년별 워크시트 이름 생성 (예: 시험결과_중1)
        worksheet_name = f"시험결과_{student_grade}"
        
        # 워크시트 확인 및 생성
        try:
            existing_worksheets = [ws.title for ws in sheet.worksheets()]
            if worksheet_name not in existing_worksheets:
                # 워크시트가 없으면 생성
                sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                # 헤더 추가
                headers = ["학생ID", "학생이름", "학년", "시험일시", 
                          "총문제수", "정답수", "정답률", "약점분석"]
                sheet.worksheet(worksheet_name).append_row(headers)
        except Exception as e:
            print(f"워크시트 생성 중 오류: {str(e)}")
            # 오류 발생 시 기본 워크시트 사용
            worksheet_name = "student_answers"
        
        # 시험 결과 저장
        result_ws = sheet.worksheet(worksheet_name)
        
        # 약점 분석 - 오답 문제의 주요 키워드 추출
        weaknesses = []
        for problem_id, detail in results.get('details', {}).items():
            if not detail.get('is_correct', True):  # 오답인 경우
                problem_data = detail.get('problem_data', {})
                keywords = []
                if "키워드" in problem_data and problem_data["키워드"]:
                    if isinstance(problem_data["키워드"], str):
                        keywords = [k.strip() for k in problem_data["키워드"].split(',') if k.strip()]
                    weaknesses.extend(keywords)
        
        # 가장 빈도가 높은 약점 키워드 추출 (최대 5개)
        weakness_counts = {}
        for keyword in weaknesses:
            weakness_counts[keyword] = weakness_counts.get(keyword, 0) + 1
        
        # 빈도순으로 정렬하여 상위 5개 추출
        top_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        weakness_analysis = ", ".join([f"{k}({v})" for k, v in top_weaknesses])
        
        # 결과 데이터 준비
        exam_data = [
            student_id,
            student_name,
            student_grade,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results.get('total_problems', 0),
            results.get('correct_count', 0),
            round(results.get('total_score', 0), 1),
            weakness_analysis
        ]
        
        # 결과 저장
        result_ws.append_row(exam_data)
        
        return True
    except Exception as e:
        print(f"시험 결과 저장 중 오류: {str(e)}")
        return False