import streamlit as st
import os
import json
import time
import random
from datetime import datetime
import uuid
import traceback  # 오류 추적을 위한 모듈 추가

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
    """Google Sheets에 연결합니다."""
    try:
        # gspread가 설치되지 않았으면 더미 시트 반환
        if not gspread_imported:
            st.warning("gspread 모듈이 설치되지 않아 더미 시트를 사용합니다.")
            print("gspread 모듈이 설치되지 않아 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # secrets.toml에서 설정 확인
        if not hasattr(st, 'secrets') or not st.secrets:
            st.warning("secrets.toml 파일이 없습니다. 더미 시트를 사용합니다.")
            print("secrets.toml 파일이 없습니다. 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # 더미 데이터 사용 설정 확인
        if "use_dummy_data" in st.secrets and st.secrets["use_dummy_data"]:
            st.info("use_dummy_data 설정이 활성화되어 있어 더미 시트를 사용합니다.")
            print("use_dummy_data 설정이 활성화되어 있어 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # 스프레드시트 ID 확인
        spreadsheet_id = ""
        if "spreadsheet_id" in st.secrets:
            spreadsheet_id = st.secrets["spreadsheet_id"]
            print(f"secrets.toml에서 spreadsheet_id를 찾았습니다: {spreadsheet_id}")
        elif "GSHEETS_ID" in st.secrets:
            spreadsheet_id = st.secrets["GSHEETS_ID"]
            print(f"secrets.toml에서 GSHEETS_ID를 찾았습니다: {spreadsheet_id}")
        
        if not spreadsheet_id:
            st.warning("스프레드시트 ID가 설정되지 않았습니다. 더미 시트를 사용합니다.")
            print("스프레드시트 ID가 설정되지 않았습니다. 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # 서비스 계정 정보 확인 (직접 로드)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = None
        
        # 서비스 계정 파일 확인
        service_account_path = "service_account.json"
        
        if "GOOGLE_SERVICE_ACCOUNT_PATH" in st.secrets:
            service_account_path = st.secrets["GOOGLE_SERVICE_ACCOUNT_PATH"]
            print(f"서비스 계정 파일 경로: {service_account_path}")
            
        # 파일 존재 확인
        if os.path.exists(service_account_path):
            print(f"서비스 계정 파일을 찾았습니다: {service_account_path}")
            try:
                credentials = Credentials.from_service_account_file(
                    service_account_path, scopes=scope
                )
                print("서비스 계정 파일로부터 credentials 객체를 생성했습니다.")
            except Exception as e:
                print(f"서비스 계정 파일 사용 오류: {str(e)}")
                print(f"상세 오류: {traceback.format_exc()}")
        # 서비스 계정 정보가 secrets.toml에 있는 경우
        elif "gcp_service_account" in st.secrets:
            print("서비스 계정 정보를 secrets.toml에서 찾았습니다.")
            try:
                credentials = Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"], scope
                )
                print("secrets.toml의 서비스 계정 정보로 credentials 객체를 생성했습니다.")
            except Exception as e:
                print(f"secrets.toml의 서비스 계정 정보 사용 오류: {str(e)}")
                print(f"상세 오류: {traceback.format_exc()}")
        else:
            st.warning("서비스 계정 정보가 없습니다. 더미 시트를 사용합니다.")
            print("서비스 계정 정보가 없습니다. 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # credentials 생성 성공 확인
        if credentials is None:
            st.warning("인증 정보 생성에 실패했습니다. 더미 시트를 사용합니다.")
            print("인증 정보 생성에 실패했습니다. 더미 시트를 사용합니다.")
            return create_dummy_sheet()
            
        # gspread 클라이언트 초기화 및 스프레드시트 열기
        try:
            gc = gspread.authorize(credentials)
            print("Google Sheets API 인증 성공")
            
            # 스프레드시트 열기
            try:
                print(f"스프레드시트 ID로 시트를 열고 있습니다: {spreadsheet_id}")
                spreadsheet = gc.open_by_key(spreadsheet_id)
                print(f"스프레드시트 '{spreadsheet.title}'에 연결되었습니다.")
                st.success(f"스프레드시트 '{spreadsheet.title}'에 연결되었습니다.")
                
                # 필요한 워크시트 확인
                worksheets = {ws.title: ws for ws in spreadsheet.worksheets()}
                print(f"현재 워크시트 목록: {', '.join(worksheets.keys())}")
                required_sheets = ["problems", "student_answers", "student_weaknesses", "students"]
                
                # 필요한 워크시트가 없으면 생성
                for sheet_name in required_sheets:
                    if sheet_name not in worksheets:
                        print(f"'{sheet_name}' 워크시트가 없어 새로 생성합니다.")
                        spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                        print(f"'{sheet_name}' 워크시트를 생성했습니다.")
                
                # 성공 표시
                st.session_state.sheets_connection_status = "success"
                st.session_state.sheets_connection_success = True
                st.session_state.using_dummy_sheet = False
                
                return spreadsheet
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(f"스프레드시트를 찾을 수 없습니다: {spreadsheet_id}")
                print(f"스프레드시트를 찾을 수 없습니다: {spreadsheet_id}")
                print("서비스 계정 이메일이 스프레드시트에 공유되어 있는지 확인하세요.")
            except Exception as e:
                st.error(f"스프레드시트 열기 오류: {str(e)}")
                print(f"스프레드시트 열기 오류: {str(e)}")
                print(f"상세 오류: {traceback.format_exc()}")
        except Exception as e:
            st.error(f"Google Sheets API 인증 오류: {str(e)}")
            print(f"Google Sheets API 인증 오류: {str(e)}")
            print(f"상세 오류: {traceback.format_exc()}")
            
        # 여기까지 왔다면 오류가 발생한 것이므로 더미 시트 반환
        st.session_state.sheets_connection_status = "error"
        st.session_state.sheets_connection_success = False
        st.session_state.using_dummy_sheet = True
        return create_dummy_sheet()
            
    except Exception as e:
        st.error(f"Google Sheets 연결 오류: {str(e)}")
        print(f"Google Sheets 연결 오류: {str(e)}")
        print(f"상세 오류: {traceback.format_exc()}")
        st.session_state.sheets_connection_status = "error"
        st.session_state.sheets_connection_success = False
        st.session_state.using_dummy_sheet = True
        return create_dummy_sheet()

def create_dummy_sheet():
    """더미 시트 객체를 생성하여 반환합니다. 실제 연결이 실패해도 UI가 작동하도록 합니다."""
    # 세션 상태에 더미 시트 사용 표시
    st.session_state.using_dummy_sheet = True
    st.session_state.sheets_connection_status = "success"  # UI에는 성공으로 표시
    
    # 모의 워크시트 클래스 (기능 향상)
    class DummyWorksheet:
        def __init__(self, title):
            self.title = title
            self._data = []
            self._headers = []
            
            # 기본 헤더 설정
            if title == "problems":
                self._headers = ["문제ID", "과목", "학년", "문제유형", "난이도", "키워드", "문제내용", "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "해설"]
            elif title == "student_answers":
                self._headers = ["학생ID", "학생이름", "학년", "문제ID", "과목", "문제유형", "난이도", "제출답안", "정답여부", "제출일시"]
            elif title == "student_weaknesses":
                self._headers = ["학생ID", "키워드", "시도횟수", "정답횟수", "정답률", "최근시도일"]
            elif title == "students":
                self._headers = ["학생ID", "이름", "학년", "실력등급", "등록일"]
                # 학생 샘플 데이터 추가
                self._data = [
                    {"학생ID": "sample-001", "이름": "홍길동", "학년": "중1", "실력등급": "중", "등록일": "2023-01-01"},
                    {"학생ID": "sample-002", "이름": "김철수", "학년": "중2", "실력등급": "상", "등록일": "2023-01-02"},
                    {"학생ID": "sample-003", "이름": "이영희", "학년": "고1", "실력등급": "하", "등록일": "2023-01-03"}
                ]
            
        def get_all_records(self):
            return self._data
            
        def append_row(self, row):
            # 행 데이터를 딕셔너리로 변환
            if len(self._headers) > 0 and len(row) <= len(self._headers):
                record = {self._headers[i]: row[i] for i in range(len(row))}
                self._data.append(record)
            return True
            
        def update_cell(self, row, col, value):
            try:
                if row-2 >= 0 and row-2 < len(self._data) and col-1 >= 0 and col-1 < len(self._headers):
                    header = self._headers[col-1]
                    self._data[row-2][header] = value
            except:
                pass
            return True
    
    # 모의 스프레드시트 클래스
    class DummySheet:
        def __init__(self):
            self.title = "Tutor-bot (Dummy)"
            self._worksheets = [
                DummyWorksheet("problems"),
                DummyWorksheet("student_answers"),
                DummyWorksheet("student_weaknesses"),
                DummyWorksheet("students")
            ]
        
        def worksheets(self):
            return self._worksheets
            
        def worksheet(self, title):
            for ws in self._worksheets:
                if ws.title == title:
                    return ws
            # 없으면 생성
            new_ws = DummyWorksheet(title)
            self._worksheets.append(new_ws)
            return new_ws
            
        def add_worksheet(self, title, rows, cols):
            new_ws = DummyWorksheet(title)
            self._worksheets.append(new_ws)
            return new_ws
    
    # 성공 메시지 출력
    print("구글 스프레드시트에 연결 대신 더미 시트 객체를 사용합니다.")
    return DummySheet()

def get_worksheet_records(sheet, worksheet_name):
    """특정 워크시트의 모든 레코드를 가져옵니다."""
    if not sheet:
        print("시트 객체가 없어 더미 데이터를 반환합니다.")
        return []
    
    try:
        worksheet = sheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        print(f"워크시트 '{worksheet_name}'에서 {len(records)}개의 레코드를 가져왔습니다.")
        return records
    except Exception as e:
        print(f"워크시트 '{worksheet_name}' 데이터 불러오기 실패: {str(e)}")
        # 에러 발생 시 빈 목록 반환
        return []

def get_random_problem(student_id=None, student_grade=None, problem_type=None):
    """
    Google Sheets에서 문제를 가져오고 필요시 학생 약점 기반 필터링을 적용합니다.
    
    Parameters:
    student_id (str, optional): 학생 ID
    student_grade (str, optional): 학생 학년 (예: '중1', '고2')
    problem_type (str, optional): 문제 유형 (예: '객관식', '주관식')
    
    Returns:
    dict: 무작위로 선택된 문제
    """
    try:
        spreadsheet = connect_to_sheets()
        if spreadsheet is None:
            print("Sheets 연결 실패, 더미 문제를 반환합니다.")
            return get_dummy_problem(student_grade)
        
        # 스프레드시트 정보 확인 및 출력
        print(f"스프레드시트 제목: {spreadsheet.title}")
        worksheets = spreadsheet.worksheets()
        worksheet_names = [ws.title for ws in worksheets]
        print(f"워크시트 목록: {', '.join(worksheet_names)}")
        
        # 문제 워크시트 가져오기 시도
        problems_worksheet_name = None
        for name in worksheet_names:
            if "problem" in name.lower() or "문제" in name:
                problems_worksheet_name = name
                break
        
        if not problems_worksheet_name:
            if "problems" in worksheet_names:
                problems_worksheet_name = "problems"
            else:
                print("문제 워크시트를 찾을 수 없습니다, 더미 문제를 반환합니다.")
                return get_dummy_problem(student_grade)
        
        print(f"사용할 문제 워크시트: {problems_worksheet_name}")
        problems_sheet = spreadsheet.worksheet(problems_worksheet_name)
        
        # 헤더 확인
        headers = problems_sheet.row_values(1)
        print(f"문제 워크시트 헤더: {headers}")
        
        # 데이터 가져오기
        all_problems = problems_sheet.get_all_records()
        print(f"총 {len(all_problems)}개의 문제 데이터를 불러왔습니다.")
        
        if not all_problems:
            print("문제가 없습니다, 더미 문제를 반환합니다.")
            return get_dummy_problem(student_grade)
        
        # 첫 번째 문제 데이터 구조 확인
        first_problem = all_problems[0]
        print(f"첫 번째 문제 키: {list(first_problem.keys())}")
        
        # 필수 필드 검증 및 필터링
        valid_problems = []
        for problem in all_problems:
            # 필수 필드 검증
            required_fields = ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "정답"]
            # 모든 필드가 존재하고 값이 있는지 확인
            missing_fields = [field for field in required_fields if field not in problem or not problem[field]]
            
            if missing_fields:
                continue  # 필수 필드가 누락된 문제는 건너뜁니다
            
            # 학년 필터링
            if student_grade and problem["학년"] != student_grade:
                continue
            
            # 문제 유형 필터링
            if problem_type and problem["문제유형"] != problem_type:
                continue
            
            valid_problems.append(problem)
        
        print(f"필터링 후 유효한 문제 수: {len(valid_problems)}/{len(all_problems)}")
        
        if not valid_problems:
            print(f"유효한 문제가 없습니다. 총 {len(all_problems)}개 문제 중 필터링 후 0개 남음.")
            return get_dummy_problem(student_grade)
        
        # 학생 ID가 제공된 경우 약점 기반 필터링 시도
        if student_id:
            try:
                # 학생 약점 데이터 가져오기
                weaknesses_worksheet_name = None
                for name in worksheet_names:
                    if "weakness" in name.lower() or "약점" in name:
                        weaknesses_worksheet_name = name
                        break
                
                if weaknesses_worksheet_name:
                    print(f"학생 약점 워크시트 발견: {weaknesses_worksheet_name}")
                    weaknesses_sheet = spreadsheet.worksheet(weaknesses_worksheet_name)
                    weaknesses_data = weaknesses_sheet.get_all_records()
                    
                    # 해당 학생의 약점 찾기
                    student_weaknesses = None
                    for record in weaknesses_data:
                        if record.get("학생ID") == student_id or record.get("student_id") == student_id:
                            weakness_field = next((f for f in record if "약점" in f or "weakness" in f.lower()), None)
                            if weakness_field and record.get(weakness_field):
                                student_weaknesses = record.get(weakness_field)
                                break
                    
                    # 약점이 있으면 관련 문제 필터링
                    if student_weaknesses:
                        weakness_keywords = [kw.strip() for kw in student_weaknesses.split(',')]
                        print(f"학생 약점 키워드: {weakness_keywords}")
                        weakness_related_problems = []
                        
                        for problem in valid_problems:
                            # 문제 키워드나 내용에 약점 키워드가 포함되어 있는지 확인
                            for keyword in weakness_keywords:
                                if (keyword in problem.get("키워드", "") or 
                                    keyword in problem.get("문제내용", "")):
                                    weakness_related_problems.append(problem)
                                    break
                        
                        # 약점 관련 문제가 있으면 그 중에서 선택
                        if weakness_related_problems:
                            print(f"약점 관련 문제 수: {len(weakness_related_problems)}")
                            selected_problem = random.choice(weakness_related_problems)
                            print(f"약점 기반 문제를 선택했습니다. ID: {selected_problem.get('문제ID', 'unknown')}")
                            return selected_problem
            except Exception as e:
                print(f"약점 기반 필터링 오류: {str(e)}")
                # 오류 발생시 일반 필터링된 문제로 진행
        
        # 랜덤 문제 선택
        selected_problem = random.choice(valid_problems)
        print(f"문제를 성공적으로 가져왔습니다. ID: {selected_problem.get('문제ID', 'unknown')}")
        
        return selected_problem
        
    except Exception as e:
        print(f"문제 가져오기 오류: {str(e)}")
        traceback.print_exc()  # 전체 오류 스택 트레이스 출력
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
    
    # 더미 데이터 사용 모드 확인
    if hasattr(st, 'secrets') and st.secrets.get("use_dummy_data", False):
        print("더미 데이터 사용 모드로 실행합니다. 학생 답안을 저장하지 않습니다.")
        return True
    
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
    
    # 더미 데이터 사용 모드 확인
    if hasattr(st, 'secrets') and st.secrets.get("use_dummy_data", False):
        print("더미 데이터 사용 모드로 실행합니다. 문제 통계를 업데이트하지 않습니다.")
        return True
    
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
    
    # 더미 데이터 사용 모드 확인
    if hasattr(st, 'secrets') and st.secrets.get("use_dummy_data", False):
        print("더미 데이터 사용 모드로 실행합니다. 시험 결과를 저장하지 않습니다.")
        return True
    
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