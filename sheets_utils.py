import gspread
import streamlit as st
import random
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
import time

def connect_to_sheets():
    """
    Google Sheets에 연결하고 문서를 반환합니다.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Streamlit secrets에서 인증 정보 가져오기
            if "GSHEETS_ID" not in st.secrets:
                return None
                
            sheets_id = st.secrets["GSHEETS_ID"]
            
            # 서비스 계정 인증 (TOML 설정에서 가져오기)
            try:
                # Streamlit secrets의 gcp_service_account 설정을 사용
                if "gcp_service_account" not in st.secrets:
                    return None
                    
                service_account_info = dict(st.secrets["gcp_service_account"])
                
                # 필수 필드 확인
                required_fields = ["client_email", "private_key", "private_key_id", "project_id"]
                missing_fields = [field for field in required_fields if field not in service_account_info]
                if missing_fields:
                    return None
                
                # API 범위 설정
                scope = [
                    'https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                
                try:
                    # 인증 및 클라이언트 생성
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
                    client = gspread.authorize(creds)
                    
                    try:
                        # 먼저 이름으로 시도
                        try:
                            sheet = client.open("Tutor-bot")
                        except gspread.exceptions.SpreadsheetNotFound:
                            try:
                                sheet = client.open_by_key(sheets_id)
                            except gspread.exceptions.APIError:
                                return None
                        
                        # 워크시트 확인 및 생성
                        worksheet_list = sheet.worksheets()
                        worksheet_names = [ws.title for ws in worksheet_list]
                        
                        # problems 워크시트 확인
                        if "problems" not in worksheet_names:
                            return None
                        
                        # student_answers 워크시트 확인 및 생성
                        if "student_answers" not in worksheet_names:
                            try:
                                answers_ws = sheet.add_worksheet("student_answers", 1000, 7)
                                answers_ws.append_row([
                                    "학생ID",
                                    "이름",
                                    "문제ID",
                                    "제출답안",
                                    "점수",
                                    "피드백",
                                    "제출시간"
                                ])
                            except:
                                pass
                        
                        return sheet
                        
                    except Exception:
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            time.sleep(1)
                            continue
                        return None
                    
                except Exception:
                    return None
                    
            except Exception:
                return None
        
        except Exception:
            if retry_count < max_retries - 1:
                retry_count += 1
                time.sleep(1)
                continue
            return None
    
    return None

def get_random_problem():
    """
    Google Sheets에서 랜덤 문제를 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return get_dummy_problem()
        
        try:
            # '문제' 워크시트 열기
            worksheet = sheet.worksheet("problems")
            
            try:
                # 모든 문제 데이터 가져오기
                all_data = worksheet.get_all_records()
                
                # 데이터 확인 및 처리
                if not all_data:
                    return get_dummy_problem()
                
                # 필수 필드 확인
                required_fields = ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "키워드", "해설"]
                
                # 유효한 문제만 필터링
                valid_problems = []
                for problem in all_data:
                    # 필수 필드가 모두 있고 값이 비어있지 않은지 확인
                    if all(field in problem and str(problem[field]).strip() for field in ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "정답"]):
                        valid_problems.append(problem)
                    
                if not valid_problems:
                    return get_dummy_problem()
                
                # 세션 상태 초기화
                if "previous_problems" not in st.session_state:
                    st.session_state.previous_problems = set()
                    st.session_state.total_problems = len(valid_problems)
                    st.session_state.current_round = 1
                
                # 아직 출제되지 않은 문제만 필터링
                available_problems = [p for p in valid_problems if p["문제ID"] not in st.session_state.previous_problems]
                
                # 모든 문제가 출제되었다면 이력을 초기화
                if not available_problems:
                    st.session_state.previous_problems = set()
                    st.session_state.current_round += 1
                    available_problems = valid_problems
                
                # 랜덤 문제 선택 (이전 문제와 다른 문제 선택)
                random_problem = random.choice(available_problems)
                
                # 출제된 문제 ID 기록
                st.session_state.previous_problems.add(random_problem["문제ID"])
                
                # 문제 데이터 정리
                cleaned_problem = {
                    "문제ID": random_problem["문제ID"],
                    "과목": random_problem["과목"],
                    "학년": random_problem["학년"],
                    "문제유형": random_problem["문제유형"],
                    "난이도": random_problem["난이도"],
                    "문제내용": random_problem["문제내용"].strip(),
                    "정답": random_problem["정답"],
                    "키워드": random_problem.get("키워드", ""),
                    "해설": random_problem.get("해설", "").strip()
                }
                
                # 보기 정리 (빈 보기 제외)
                for i in range(1, 6):
                    option_key = f"보기{i}"
                    if option_key in random_problem and random_problem[option_key].strip():
                        cleaned_problem[option_key] = random_problem[option_key].strip()
                
                return cleaned_problem
                
            except Exception:
                return get_dummy_problem()
                
        except Exception:
            return get_dummy_problem()
            
    except Exception:
        return get_dummy_problem()

def get_dummy_problem():
    """
    더미 문제를 반환합니다.
    """
    dummy_problems = [
        {
            "문제ID": "dummy-1",
            "과목": "영어",
            "학년": "중1",
            "문제유형": "객관식",
            "난이도": "하",
            "문제내용": "Which verb best completes the sentence: Our class ___ the article?",
            "보기1": "discussed",
            "보기2": "discusses",
            "보기3": "discussing",
            "보기4": "discuss",
            "보기5": "to discuss",
            "정답": "보기1",
            "키워드": "동사 시제",
            "해설": "과거 시제를 사용해야 합니다. 주어가 'Our class'로 3인칭 단수이고, 과거의 행동을 나타내므로 'discussed'가 정답입니다."
        }
    ]
    return dummy_problems[0]

def save_student_answer(student_id, student_name, problem_id, submitted_answer, score, feedback):
    """
    학생 답안과 점수를 Google Sheets에 저장합니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return True
        
        try:
            # '학생답변' 워크시트 열기
            worksheet = sheet.worksheet("student_answers")
            
            # 현재 시간
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 저장할 데이터
            row_data = [
                student_id,          # 학생ID
                student_name,        # 이름
                problem_id,          # 문제ID
                submitted_answer,    # 제출답안
                score,              # 점수
                feedback,           # 피드백
                current_time        # 제출시간
            ]
            
            # 데이터 추가
            worksheet.append_row(row_data)
            return True
            
        except Exception:
            return True
    
    except Exception:
        return True 