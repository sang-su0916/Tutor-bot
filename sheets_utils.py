import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
from datetime import datetime
import os
import json
import time
import pandas as pd
import uuid

def connect_to_sheets():
    """
    Google Sheets에 연결하고 문서를 반환합니다.
    최대 3번까지 재시도합니다.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Streamlit secrets에서 인증 정보 가져오기
            if "GSHEETS_ID" not in st.secrets:
                st.error("스프레드시트 설정이 필요합니다.")
                return None
                
            sheets_id = st.secrets["GSHEETS_ID"]
            
            # 서비스 계정 인증 (TOML 설정에서 가져오기)
            try:
                # Streamlit secrets의 gcp_service_account 설정을 사용
                if "gcp_service_account" not in st.secrets:
                    st.error("서비스 계정 설정이 필요합니다.")
                    return None
                    
                service_account_info = dict(st.secrets["gcp_service_account"])
                
                # 필수 필드 확인
                required_fields = ["client_email", "private_key", "private_key_id", "project_id"]
                missing_fields = [field for field in required_fields if field not in service_account_info]
                
                if missing_fields:
                    st.error("서비스 계정 설정이 올바르지 않습니다.")
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
                            except gspread.exceptions.APIError as e:
                                error_message = str(e)
                                if "404" in error_message:
                                    st.error("스프레드시트를 찾을 수 없습니다.")
                                    return None
                                elif "403" in error_message:
                                    st.error("스프레드시트 접근 권한이 없습니다.")
                                    return None
                                else:
                                    raise
                        
                        # 워크시트 확인 및 생성
                        worksheet_list = sheet.worksheets()
                        worksheet_names = [ws.title for ws in worksheet_list]
                        
                        # problems 워크시트 확인
                        if "problems" not in worksheet_names:
                            st.error("문제 데이터를 찾을 수 없습니다.")
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
                            except Exception as ws_error:
                                st.error("답안 저장소 생성에 실패했습니다.")
                                return None

                        # student_weaknesses 워크시트 확인 및 생성
                        if "student_weaknesses" not in worksheet_names:
                            try:
                                weaknesses_ws = sheet.add_worksheet("student_weaknesses", 1000, 5)
                                weaknesses_ws.append_row([
                                    "학생ID",
                                    "키워드",
                                    "시도횟수",
                                    "정답횟수",
                                    "마지막시도"
                                ])
                            except Exception as ws_error:
                                st.error("취약점 저장소 생성에 실패했습니다.")
                                # 계속 진행 (없으면 추천 기능만 작동 안함)
                        
                        return sheet
                        
                    except Exception as e:
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            time.sleep(1)  # 1초 대기
                            continue
                        st.error("스프레드시트 연결에 실패했습니다.")
                        return None
                    
                except Exception as auth_error:
                    st.error("인증에 실패했습니다.")
                    return None
                    
            except Exception as e:
                st.error("서비스 계정 설정에 문제가 있습니다.")
                return None
        
        except Exception as e:
            if retry_count < max_retries - 1:
                retry_count += 1
                time.sleep(1)  # 1초 대기
                continue
            st.error("연결에 실패했습니다.")
            return None

    return None

def get_worksheet_records(worksheet, limit=None):
    """
    워크시트에서 레코드를 가져오는 래퍼 함수입니다.
    gspread 버전 호환성 문제를 해결합니다.
    """
    try:
        # 최신 버전의 gspread는 limit 매개변수를 지원하지 않을 수 있음
        if limit is not None:
            try:
                # 최신 버전은 limit 대신 end 파라미터를 사용할 수 있음
                records = worksheet.get_all_records(end=limit+1)  # 헤더 행 + limit
                return records[:limit]
            except TypeError:
                # 이전 버전의 경우 limit 파라미터를 시도 
                try:
                    return worksheet.get_all_records(limit=limit)
                except:
                    # 모든 레코드를 가져온 후 자르는 대체 방법
                    records = worksheet.get_all_records()
                    return records[:limit] if limit else records
        else:
            # limit 없이 모든 레코드 가져오기
            return worksheet.get_all_records()
    except Exception as e:
        print(f"워크시트 데이터 가져오기 오류: {e}")
        return []

def get_student_weaknesses(student_id):
    """
    학생의 취약점(낮은 정답률을 보이는 키워드)을 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return {}
        
        try:
            # 학생 취약점 워크시트 가져오기
            try:
                weaknesses_ws = sheet.worksheet("student_weaknesses")
            except:
                # 취약점 워크시트가 없으면 빈 데이터 반환
                return {}
            
            # 모든 데이터 가져오기
            all_records = weaknesses_ws.get_all_records()
            
            # 해당 학생의 데이터만 필터링
            student_records = [record for record in all_records if record["학생ID"] == student_id]
            
            # 키워드별 취약점 계산 (정답률 기준)
            weaknesses = {}
            for record in student_records:
                keyword = record["키워드"]
                attempts = record["시도횟수"]
                correct = record["정답횟수"]
                
                if attempts > 0:
                    accuracy = correct / attempts
                    # 정답률이 낮을수록 취약점 점수가 높음 (0~1 사이 값)
                    weakness_score = 1 - accuracy
                    weaknesses[keyword] = {
                        "시도횟수": attempts,
                        "정답횟수": correct,
                        "정답률": accuracy,
                        "취약도": weakness_score
                    }
            
            return weaknesses
            
        except Exception as e:
            print(f"취약점 데이터 가져오기 오류: {e}")
            return {}
            
    except Exception as e:
        print(f"취약점 데이터 가져오기 오류: {e}")
        return {}

def update_student_weakness(student_id, keyword, is_correct):
    """
    학생의 취약점 데이터를 업데이트합니다.
    """
    if not keyword:
        return False  # 키워드가 없으면 업데이트하지 않음
    
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False
        
        try:
            # 취약점 워크시트 가져오기
            try:
                weaknesses_ws = sheet.worksheet("student_weaknesses")
            except:
                # 워크시트가 없으면 생성
                weaknesses_ws = sheet.add_worksheet("student_weaknesses", 1000, 5)
                weaknesses_ws.append_row([
                    "학생ID",
                    "키워드",
                    "시도횟수",
                    "정답횟수",
                    "마지막시도"
                ])
            
            # 모든 데이터 가져오기
            all_data = weaknesses_ws.get_all_values()
            header = all_data[0]
            
            # 필요한 인덱스 찾기
            student_id_idx = header.index("학생ID")
            keyword_idx = header.index("키워드")
            attempts_idx = header.index("시도횟수")
            correct_idx = header.index("정답횟수")
            last_try_idx = header.index("마지막시도")
            
            # 해당 학생 및 키워드 레코드 찾기
            row_idx = None
            for i, row in enumerate(all_data[1:], start=2):  # 헤더 제외, 1-indexed
                if row[student_id_idx] == student_id and row[keyword_idx] == keyword:
                    row_idx = i
                    break
            
            # 현재 시간
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if row_idx:
                # 기존 데이터 업데이트
                current_attempts = int(all_data[row_idx-1][attempts_idx])
                current_correct = int(all_data[row_idx-1][correct_idx])
                
                # 새 데이터 계산
                new_attempts = current_attempts + 1
                new_correct = current_correct + (1 if is_correct else 0)
                
                # 셀 업데이트
                weaknesses_ws.update_cell(row_idx, attempts_idx + 1, new_attempts)
                weaknesses_ws.update_cell(row_idx, correct_idx + 1, new_correct)
                weaknesses_ws.update_cell(row_idx, last_try_idx + 1, current_time)
            else:
                # 새 레코드 추가
                weaknesses_ws.append_row([
                    student_id,
                    keyword,
                    1,  # 첫 번째 시도
                    1 if is_correct else 0,  # 정답 여부
                    current_time
                ])
            
            return True
            
        except Exception as e:
            print(f"취약점 데이터 업데이트 오류: {e}")
            return False
            
    except Exception as e:
        print(f"취약점 데이터 업데이트 오류: {e}")
        return False

def get_random_problem(student_id=None, student_grade=None, problem_type=None):
    """
    Google Sheets에서 문제를 무작위로 가져옵니다.
    student_id가 제공되면 학생 취약점 기반으로 문제를 가져옵니다.
    student_grade가 제공되면 해당 학년에 맞는 문제만 필터링합니다.
    problem_type이 제공되면 해당 유형의 문제만 필터링합니다.
    """
    # Google Sheets 연결
    sheet = connect_to_sheets()
    if not sheet:
        return get_dummy_problem(student_grade)
    
    try:
        # 학생 취약점 정보 가져오기
        student_weaknesses = None
        if student_id:
            try:
                student_weaknesses_ws = sheet.worksheet("student_weaknesses")
                all_weaknesses = student_weaknesses_ws.get_all_records()
                student_weaknesses = [w for w in all_weaknesses if w.get("학생ID") == student_id]
            except:
                # 취약점 정보 없음 - 무시하고 계속 진행
                pass
        
        # 문제 목록 가져오기
        problems_ws = sheet.worksheet("problems")
        all_problems = problems_ws.get_all_records()
        
        print(f"총 {len(all_problems)}개의 문제를 시트에서 로드했습니다.")
        
        # 학생 학년 정규화
        normalized_student_grade = ""
        if student_grade:
            normalized_student_grade = normalize_grade(student_grade)
        
        # 유효한 문제만 필터링 (필수 필드 확인)
        valid_problems = []
        problem_types_found = set()
        
        for p in all_problems:
            if "문제ID" in p and "문제내용" in p and "정답" in p:
                # 학년 필터링 - 학생 학년이 제공된 경우
                if student_grade and normalized_student_grade:
                    # 문제 학년 정규화
                    problem_grade = p.get("학년", "")
                    normalized_problem_grade = normalize_grade(problem_grade)
                    
                    # 학년이 다르면 건너뛰기 (정규화된 형태로 비교)
                    if not normalized_problem_grade or normalized_problem_grade != normalized_student_grade:
                        continue
                
                # 문제 유형 필터링 - 문제 유형이 제공된 경우
                if problem_type and p.get("문제유형") != problem_type:
                    continue  # 문제 유형이 다르면 건너뛰기
                
                # 문제 유형 기록 (디버깅 및 다양성 확인용)
                current_type = p.get("문제유형", "기타")
                problem_types_found.add(current_type)
                
                # 보기 정보 포맷팅 - 반드시 보기 정보를 올바르게 구성
                if "보기정보" not in p or not p["보기정보"]:
                    p["보기정보"] = {}
                    for i in range(1, 6):
                        option_key = f"보기{i}"
                        if option_key in p and p[option_key] and p[option_key].strip():
                            p["보기정보"][option_key] = p[option_key].strip()
                
                # 객관식인 경우 보기가 잘 설정되었는지 확인
                if p.get("문제유형") == "객관식" and (not p.get("보기정보") or len(p.get("보기정보", {})) < 2):
                    print(f"유효하지 않은 객관식 문제를 건너뜁니다. 문제ID: {p.get('문제ID')} (보기 부족)")
                    continue
                
                valid_problems.append(p)
        
        print(f"유효한 문제 {len(valid_problems)}개를 찾았습니다. 문제 유형: {sorted(problem_types_found)}")
        
        # 유효한 문제가 없으면 더미 문제 반환
        if not valid_problems:
            print(f"학년 {normalized_student_grade}에 맞는 문제가 없습니다. 더미 문제 생성.")
            return get_dummy_problem(student_grade)
        
        # 취약점 기반 문제 선택 또는 무작위 선택
        if student_weaknesses and len(student_weaknesses) > 0:
            # 학생 취약점 정보로부터 가중치 계산
            keyword_weights = {}
            for weakness in student_weaknesses:
                keyword = weakness.get("키워드", "")
                if keyword:
                    correct_rate = weakness.get("정답횟수", 0) / max(1, weakness.get("시도횟수", 1)) * 100
                    # 정답률이 낮을수록 높은 가중치 (취약할수록 자주 출제)
                    weight = max(1, 100 - correct_rate)
                    keyword_weights[keyword] = weight
            
            # 각 문제에 가중치 할당
            weighted_problems = []
            for p in valid_problems:
                problem_keywords = p.get("키워드", "").split(",")
                problem_weight = 1  # 기본 가중치
                
                for keyword in problem_keywords:
                    keyword = keyword.strip()
                    if keyword in keyword_weights:
                        problem_weight = max(problem_weight, keyword_weights[keyword])
                
                # 문제와 가중치를 함께 저장
                weighted_problems.append((p, problem_weight))
            
            # 가중치 기반 랜덤 선택
            total_weight = sum(w for _, w in weighted_problems)
            if total_weight > 0:
                r = random.uniform(0, total_weight)
                current_weight = 0
                for problem, weight in weighted_problems:
                    current_weight += weight
                    if r <= current_weight:
                        return problem
            
            # 가중치 선택 실패 시 그냥 무작위로 선택
            return random.choice(valid_problems)
        else:
            # 취약점 정보가 없으면 무작위로 선택
            return random.choice(valid_problems)
    
    except Exception as e:
        # 오류 발생 시 더미 문제 반환
        print(f"문제 로드 오류: {str(e)}")
        return get_dummy_problem(student_grade)

def normalize_grade(grade_str):
    """
    학년 문자열을 표준 형식(중1, 중2, 중3, 고1, 고2, 고3)으로 정규화합니다.
    """
    if not grade_str:
        return ""
    
    # 문자열 정리
    normalized = grade_str.replace("학년", "").strip()
    
    # 학교급 처리
    if "중학교" in grade_str or "중" in grade_str:
        grade_prefix = "중"
    elif "고등학교" in grade_str or "고" in grade_str:
        grade_prefix = "고"
    else:
        # 학교급 정보가 없으면 중학교로 가정
        grade_prefix = "중"
    
    # 학년 숫자 추출
    grade_number = None
    for char in normalized:
        if char.isdigit():
            grade_number = char
            break
    
    # 학년 숫자가 1~3이 아니면 기본값 1로 설정
    if grade_number not in ["1", "2", "3"]:
        grade_number = "1"
    
    # 정규화된 형식 반환
    return f"{grade_prefix}{grade_number}"

def save_student_answer(student_id, student_name, problem_id, submitted_answer, score, feedback):
    """
    학생이 제출한 답안을 Google Sheets에 저장합니다.
    또한 문제의 키워드에 대한 취약점 정보도 업데이트합니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False
        
        try:
            # 답안 워크시트 가져오기
            try:
                answers_ws = sheet.worksheet("student_answers")
            except:
                # 워크시트가 없으면 생성
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
            
            # 현재 시간
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 답안 저장
            answers_ws.append_row([
                student_id,
                student_name,
                problem_id,
                submitted_answer,
                score,
                feedback,
                current_time
            ])
            
            # 취약점 업데이트를 위해 문제 정보 가져오기
            try:
                problems_ws = sheet.worksheet("problems")
                problems = problems_ws.get_all_records()
                
                # 해당 문제 찾기
                problem = None
                for p in problems:
                    if p["문제ID"] == problem_id:
                        problem = p
                        break
                
                # 키워드 기반 취약점 업데이트
                if problem and "키워드" in problem and problem["키워드"]:
                    keywords = [k.strip() for k in problem["키워드"].split(',')]
                    for keyword in keywords:
                        is_correct = (score == 100)  # 100점이면 정답으로 간주
                        update_student_weakness(student_id, keyword, is_correct)
            except Exception as e:
                # 취약점 업데이트 실패해도 답안 저장은 성공으로 처리
                print(f"취약점 업데이트 오류: {e}")
                pass
            
            return True
            
        except Exception as e:
            print(f"답안 저장 오류: {e}")
            return False
            
    except Exception as e:
        print(f"답안 저장 오류: {e}")
        return False

def get_student_performance(student_id):
    """
    학생의 성적 데이터를 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return None
        
        try:
            # 답안 워크시트 가져오기
            try:
                answers_ws = sheet.worksheet("student_answers")
                all_answers = answers_ws.get_all_records()
            except:
                return None
            
            # 해당 학생의 답안만 필터링
            student_answers = [answer for answer in all_answers if answer["학생ID"] == student_id]
            
            if not student_answers:
                return None
            
            # 성적 통계 계산
            total_problems = len(student_answers)
            correct_answers = sum(1 for answer in student_answers if answer["점수"] == 100)
            incorrect_answers = total_problems - correct_answers
            
            # 정답률 계산
            if total_problems > 0:
                accuracy = (correct_answers / total_problems) * 100
            else:
                accuracy = 0
            
            # 최근 10개 문제의 정답률 추이
            recent_answers = sorted(student_answers, key=lambda x: x["제출시간"], reverse=True)[:10]
            recent_trend = [1 if answer["점수"] == 100 else 0 for answer in recent_answers]
            
            # 결과 데이터
            performance = {
                "total_problems": total_problems,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers,
                "accuracy": accuracy,
                "recent_trend": recent_trend
            }
            
            # 취약점 정보 추가
            weaknesses = get_student_weaknesses(student_id)
            if weaknesses:
                # 취약점이 높은 순으로 정렬
                sorted_weaknesses = sorted(weaknesses.items(), key=lambda x: x[1]["취약도"], reverse=True)
                performance["weaknesses"] = sorted_weaknesses
            
            return performance
            
        except Exception as e:
            print(f"성적 데이터 가져오기 오류: {e}")
            return None
            
    except Exception as e:
        print(f"성적 데이터 가져오기 오류: {e}")
        return None

def get_dummy_problem(student_grade="중학교 1학년"):
    """
    구글 시트 연결 실패 시 샘플 문제를 반환합니다.
    학생 학년에 맞는 더미 문제를 생성합니다.
    """
    # 학년 정보 정규화
    full_grade = normalize_grade(student_grade)
    if not full_grade:
        full_grade = "중1"  # 기본값
    
    # 학교급과 학년 구분
    grade_prefix = full_grade[0]  # 중 또는 고
    grade_level = full_grade[1]   # 1, 2, 또는 3
    
    # 다양한 문제 유형 생성을 위한 랜덤 선택
    problem_type = random.choice(["객관식", "단답형"])
    
    # 학년별 다른 문제 내용 생성
    if grade_prefix == "중":
        if grade_level == "1":
            if problem_type == "객관식":
                question = "Which verb best completes the sentence: My parents ___ the article?"
                options = {
                    "보기1": "analyze",
                    "보기2": "analyzes",
                    "보기3": "analyzing",
                    "보기4": "analyzed",
                    "보기5": "to analyze"
                }
                answer = "보기1"
                explanation = "주어가 '부모님(My parents)'으로 복수형이므로, 복수형 동사 'analyze'가 정답입니다."
            else:
                question = "What is the past tense of the verb 'swim'?"
                options = {}
                answer = "swam"
                explanation = "'swim'의 과거형은 'swam'입니다."
        elif grade_level == "2":
            if problem_type == "객관식":
                question = "Choose the correct form: If I ___ rich, I would buy a new car."
                options = {
                    "보기1": "am",
                    "보기2": "was",
                    "보기3": "were",
                    "보기4": "be",
                    "보기5": "being"
                }
                answer = "보기3"
                explanation = "가정법 과거에서는 'If I were...'의 형태를 사용합니다."
            else:
                question = "What is the comparative form of the adjective 'good'?"
                options = {}
                answer = "better"
                explanation = "'good'의 비교급은 'better'입니다."
        else:  # 중3
            if problem_type == "객관식":
                question = "Complete the sentence: She has been studying English ___ three years."
                options = {
                    "보기1": "since",
                    "보기2": "for",
                    "보기3": "during",
                    "보기4": "in",
                    "보기5": "within"
                }
                answer = "보기2"
                explanation = "특정 기간을 나타낼 때는 'for'를 사용합니다."
            else:
                question = "What is the superlative form of the adjective 'far'?"
                options = {}
                answer = "farthest"
                explanation = "'far'의 최상급은 'farthest'입니다."
    else:  # 고등학교
        if grade_level == "1":
            if problem_type == "객관식":
                question = "Choose the expression that best completes the dialogue: A: I'm so tired. B: ___"
                options = {
                    "보기1": "So do I.",
                    "보기2": "So am I.",
                    "보기3": "Neither am I.",
                    "보기4": "Neither do I.",
                    "보기5": "So I am."
                }
                answer = "보기2"
                explanation = "상대방의 상태에 대해 동의할 때는 'So + 조동사/be동사 + 주어'를 사용합니다."
            else:
                question = "What is the past participle of the verb 'break'?"
                options = {}
                answer = "broken"
                explanation = "'break'의 과거분사는 'broken'입니다."
        elif grade_level == "2":
            if problem_type == "객관식":
                question = "Fill in the blank: In spite of ___ late, he arrived at the meeting on time."
                options = {
                    "보기1": "leave",
                    "보기2": "leaving",
                    "보기3": "to leave",
                    "보기4": "left",
                    "보기5": "to be left"
                }
                answer = "보기2"
                explanation = "'In spite of' 다음에는 명사나 동명사가 옵니다."
            else:
                question = "What is the passive voice of 'They are building a new school'?"
                options = {}
                answer = "A new school is being built"
                explanation = "능동태문장 'They are building a new school'의 수동태는 'A new school is being built'입니다."
        else:  # 고3
            if problem_type == "객관식":
                question = "Select the word that does NOT belong with the others:"
                options = {
                    "보기1": "collaborate",
                    "보기2": "cooperate",
                    "보기3": "participate",
                    "보기4": "compete",
                    "보기5": "coordinate"
                }
                answer = "보기4"
                explanation = "'compete'는 '경쟁하다'라는 의미로, 다른 단어들('함께 일하다', '협력하다', '참여하다')과 의미가 다릅니다."
            else:
                question = "What is the gerund form of the phrasal verb 'give up'?"
                options = {}
                answer = "giving up"
                explanation = "동명사 형태는 동사에 '-ing'를 붙이는데, 구동사인 경우 첫 번째 단어에만 '-ing'를 붙입니다."
    
    # 더미 문제 반환
    dummy_problem = {
        "문제ID": f"dummy-{uuid.uuid4()}",
        "과목": "영어",
        "학년": full_grade,  # 정규화된 학년 정보
        "문제유형": problem_type,
        "난이도": "중",
        "문제내용": question,
        "정답": answer,
        "키워드": "영어 문법",
        "해설": explanation
    }
    
    # 객관식인 경우만 보기 정보 추가
    if problem_type == "객관식" and options:
        dummy_problem["보기정보"] = options
    
    return dummy_problem

def save_student_result(student_id, student_name, student_grade, results):
    """
    학생 시험 결과를 학년별로 저장합니다.
    """
    # Google Sheets 연결
    sheet = connect_to_sheets()
    if not sheet:
        return False
    
    try:
        # 정규화된 학년 정보 추출
        normalized_grade = student_grade.replace("학년", "").strip()
        if "중학교" in student_grade or "중" in student_grade:
            if "1" in normalized_grade:
                worksheet_name = "중1_results"
            elif "2" in normalized_grade:
                worksheet_name = "중2_results"
            elif "3" in normalized_grade:
                worksheet_name = "중3_results"
            else:
                worksheet_name = "중1_results"  # 기본값
        elif "고등학교" in student_grade or "고" in student_grade:
            if "1" in normalized_grade:
                worksheet_name = "고1_results"
            elif "2" in normalized_grade:
                worksheet_name = "고2_results"
            elif "3" in normalized_grade:
                worksheet_name = "고3_results"
            else:
                worksheet_name = "고1_results"  # 기본값
        else:
            worksheet_name = "results"  # 일반 결과
        
        # 워크시트 존재 여부 확인 및 생성
        try:
            worksheet = sheet.worksheet(worksheet_name)
        except:
            # 워크시트가 없으면 새로 생성
            worksheet = sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
            # 헤더 추가
            headers = ["학생ID", "이름", "학년", "시험일시", "총문제수", "정답수", "정확도", "취약점"]
            worksheet.append_row(headers)
        
        # 현재 시간
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 결과 분석
        total_problems = results.get('total_problems', 0)
        correct_count = results.get('correct_count', 0)
        accuracy = results.get('accuracy', 0)
        
        # 틀린 문제 키워드 분석
        keywords_count = {}
        for problem_id, detail in results.get('details', {}).items():
            if not detail.get('is_correct', False):
                problem_data = st.session_state.student_answers.get(problem_id, {})
                if "키워드" in problem_data and problem_data["키워드"]:
                    keywords = problem_data["키워드"].split(",")
                    for keyword in keywords:
                        keyword = keyword.strip()
                        if keyword:
                            keywords_count[keyword] = keywords_count.get(keyword, 0) + 1
        
        # 주요 취약점 (상위 3개)
        weakness = ", ".join([f"{k}({v})" for k, v in sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)[:3]])
        
        # 결과 행 추가
        row = [student_id, student_name, student_grade, now, total_problems, correct_count, f"{accuracy:.1f}%", weakness]
        worksheet.append_row(row)
        
        return True
    except Exception as e:
        print(f"결과 저장 오류: {str(e)}")
        return False

def get_student_progress(student_id, student_grade):
    """
    학생의 학습 진행 상황과 성적 추이를 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return None
        
        try:
            # 학년별 결과 워크시트 확인
            worksheet_name = f"student_results_{student_grade}"
            worksheet_name = worksheet_name.replace(" ", "_").replace("학년", "").strip()
            
            try:
                results_ws = sheet.worksheet(worksheet_name)
                all_records = results_ws.get_all_records()
            except Exception as e:
                # 워크시트가 없으면 빈 데이터 반환
                return {"tests": [], "average_score": 0, "progress": []}
            
            # 해당 학생의 레코드만 필터링
            student_records = [r for r in all_records if r["학생ID"] == student_id]
            
            if not student_records:
                return {"tests": [], "average_score": 0, "progress": []}
            
            # 시험별 데이터 준비
            tests = []
            scores = []
            
            for record in student_records:
                # 날짜 포맷 변환
                try:
                    test_date = datetime.strptime(record["시험일시"], "%Y-%m-%d %H:%M:%S")
                    formatted_date = test_date.strftime("%m/%d")
                except:
                    formatted_date = "날짜 오류"
                
                # 점수 변환
                try:
                    score = float(record["총점"])
                except:
                    score = 0
                
                tests.append({
                    "date": formatted_date,
                    "score": score,
                    "accuracy": record.get("정답률", "0%").replace("%", ""),
                    "analysis": record.get("분석결과", "")
                })
                
                scores.append(score)
            
            # 평균 점수 계산
            average_score = sum(scores) / len(scores) if scores else 0
            
            # 성적 추이 (최대 10개)
            progress = [{"date": t["date"], "score": t["score"]} for t in tests[-10:]]
            
            return {
                "tests": tests,
                "average_score": average_score,
                "progress": progress
            }
            
        except Exception as e:
            print(f"학생 진행 상황 데이터 가져오기 오류: {e}")
            return None
            
    except Exception as e:
        print(f"학생 진행 상황 데이터 가져오기 오류: {e}")
        return None