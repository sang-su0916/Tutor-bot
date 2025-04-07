import gspread
import streamlit as st
import random
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

def connect_to_sheets():
    """
    Google Sheets에 연결하고 문서를 반환합니다.
    """
    try:
        # Streamlit secrets에서 인증 정보 가져오기
        if "GSHEETS_ID" not in st.secrets:
            st.error("GSHEETS_ID가 secrets에 설정되어 있지 않습니다.")
            return None
            
        sheets_id = st.secrets["GSHEETS_ID"]
        st.info(f"스프레드시트 ID: {sheets_id}")
        
        # 서비스 계정 인증 (TOML 설정에서 가져오기)
        try:
            # Streamlit secrets의 gcp_service_account 설정을 사용
            if "gcp_service_account" not in st.secrets:
                st.error("gcp_service_account가 secrets에 설정되어 있지 않습니다.")
                return None
                
            service_account_info = st.secrets["gcp_service_account"]
            service_account_info = dict(service_account_info)
            
            # 필수 필드 확인
            required_fields = ["client_email", "private_key"]
            for field in required_fields:
                if field not in service_account_info:
                    st.error(f"서비스 계정 설정에서 {field}가 누락되었습니다.")
                    return None
            
            st.info(f"서비스 계정 이메일: {service_account_info['client_email']}")
            
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
                    # 스프레드시트 열기 전에 접근 가능한 문서 목록 확인
                    spreadsheets = client.list_spreadsheet_files()
                    accessible_sheets = [sheet['name'] for sheet in spreadsheets]
                    st.info(f"접근 가능한 스프레드시트 목록: {accessible_sheets}")
                    
                    # 먼저 이름으로 시도
                    try:
                        sheet = client.open("Tutor-bot")
                        st.success("이름으로 스프레드시트 접근 성공!")
                    except gspread.exceptions.SpreadsheetNotFound:
                        st.warning("이름으로 스프레드시트를 찾을 수 없어 ID로 시도합니다.")
                        try:
                            sheet = client.open_by_key(sheets_id)
                            st.success("ID로 스프레드시트 접근 성공!")
                        except gspread.exceptions.APIError as e:
                            error_message = str(e)
                            if "404" in error_message:
                                st.error(f"스프레드시트를 찾을 수 없습니다. ID가 올바른지 확인해주세요: {sheets_id}")
                                st.info("1. 스프레드시트 ID가 올바른지 확인")
                                st.info("2. 서비스 계정에 스프레드시트가 공유되어 있는지 확인")
                                return None
                            elif "403" in error_message:
                                st.error("권한이 없습니다. 다음 사항을 확인해주세요:")
                                st.info("1. 스프레드시트가 서비스 계정과 공유되어 있는지 확인")
                                st.info("2. Google Sheets API가 활성화되어 있는지 확인")
                                st.info("3. Google Drive API가 활성화되어 있는지 확인")
                                return None
                            else:
                                st.error(f"API 오류: {error_message}")
                                return None
                    
                    # 워크시트 목록 확인
                    worksheet_list = sheet.worksheets()
                    worksheet_names = [ws.title for ws in worksheet_list]
                    st.info(f"스프레드시트의 워크시트 목록: {worksheet_names}")
                    
                    if "problems" not in worksheet_names:
                        st.error("'problems' 워크시트가 없습니다.")
                        return None
                        
                    if "student_answers" not in worksheet_names:
                        st.info("'student_answers' 워크시트를 생성합니다.")
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
                    
                    st.success("Google Sheets 연결 성공!")
                    return sheet
                    
                except Exception as e:
                    st.error(f"스프레드시트 접근 중 오류 발생: {str(e)}")
                    return None
                
            except Exception as auth_error:
                st.error(f"인증 처리 중 오류 발생: {str(auth_error)}")
                return None
                
        except Exception as e:
            st.error(f"서비스 계정 설정 오류: {e}")
            return None
    
    except Exception as e:
        st.error(f"Google Sheets 연결 오류: {e}")
        return None

def get_random_problem():
    """
    Google Sheets에서 랜덤 문제를 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            st.error("Google Sheets 연결 실패")
            return get_dummy_problem()
        
        try:
            # '문제' 워크시트 열기
            worksheet = sheet.worksheet("problems")
            
            try:
                # 모든 문제 데이터 가져오기
                all_data = worksheet.get_all_records()
                
                # 데이터 확인 및 처리
                if not all_data:
                    st.warning("문제 데이터가 없습니다.")
                    return get_dummy_problem()
                
                # 데이터 구조 확인
                st.info(f"가져온 문제 수: {len(all_data)}")
                if len(all_data) > 0:
                    st.info(f"문제 데이터 구조: {list(all_data[0].keys())}")
                
                # 필수 필드 확인
                required_fields = ["문제ID", "문제내용", "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "해설"]
                for problem in all_data:
                    missing_fields = [field for field in required_fields if field not in problem or not problem[field]]
                    if missing_fields:
                        continue
                    
                # 유효한 문제만 필터링
                valid_problems = [p for p in all_data if all(field in p and p[field] for field in required_fields)]
                
                if not valid_problems:
                    st.warning("유효한 문제가 없습니다.")
                    return get_dummy_problem()
                
                # 랜덤 문제 선택
                random_problem = random.choice(valid_problems)
                st.success("문제를 성공적으로 가져왔습니다!")
                return random_problem
                
            except Exception as data_error:
                st.error(f"데이터 처리 중 오류 발생: {str(data_error)}")
                return get_dummy_problem()
                
        except Exception as ws_error:
            st.error(f"워크시트 접근 오류: {str(ws_error)}")
            return get_dummy_problem()
            
    except Exception as e:
        st.error(f"문제 가져오기 오류: {str(e)}")
        return get_dummy_problem()

def get_dummy_problem():
    """
    더미 문제를 반환합니다.
    """
    dummy_problems = [
        {
            "문제ID": "dummy-1",
            "문제내용": "Choose the correct sentence with the appropriate use of articles.",
            "보기1": "I saw an unicorn in the forest yesterday.",
            "보기2": "She is the best student in an class.",
            "보기3": "He bought a new car, and the car is red.",
            "보기4": "We had the dinner at restaurant last night.",
            "보기5": "I need a advice about this problem.",
            "정답": "보기3",
            "해설": "관사 사용에서 'an'은 모음 소리로 시작하는 단어 앞에, 'a'는 자음 소리로 시작하는 단어 앞에 사용됩니다. 특정 대상을 지칭할 때 'the'를 사용합니다."
        }
    ]
    st.warning("더미 문제를 사용합니다.")
    return dummy_problems[0]

def save_student_answer(student_id, student_name, problem_id, submitted_answer, score, feedback):
    """
    학생 답안과 점수를 Google Sheets에 저장합니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            st.info("Google Sheets 연결이 없어 로컬에만 답변이 저장됩니다.")
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
            st.success("답안이 성공적으로 저장되었습니다!")
            return True
        except Exception as e:
            st.error(f"워크시트 접근 오류: {e}. 로컬에만 저장합니다.")
            return True
    
    except Exception as e:
        st.error(f"답변 저장 오류: {e}")
        return False 