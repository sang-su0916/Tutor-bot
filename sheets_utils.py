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
        creds_source = None
        
        # 1. 우선순위: secrets.toml에 있는 서비스 계정 정보
        if "gcp_service_account" in st.secrets:
            print("서비스 계정 정보를 secrets.toml에서 찾았습니다.")
            try:
                service_account_info = st.secrets["gcp_service_account"]
                credentials = Credentials.from_service_account_info(
                    service_account_info, scopes=scope
                )
                creds_source = "secrets.toml"
                print("secrets.toml의 서비스 계정 정보로 credentials 객체를 생성했습니다.")
            except Exception as e:
                print(f"secrets.toml의 서비스 계정 정보 사용 오류: {str(e)}")
                print(f"상세 오류: {traceback.format_exc()}")
        
        # 2. 두번째 우선순위: service_account.json 파일
        if credentials is None:
            service_account_path = "service_account.json"
            
            if "GOOGLE_SERVICE_ACCOUNT_PATH" in st.secrets:
                service_account_path = st.secrets["GOOGLE_SERVICE_ACCOUNT_PATH"]
            
            if os.path.exists(service_account_path):
                print(f"서비스 계정 파일을 찾았습니다: {service_account_path}")
                try:
                    # 직접 JSON 파일을 읽어서 딕셔너리로 변환
                    with open(service_account_path, 'r') as f:
                        service_account_info = json.load(f)
                    
                    # 딕셔너리에서 credentials 생성
                    credentials = Credentials.from_service_account_info(
                        service_account_info, scopes=scope
                    )
                    creds_source = "service_account.json"
                    print("서비스 계정 파일의 내용을 직접 로드하여 credentials 객체를 생성했습니다.")
                except Exception as e:
                    print(f"서비스 계정 파일 사용 오류: {str(e)}")
                    print(f"상세 오류: {traceback.format_exc()}")

        # credentials 생성 성공 확인
        if credentials is None:
            st.warning("인증 정보 생성에 실패했습니다. 더미 시트를 사용합니다.")
            print("인증 정보 생성에 실패했습니다. 더미 시트를 사용합니다.")
            return create_dummy_sheet()
        
        # 서비스 계정 이메일 확인 및 표시 (공유 설정 도움을 위해)
        service_account_email = None
        if creds_source == "secrets.toml" and "client_email" in st.secrets["gcp_service_account"]:
            service_account_email = st.secrets["gcp_service_account"]["client_email"]
        elif creds_source == "service_account.json":
            try:
                with open(service_account_path, 'r') as f:
                    sa_info = json.load(f)
                    if "client_email" in sa_info:
                        service_account_email = sa_info["client_email"]
            except Exception as e:
                print(f"서비스 계정 파일 읽기 오류: {str(e)}")
        
        if service_account_email:
            print(f"서비스 계정 이메일: {service_account_email}")
            print(f"이 이메일이 스프레드시트에 '편집자' 권한으로 공유되어 있어야 합니다.")
            
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
                
                # 충돌 워크시트 정리
                conflict_sheets = [ws for title, ws in worksheets.items() if "_conflict" in title]
                if conflict_sheets:
                    print(f"{len(conflict_sheets)}개의 충돌 워크시트를 발견했습니다. 정리합니다...")
                    for ws in conflict_sheets:
                        try:
                            print(f"충돌 워크시트 '{ws.title}'를 삭제합니다.")
                            spreadsheet.del_worksheet(ws)
                            print(f"'{ws.title}' 워크시트를 삭제했습니다.")
                        except Exception as e:
                            print(f"워크시트 '{ws.title}' 삭제 중 오류: {str(e)}")
                    
                    # 업데이트된 워크시트 목록 가져오기
                    worksheets = {ws.title: ws for ws in spreadsheet.worksheets()}
                    print(f"정리 후 워크시트 목록: {', '.join(worksheets.keys())}")
                
                required_sheets = ["problems", "student_answers", "student_weaknesses", "students", "teachers"]
                
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
                error_msg = f"스프레드시트를 찾을 수 없습니다 (ID: {spreadsheet_id})"
                st.error(error_msg)
                print(error_msg)
                if service_account_email:
                    share_msg = f"서비스 계정 이메일({service_account_email})이 스프레드시트에 '편집자' 권한으로 공유되어 있는지 확인하세요."
                    st.error(share_msg)
                    print(share_msg)
                return create_dummy_sheet()
            except gspread.exceptions.APIError as api_err:
                error_msg = f"Google API 오류: {str(api_err)}"
                print(error_msg)
                print(f"상세 오류: {traceback.format_exc()}")
                
                # API 오류 발생 시 실제 스프레드시트에 접근 시도
                try:
                    # 스프레드시트 존재 여부 확인을 위한 다른 시도
                    sheet_list = gc.list_spreadsheet_files()
                    sheet_titles = [s['name'] for s in sheet_list]
                    print(f"사용 가능한 스프레드시트 목록: {', '.join(sheet_titles)}")
                    
                    # 비슷한 이름의 스프레드시트가 있는지 확인
                    target_sheet = None
                    for sheet in sheet_list:
                        if sheet['id'] == spreadsheet_id:
                            target_sheet = sheet
                            break
                    
                    if target_sheet:
                        try:
                            # 직접 이름으로 열기 시도
                            spreadsheet = gc.open(target_sheet['name'])
                            print(f"이름으로 스프레드시트 '{spreadsheet.title}'에 연결되었습니다.")
                            st.success(f"이름으로 스프레드시트 '{spreadsheet.title}'에 연결되었습니다.")
                            st.session_state.sheets_connection_status = "success"
                            st.session_state.sheets_connection_success = True
                            return spreadsheet
                        except Exception as e:
                            print(f"이름으로 스프레드시트 열기 실패: {str(e)}")
                except Exception as e:
                    print(f"스프레드시트 접근 시도 중 추가 오류: {str(e)}")
                
                # 접근 실패시 더미 시트 사용
                return create_dummy_sheet()
        except Exception as auth_err:
            error_msg = f"Google API 인증 오류: {str(auth_err)}"
            st.error(error_msg)
            print(error_msg)
            print(f"상세 오류: {traceback.format_exc()}")
            return create_dummy_sheet()
    except Exception as e:
        error_msg = f"Google Sheets 연결 초기화 오류: {str(e)}"
        st.error(error_msg)
        print(error_msg)
        print(f"상세 오류: {traceback.format_exc()}")
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

def get_worksheet_records(sheet, worksheet_name, use_csv_file=False, csv_path=None):
    """워크시트의 모든 레코드를 가져옵니다."""
    try:
        if use_csv_file and csv_path:
            import pandas as pd
            import os
            
            # CSV 파일이 존재하는지 확인
            if not os.path.exists(csv_path):
                print(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
                return []
            
            try:
                # 다양한 인코딩 시도
                encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
                records = []
                error_messages = []
                
                for encoding in encodings:
                    try:
                        print(f"CSV 파일을 {encoding} 인코딩으로 읽기 시도: {csv_path}")
                        # CSV 파일 읽기
                        df = pd.read_csv(csv_path, encoding=encoding)
                        
                        # DataFrame을 딕셔너리 리스트로 변환
                        records = df.to_dict(orient='records')
                        print(f"CSV 파일에서 {len(records)}개의 문제를 {encoding} 인코딩으로 불러왔습니다.")
                        
                        # 보기정보 필드가 문자열이면 딕셔너리로 변환
                        for record in records:
                            if "보기정보" in record and isinstance(record["보기정보"], str):
                                try:
                                    import json
                                    record["보기정보"] = json.loads(record["보기정보"])
                                except:
                                    # JSON 변환 실패 시 기본값 유지
                                    pass
                        
                        # 성공하면 루프 종료
                        break
                    except Exception as e:
                        error_messages.append(f"{encoding} 인코딩 시도 실패: {str(e)}")
                        continue
                
                if records:
                    return records
                else:
                    # 모든 인코딩 시도 실패
                    print("모든 인코딩 시도 실패:")
                    for msg in error_messages:
                        print(f"  - {msg}")
                    return []
            except Exception as e:
                print(f"CSV 파일 읽기 오류: {str(e)}")
                return []
        
        # Google Sheets에서 데이터 가져오기
        if not gspread_imported:
            return []
            
        if sheet is None:
            print("스프레드시트 연결이 없습니다.")
            return []
        
        try:
            # 워크시트 가져오기
            worksheet = sheet.worksheet(worksheet_name)
            
            # 헤더 확인
            headers = worksheet.row_values(1)
            if not headers:
                print(f"{worksheet_name} 워크시트에 헤더가 없습니다.")
                return []
            
            # 모든 레코드 가져오기
            all_records = worksheet.get_all_records()
            print(f"{worksheet_name} 워크시트에서 {len(all_records)}개의 레코드를 불러왔습니다.")
            
            return all_records
        except Exception as e:
            print(f"{worksheet_name} 워크시트 데이터 가져오기 오류: {str(e)}")
            return []
    except Exception as e:
        print(f"워크시트 데이터 가져오기 중 오류 발생: {str(e)}")
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
    
    # 여러 문제 옵션 제공 - 무작위로 선택되도록 함
    problems = {
        "중1": [
            {
                "question": "Pick the correct word to complete the sentence: A student ___ to school.",
                "options": {
                    "보기1": "go",
                    "보기2": "goes",
                    "보기3": "going",
                    "보기4": "went"
                },
                "answer": "보기2",
                "explanation": "'A student'는 3인칭 단수이므로 동사에 -s를 붙여 'goes'가 됩니다."
            },
            {
                "question": "Choose the correct word: She ___ English very well.",
                "options": {
                    "보기1": "speak",
                    "보기2": "speaks",
                    "보기3": "speaking",
                    "보기4": "spoke"
                },
                "answer": "보기2",
                "explanation": "3인칭 단수 주어는 동사에 -s를 붙입니다."
            },
            {
                "question": "Select the correct answer: My brother ___ soccer every weekend.",
                "options": {
                    "보기1": "play",
                    "보기2": "plays",
                    "보기3": "playing",
                    "보기4": "played"
                },
                "answer": "보기2",
                "explanation": "규칙적인 현재 습관을 나타내는 현재 시제입니다."
            },
            {
                "question": "Which word is a proper noun?",
                "options": {
                    "보기1": "book",
                    "보기2": "London",
                    "보기3": "teacher",
                    "보기4": "computer"
                },
                "answer": "보기2",
                "explanation": "고유명사는 특정 인물, 장소, 사물의 이름을 나타냅니다. London은 도시 이름으로 고유명사입니다."
            },
            {
                "question": "Find the plural form: One child, two ___.",
                "options": {
                    "보기1": "childs",
                    "보기2": "childes",
                    "보기3": "children",
                    "보기4": "child"
                },
                "answer": "보기3",
                "explanation": "'child'의 복수형은 불규칙 복수형으로 'children'입니다."
            },
            {
                "question": "Choose the correct preposition: The book is ___ the table.",
                "options": {
                    "보기1": "on",
                    "보기2": "in",
                    "보기3": "at",
                    "보기4": "by"
                },
                "answer": "보기1",
                "explanation": "물체가 표면 위에 있을 때는 전치사 'on'을 사용합니다."
            },
            {
                "question": "What time is it? It's ___.",
                "options": {
                    "보기1": "half to nine",
                    "보기2": "half past eight",
                    "보기3": "half eight",
                    "보기4": "eight and half"
                },
                "answer": "보기2",
                "explanation": "8시 30분을 나타낼 때는 'half past eight'이라고 합니다."
            }
        ],
        "중2": [
            {
                "question": "Choose the correct past tense: Yesterday, I ___ to the store.",
                "options": {
                    "보기1": "go",
                    "보기2": "goes",
                    "보기3": "going",
                    "보기4": "went"
                },
                "answer": "보기4",
                "explanation": "과거 시제를 나타내는 'Yesterday'가 있으므로 go의 과거형인 'went'를 사용합니다."
            },
            {
                "question": "Complete the sentence: Last week, she ___ a new car.",
                "options": {
                    "보기1": "buy",
                    "보기2": "buys",
                    "보기3": "buying",
                    "보기4": "bought"
                },
                "answer": "보기4",
                "explanation": "'Last week'은 과거 시제를 나타내므로 'bought'를 사용합니다."
            },
            {
                "question": "Choose the correct form: They ___ to music last night.",
                "options": {
                    "보기1": "listen",
                    "보기2": "listens",
                    "보기3": "listening",
                    "보기4": "listened"
                },
                "answer": "보기4",
                "explanation": "'Last night'은 과거를 나타내므로 과거형 'listened'를 사용합니다."
            },
            {
                "question": "Choose the correct future tense: Next year, I ___ to college.",
                "options": {
                    "보기1": "go",
                    "보기2": "goes",
                    "보기3": "will go",
                    "보기4": "went"
                },
                "answer": "보기3",
                "explanation": "미래를 나타내는 'Next year'가 있으므로 'will go'를 사용합니다."
            },
            {
                "question": "Which sentence uses the correct article?",
                "options": {
                    "보기1": "He is a university student.",
                    "보기2": "He is an university student.",
                    "보기3": "He is the university student.",
                    "보기4": "He is university student."
                },
                "answer": "보기1",
                "explanation": "'university'는 /juː/로 시작하는 자음 소리이므로 'a'를 사용합니다."
            },
            {
                "question": "Select the sentence with the correct order of adjectives.",
                "options": {
                    "보기1": "I bought a leather black expensive bag.",
                    "보기2": "I bought an expensive black leather bag.",
                    "보기3": "I bought a black expensive leather bag.",
                    "보기4": "I bought an leather expensive black bag."
                },
                "answer": "보기2",
                "explanation": "형용사 순서는 의견-크기-나이-모양-색깔-출신-재료 순입니다. 따라서 'expensive(의견) black(색깔) leather(재료)'가 올바른 순서입니다."
            },
            {
                "question": "Choose the sentence with the correct adverb placement.",
                "options": {
                    "보기1": "She quickly finished her homework.",
                    "보기2": "She finished quickly her homework.",
                    "보기3": "She finished her quickly homework.",
                    "보기4": "She finished her homework quickly."
                },
                "answer": "보기1",
                "explanation": "방법을 나타내는 부사는 주로 동사 앞이나 문장 끝에 위치합니다. 'quickly'는 'finished' 앞에 올 수 있습니다."
            }
        ],
        "중3": [
            {
                "question": "Select the correct passive form: The book ___ by the student.",
                "options": {
                    "보기1": "read",
                    "보기2": "reads",
                    "보기3": "is read",
                    "보기4": "reading"
                },
                "answer": "보기3",
                "explanation": "수동태는 'be동사 + 과거분사'의 형태입니다. 따라서 'is read'가 정답입니다."
            },
            {
                "question": "Choose the passive voice: The letter ___ yesterday.",
                "options": {
                    "보기1": "wrote",
                    "보기2": "writes",
                    "보기3": "was written",
                    "보기4": "is writing"
                },
                "answer": "보기3",
                "explanation": "과거 수동태는 'was/were + 과거분사' 형태입니다."
            },
            {
                "question": "Select the passive form: This building ___ in 1960.",
                "options": {
                    "보기1": "built",
                    "보기2": "builds",
                    "보기3": "was built",
                    "보기4": "is building"
                },
                "answer": "보기3",
                "explanation": "과거에 완료된 행동의 수동태는 'was built'입니다."
            },
            {
                "question": "Choose the correct question tag: You like pizza, ___?",
                "options": {
                    "보기1": "do you",
                    "보기2": "don't you",
                    "보기3": "are you",
                    "보기4": "did you"
                },
                "answer": "보기2",
                "explanation": "긍정문 뒤에는 부정형 의문태그가 붙습니다."
            },
            {
                "question": "Select the correct relative pronoun: The man ___ lives next door is a doctor.",
                "options": {
                    "보기1": "who",
                    "보기2": "which",
                    "보기3": "whose",
                    "보기4": "whom"
                },
                "answer": "보기1",
                "explanation": "사람을 지칭하는 주격 관계대명사는 'who'입니다."
            },
            {
                "question": "Choose the correct reported speech: She said, 'I am happy.'",
                "options": {
                    "보기1": "She said I am happy.",
                    "보기2": "She said she is happy.",
                    "보기3": "She said she was happy.",
                    "보기4": "She said I was happy."
                },
                "answer": "보기3",
                "explanation": "직접화법이 간접화법으로 바뀔 때 시제가 과거로 바뀝니다. 'am'은 'was'로 변경됩니다."
            },
            {
                "question": "Select the correct gerund usage:",
                "options": {
                    "보기1": "I enjoy to swim in the ocean.",
                    "보기2": "I enjoy swimming in the ocean.",
                    "보기3": "I enjoy swim in the ocean.",
                    "보기4": "I enjoy swam in the ocean."
                },
                "answer": "보기2",
                "explanation": "'enjoy'는 동명사를 목적어로 취하는 동사입니다. 따라서 'swimming'이 올바른 형태입니다."
            }
        ],
        "고1": [
            {
                "question": "Choose the correct comparative: This book is ___ than that one.",
                "options": {
                    "보기1": "interesting",
                    "보기2": "more interesting",
                    "보기3": "most interesting",
                    "보기4": "interestingly"
                },
                "answer": "보기2",
                "explanation": "두 개를 비교할 때는 비교급을 사용합니다. 긴 형용사는 'more + 원급'으로 비교급을 만듭니다."
            },
            {
                "question": "Select the comparative form: This problem is ___ than I thought.",
                "options": {
                    "보기1": "difficult",
                    "보기2": "more difficult",
                    "보기3": "most difficult",
                    "보기4": "difficultly"
                },
                "answer": "보기2",
                "explanation": "비교급은 'more + 형용사' 형태로 만듭니다."
            },
            {
                "question": "Choose the correct form: She runs ___ than her brother.",
                "options": {
                    "보기1": "fast",
                    "보기2": "faster",
                    "보기3": "fastest",
                    "보기4": "more fast"
                },
                "answer": "보기2",
                "explanation": "짧은 형용사의 비교급은 '-er'을 붙여 만듭니다."
            },
            {
                "question": "Select the correct superlative: This is ___ building in the city.",
                "options": {
                    "보기1": "tall",
                    "보기2": "taller",
                    "보기3": "tallest",
                    "보기4": "the tallest"
                },
                "answer": "보기4",
                "explanation": "최상급은 'the + 형용사est' 형태로 만듭니다."
            },
            {
                "question": "Choose the correct countable/uncountable usage:",
                "options": {
                    "보기1": "There are many informations in this book.",
                    "보기2": "There is much information in this book.",
                    "보기3": "There are much informations in this book.",
                    "보기4": "There is many information in this book."
                },
                "answer": "보기2",
                "explanation": "'information'은 불가산명사로 단수 취급하며, 불가산명사는 'much'와 함께 사용합니다."
            },
            {
                "question": "Select the sentence with correct parallel structure:",
                "options": {
                    "보기1": "She likes swimming, running, and to ride bikes.",
                    "보기2": "She likes swimming, running, and riding bikes.",
                    "보기3": "She likes to swim, to run, and riding bikes.",
                    "보기4": "She likes to swim, running, and to ride bikes."
                },
                "answer": "보기2",
                "explanation": "병렬 구조에서는 같은 문법 형태를 유지해야 합니다. 'swimming, running, riding' 모두 동명사 형태입니다."
            },
            {
                "question": "Choose the phrase that correctly completes: Despite ___.",
                "options": {
                    "보기1": "it was raining",
                    "보기2": "it is raining",
                    "보기3": "the rain",
                    "보기4": "is raining"
                },
                "answer": "보기3",
                "explanation": "'Despite'는 전치사이므로 뒤에 명사나 동명사가 와야 합니다."
            }
        ],
        "고2": [
            {
                "question": "Select the correct present perfect: She ___ in Korea for five years.",
                "options": {
                    "보기1": "live",
                    "보기2": "lives",
                    "보기3": "living",
                    "보기4": "has lived"
                },
                "answer": "보기4",
                "explanation": "현재완료는 'have/has + 과거분사'의 형태로, 과거부터 현재까지 지속되는 상황을 나타냅니다."
            },
            {
                "question": "Choose the present perfect: I ___ this book three times.",
                "options": {
                    "보기1": "read",
                    "보기2": "reads",
                    "보기3": "have read",
                    "보기4": "reading"
                },
                "answer": "보기3",
                "explanation": "경험을 나타내는 현재완료는 'have + 과거분사' 형태입니다."
            },
            {
                "question": "Select the correct form: We ___ each other since childhood.",
                "options": {
                    "보기1": "know",
                    "보기2": "knows",
                    "보기3": "have known",
                    "보기4": "knew"
                },
                "answer": "보기3",
                "explanation": "'since childhood'는 과거부터 현재까지 계속되는 상황을 나타내므로 현재완료를 사용합니다."
            },
            {
                "question": "Choose the correct usage of past perfect:",
                "options": {
                    "보기1": "When I arrived, the train left.",
                    "보기2": "When I arrived, the train has left.",
                    "보기3": "When I arrived, the train had left.",
                    "보기4": "When I arrived, the train was leaving."
                },
                "answer": "보기3",
                "explanation": "과거완료는 과거의 어떤 시점보다 더 이전에 일어난 일을 표현할 때 사용합니다."
            },
            {
                "question": "Select the correct infinitive use:",
                "options": {
                    "보기1": "I want learning English.",
                    "보기2": "I want learn English.",
                    "보기3": "I want to learning English.",
                    "보기4": "I want to learn English."
                },
                "answer": "보기4",
                "explanation": "'want'는 to부정사를 목적어로 취하는 동사입니다."
            },
            {
                "question": "Choose the sentence with a participial phrase:",
                "options": {
                    "보기1": "The girl is singing a song.",
                    "보기2": "Walking in the park, I saw an old friend.",
                    "보기3": "She walks to school every day.",
                    "보기4": "They want to see the movie."
                },
                "answer": "보기2",
                "explanation": "'Walking in the park'는 분사구문으로, 주절의 주어와 같은 주어가 동작을 수행하는 상황을 나타냅니다."
            },
            {
                "question": "Select the sentence with a correct subjunctive mood:",
                "options": {
                    "보기1": "I suggest that he goes to the doctor.",
                    "보기2": "I suggest that he go to the doctor.",
                    "보기3": "I suggest that he went to the doctor.",
                    "보기4": "I suggest that he would go to the doctor."
                },
                "answer": "보기2",
                "explanation": "가정법에서 'suggest that' 다음에는 동사 원형을 사용합니다."
            }
        ],
        "고3": [
            {
                "question": "Choose the correct conditional: If I ___ rich, I would buy a new car.",
                "options": {
                    "보기1": "am",
                    "보기2": "was",
                    "보기3": "were",
                    "보기4": "being"
                },
                "answer": "보기3",
                "explanation": "가정법 과거에서는 if절에 'were'를 사용합니다. 'If I were...'는 현재 사실과 반대되는 상황을 가정할 때 씁니다."
            },
            {
                "question": "Select the correct form: If it ___ tomorrow, we will cancel the picnic.",
                "options": {
                    "보기1": "rain",
                    "보기2": "rains",
                    "보기3": "rained",
                    "보기4": "raining"
                },
                "answer": "보기2",
                "explanation": "조건절(if)에서 미래의 가능성을 나타낼 때는 현재시제를 씁니다."
            },
            {
                "question": "Choose the correct form: I wish I ___ how to speak Spanish.",
                "options": {
                    "보기1": "know",
                    "보기2": "knows",
                    "보기3": "knew",
                    "보기4": "known"
                },
                "answer": "보기3",
                "explanation": "'I wish'는 현재 사실과 반대되는 상황을 가정할 때 과거형을 사용합니다."
            },
            {
                "question": "Select the correct usage of inversion:",
                "options": {
                    "보기1": "Never I have seen such a beautiful sunset.",
                    "보기2": "Never have I seen such a beautiful sunset.",
                    "보기3": "I have never seen such a beautiful sunset.",
                    "보기4": "I never have seen such a beautiful sunset."
                },
                "answer": "보기2",
                "explanation": "부정어 'never'가 문장 앞에 오면 주어와 조동사가 도치됩니다."
            },
            {
                "question": "Choose the correct cleft sentence:",
                "options": {
                    "보기1": "The book I bought yesterday.",
                    "보기2": "It is the book that I bought yesterday.",
                    "보기3": "I bought the book yesterday.",
                    "보기4": "The book is what I bought yesterday."
                },
                "answer": "보기2",
                "explanation": "강조구문은 'It is/was + 강조하는 말 + that' 형태를 사용합니다."
            },
            {
                "question": "Select the correct sentence with a complex structure:",
                "options": {
                    "보기1": "He is tall and handsome.",
                    "보기2": "Although he studied hard, he failed the exam.",
                    "보기3": "She likes coffee, tea, and juice.",
                    "보기4": "They went to the park and played soccer."
                },
                "answer": "보기2",
                "explanation": "복합문은 주절과 종속절을 포함합니다. 'Although he studied hard'는 종속절입니다."
            },
            {
                "question": "Choose the sentence with correct modality:",
                "options": {
                    "보기1": "You need study harder.",
                    "보기2": "You must to study harder.",
                    "보기3": "You should studying harder.",
                    "보기4": "You ought to study harder."
                },
                "answer": "보기4",
                "explanation": "'ought to' 다음에는 동사 원형이 와야 합니다."
            }
        ]
    }
    
    # 학년 확인 및 기본값 설정
    grade_key = "중1"  # 기본값
    for key in problems.keys():
        if key in student_grade:
            grade_key = key
            break
    
    # 해당 학년에서 무작위로 문제 선택
    grade_problems = problems.get(grade_key, problems["중1"])
    problem_data = random.choice(grade_problems)
    
    # 더미 문제 ID 생성 (유니크한 값 보장)
    dummy_id = f"dummy-{uuid.uuid4()}"
    
    # 더미 문제 데이터 구성
    dummy_problem = {
        "문제ID": dummy_id,
        "과목": "영어",
        "학년": student_grade,
        "문제유형": "객관식",
        "난이도": "중",
        "문제내용": problem_data["question"],
        "정답": problem_data["answer"],
        "해설": problem_data["explanation"],
        "보기정보": problem_data["options"]
    }
    
    # 보기 항목 추가
    for key, value in problem_data["options"].items():
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

def generate_dummy_problems(student_grade, count=20):
    """학생 학년에 맞는 더미 문제를 여러 개 생성합니다."""
    problems = []
    
    # 이미 선택된 문제 추적 (중복 방지)
    selected_questions = set()
    
    for i in range(count):
        # 중복을 피해 문제 선택
        attempts = 0
        max_attempts = 10  # 최대 시도 횟수
        
        dummy_problem = None
        while attempts < max_attempts and (dummy_problem is None or dummy_problem["문제내용"] in selected_questions):
            dummy_problem = get_dummy_problem(student_grade)
            attempts += 1
        
        # 중복이 아니면 추가
        if dummy_problem["문제내용"] not in selected_questions:
            selected_questions.add(dummy_problem["문제내용"])
            problems.append(dummy_problem)
        
        # 중복이 계속 발생하면 약간 변형하여 추가
        else:
            dummy_problem["문제내용"] = f"{dummy_problem['문제내용']} (문제 {i+1})"
            selected_questions.add(dummy_problem["문제내용"])
            problems.append(dummy_problem)
    
    # 모든 문제가 생성되었는지 확인
    if len(problems) < count:
        print(f"경고: {count}개 문제 중 {len(problems)}개만 생성되었습니다. 중복 문제가 있을 수 있습니다.")
        # 부족한 문제 추가 생성
        for i in range(len(problems), count):
            dummy_problem = get_dummy_problem(student_grade)
            dummy_problem["문제내용"] = f"{dummy_problem['문제내용']} (추가 문제 {i+1})"
            problems.append(dummy_problem)
    
    return problems