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
        sheets_id = st.secrets["GSHEETS_ID"]
        
        # 서비스 계정 인증 (TOML 설정에서 가져오기)
        try:
            # Streamlit secrets의 gcp_service_account 설정을 사용
            if "gcp_service_account" in st.secrets:
                service_account_info = st.secrets["gcp_service_account"]
                service_account_info = dict(service_account_info)
                
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
                        # 스프레드시트 열기
                        sheet = client.open_by_key(sheets_id)
                        
                        # 필요한 워크시트 확인 및 초기화
                        try:
                            problems_ws = sheet.worksheet("problems")
                        except gspread.exceptions.WorksheetNotFound:
                            st.error("'problems' 워크시트를 찾을 수 없습니다.")
                            return None
                        
                        try:
                            answers_ws = sheet.worksheet("student_answers")
                            # student_answers 워크시트 헤더 확인
                            headers = answers_ws.row_values(1)
                            if not headers or len(headers) < 7:
                                # 헤더 설정
                                answers_ws.clear()
                                answers_ws.append_row([
                                    "student_id",
                                    "student_name",
                                    "problem_id",
                                    "submitted_answer",
                                    "score",
                                    "feedback",
                                    "timestamp"
                                ])
                        except gspread.exceptions.WorksheetNotFound:
                            # student_answers 워크시트 생성
                            answers_ws = sheet.add_worksheet("student_answers", 1000, 7)
                            answers_ws.append_row([
                                "student_id",
                                "student_name",
                                "problem_id",
                                "submitted_answer",
                                "score",
                                "feedback",
                                "timestamp"
                            ])
                        
                        st.success("Google Sheets 연결 성공!")
                        return sheet
                        
                    except gspread.exceptions.APIError as e:
                        error_message = str(e)
                        if "404" in error_message:
                            st.error(f"스프레드시트를 찾을 수 없습니다. ID를 확인해주세요: {sheets_id}")
                        elif "403" in error_message:
                            st.error("권한이 없습니다. 스프레드시트 공유 설정을 확인해주세요.")
                        else:
                            st.error(f"API 오류: {error_message}")
                        return None
                        
                except Exception as auth_error:
                    st.error(f"인증 처리 중 오류 발생: {str(auth_error)}")
                    return None
            else:
                st.error("서비스 계정 설정을 찾을 수 없습니다.")
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
            # 가짜 문제 데이터 반환
            dummy_problems = [
                {
                    "문제ID": "dummy-1",
                    "문제내용": "What is the correct form of the verb 'write' in the present perfect tense?",
                    "보기1": "having written",
                    "보기2": "has wrote",
                    "보기3": "has written",
                    "보기4": "have been writing",
                    "보기5": "had written",
                    "정답": "보기3",
                    "해설": "Present perfect tense는 'have/has + past participle' 형태로, 'write'의 past participle은 'written'입니다."
                },
                {
                    "문제ID": "dummy-2",
                    "문제내용": "Choose the correct sentence with the appropriate use of articles.",
                    "보기1": "I saw an unicorn in the forest yesterday.",
                    "보기2": "She is the best student in an class.",
                    "보기3": "He bought a new car, and the car is red.",
                    "보기4": "We had the dinner at restaurant last night.",
                    "보기5": "I need a advice about this problem.",
                    "정답": "보기3",
                    "해설": "관사 사용에서 'an'은 모음 소리로 시작하는 단어 앞에, 'a'는 자음 소리로 시작하는 단어 앞에 사용됩니다. 특정 대상을 지칭할 때 'the'를 사용합니다."
                },
                {
                    "문제ID": "dummy-3",
                    "문제내용": "Which option contains the correct comparative and superlative forms of the adjective 'good'?",
                    "보기1": "good, gooder, goodest",
                    "보기2": "good, better, best",
                    "보기3": "good, more good, most good",
                    "보기4": "well, better, best",
                    "보기5": "good, well, best",
                    "정답": "보기2",
                    "해설": "'good'의 비교급은 'better', 최상급은 'best'입니다. 이는 불규칙 형용사로 'more good'이나 'most good' 형태로 변화하지 않습니다."
                }
            ]
            return random.choice(dummy_problems)
        
        try:
            # '문제' 워크시트 열기
            worksheet = sheet.worksheet("problems")
            
            # 모든 문제 데이터 가져오기
            all_data = worksheet.get_all_records()
            
            # 데이터가 없으면 가짜 데이터 반환
            if not all_data:
                st.warning("문제 데이터가 없습니다. 가짜 데이터를 사용합니다.")
                return dummy_problems[0]
            
            # 랜덤 문제 선택
            random_problem = random.choice(all_data)
            return random_problem
        except Exception as e:
            st.error(f"워크시트 접근 오류: {e}. 가짜 데이터를 사용합니다.")
            return dummy_problems[0]
    
    except Exception as e:
        st.error(f"문제 가져오기 오류: {e}")
        return None

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
                student_id,
                student_name,
                problem_id,
                submitted_answer,
                score,
                feedback,
                current_time
            ]
            
            # 데이터 추가
            worksheet.append_row(row_data)
            return True
        except Exception as e:
            st.error(f"워크시트 접근 오류: {e}. 로컬에만 저장합니다.")
            return True
    
    except Exception as e:
        st.error(f"답변 저장 오류: {e}")
        return False 