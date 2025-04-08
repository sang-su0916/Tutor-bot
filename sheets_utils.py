import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
from datetime import datetime
import os
import json
import time
import pandas as pd

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
    Google Sheets에서 문제를 가져옵니다.
    학생ID가 제공되면 취약점에 기반하여 문제를 추천합니다.
    학년과 문제유형을 지정하면 해당 조건에 맞는 문제만 가져옵니다.
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return get_dummy_problem(student_grade)

        try:
            # problems 워크시트에서 문제 가져오기
            try:
                problems_ws = sheet.worksheet("problems")
                all_data = problems_ws.get_all_records()
            except Exception as e:
                return get_dummy_problem(student_grade)

            # 데이터 확인 및 처리
            if not all_data:
                return get_dummy_problem(student_grade)

            # 필수 필드 확인
            required_fields = ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", 
                             "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "키워드", "해설"]

            # 유효한 문제만 필터링
            valid_problems = []
            for problem in all_data:
                # 필수 필드가 모두 있고 값이 비어있지 않은지 확인
                if all(field in problem and str(problem[field]).strip() for field in required_fields[:6]): # 보기는 선택적일 수 있음
                    # 정답과 해설은 필수
                    if "정답" in problem and str(problem["정답"]).strip() and "해설" in problem and str(problem["해설"]).strip():
                        valid_problems.append(problem)

            if not valid_problems:
                return get_dummy_problem(student_grade)

            # 학년으로 필터링 (학년이 제공된 경우)
            if student_grade and student_grade.strip():
                grade_filtered_problems = [p for p in valid_problems 
                                         if p["학년"] == student_grade or 
                                         p["학년"] == student_grade.replace("학년", "").strip() or
                                         p["학년"] == student_grade.replace("중", "중학교").strip() or
                                         p["학년"] == student_grade.replace("고", "고등학교").strip()]
                
                # 학년 필터링된 문제가 있으면 사용, 없으면 원래 문제 풀로 계속 진행
                if grade_filtered_problems:
                    valid_problems = grade_filtered_problems
            
            # 문제 유형으로 필터링 (유형이 제공된 경우)
            if problem_type and problem_type.strip():
                type_filtered_problems = [p for p in valid_problems if p["문제유형"] == problem_type]
                
                # 유형 필터링된 문제가 있으면 사용, 없으면 원래 문제로 계속 진행
                if type_filtered_problems:
                    valid_problems = type_filtered_problems

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

            # 취약점 기반 문제 선택
            current_problem = None
            
            # 학생 취약점 가져오기 (학생ID가 있는 경우)
            if student_id:
                from student_analytics import get_problem_for_student
                selected_problem = get_problem_for_student(student_id, available_problems)
                if selected_problem:
                    current_problem = selected_problem
            
            # 취약점 기반 선택이 되지 않았으면 일반 랜덤 선택
            if current_problem is None:
                max_attempts = 10  # 최대 시도 횟수
                
                for _ in range(max_attempts):
                    random_problem = random.choice(available_problems)
                    
                    # 이전 문제와 비교
                    if "current_problem" not in st.session_state or \
                        st.session_state.current_problem is None or \
                        random_problem["문제ID"] != st.session_state.current_problem.get("문제ID"):
                        current_problem = random_problem
                        break
                
                if current_problem is None:
                    current_problem = random.choice(available_problems)

            # 출제된 문제 ID 기록
            st.session_state.previous_problems.add(current_problem["문제ID"])
            
            # 문제 데이터 정리
            cleaned_problem = {
                "문제ID": current_problem["문제ID"],
                "과목": current_problem.get("과목", ""),
                "학년": current_problem.get("학년", ""),
                "문제유형": current_problem.get("문제유형", "객관식"),
                "난이도": current_problem.get("난이도", "중"),
                "문제내용": current_problem["문제내용"],
                "정답": current_problem["정답"],
                "키워드": current_problem.get("키워드", ""),
                "해설": current_problem["해설"]
            }
            
            # 보기 정보를 별도 딕셔너리로 구성
            cleaned_problem["보기정보"] = {}
            for i in range(1, 6):
                option_key = f"보기{i}"
                if option_key in current_problem and current_problem[option_key]:
                    cleaned_problem["보기정보"][option_key] = current_problem[option_key]
            
            return cleaned_problem
            
        except Exception as e:
            print(f"문제 가져오기 오류: {e}")
            return get_dummy_problem(student_grade)
            
    except Exception as e:
        print(f"문제 가져오기 오류: {e}")
        return get_dummy_problem(student_grade)

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

def get_dummy_problem(student_grade=None):
    """
    샘플 문제를 반환합니다. (Sheets 연결이 실패할 경우 사용)
    학년 정보가 제공된 경우, 해당 학년에 맞는 샘플 문제를 제공합니다.
    """
    # 학년 기본값 설정
    grade = "중1"
    if student_grade:
        grade = student_grade.replace("학년", "").strip()
    
    problem_templates = {
        "중1": {
            "문제내용": "Choose the correct verb form to complete the sentence: The students ___ homework every day.",
            "보기1": "do",
            "보기2": "does",
            "보기3": "doing",
            "보기4": "did",
            "보기5": "done",
            "정답": "보기1",
            "해설": "주어가 'The students'로 복수이므로 'do'가 정답입니다. 3인칭 단수 주어가 아닐 때는 기본형 do를 사용합니다."
        },
        "중2": {
            "문제내용": "Choose the correct sentence: Yesterday, I ___.",
            "보기1": "go to school",
            "보기2": "goes to school",
            "보기3": "went to school",
            "보기4": "going to school",
            "보기5": "gone to school",
            "정답": "보기3",
            "해설": "과거 시제를 사용해야 합니다. 'Yesterday'는 과거 시점을 나타내므로 'went'가 정답입니다."
        },
        "중3": {
            "문제내용": "Fill in the blank: If it ___ tomorrow, we will cancel the picnic.",
            "보기1": "rain",
            "보기2": "rains",
            "보기3": "rained",
            "보기4": "raining",
            "보기5": "is raining",
            "정답": "보기2",
            "해설": "조건절(If clause)에서 미래 시제는 현재형으로 표현합니다. 주어가 'it'이므로 3인칭 단수형 'rains'가 정답입니다."
        },
        "고1": {
            "문제내용": "Choose the correct sentence: By the time I arrived at the station, the train ___.",
            "보기1": "already left",
            "보기2": "has already left",
            "보기3": "had already left",
            "보기4": "was already left",
            "보기5": "would already left",
            "정답": "보기3",
            "해설": "대과거(past perfect) 시제가 필요한 문장입니다. 'By the time I arrived'는 과거의 한 시점을 나타내고, 그 전에 일어난 일은 'had + 과거분사'로 표현합니다."
        },
        "고2": {
            "문제내용": "Fill in the blank: She suggested that he ___ the offer.",
            "보기1": "accept",
            "보기2": "accepts",
            "보기3": "accepted",
            "보기4": "would accept",
            "보기5": "has accepted",
            "정답": "보기1",
            "해설": "suggest that 다음에는 (should) 동사원형을 사용하는 가정법 현재가 옵니다. 따라서 'accept'가 정답입니다."
        },
        "고3": {
            "문제내용": "Choose the appropriate expression: The project is behind schedule, ___.",
            "보기1": "so we need to catch up",
            "보기2": "but we have plenty of time",
            "보기3": "therefore we can take a break",
            "보기4": "however we should slow down",
            "보기5": "nevertheless it's completed on time",
            "정답": "보기1",
            "해설": "뒤에 이어지는 표현이 앞 문장의 논리적 결과여야 합니다. '프로젝트가 일정보다 뒤처져 있다'라는 상황에서는 '따라서 따라잡을 필요가 있다'가 가장 논리적인 결론입니다."
        }
    }
    
    # 학년에 맞는 템플릿 선택
    template = problem_templates.get(grade, problem_templates["중1"])
    
    return {
        "문제ID": f"dummy-{random.randint(1, 1000)}",
        "과목": "영어",
        "학년": grade,
        "문제유형": "객관식",
        "난이도": "중",
        "문제내용": template["문제내용"],
        "보기1": template["보기1"],
        "보기2": template["보기2"],
        "보기3": template["보기3"],
        "보기4": template["보기4"],
        "보기5": template["보기5"],
        "정답": template["정답"],
        "키워드": "동사 시제",
        "해설": template["해설"],
        "보기정보": {
            "보기1": template["보기1"],
            "보기2": template["보기2"],
            "보기3": template["보기3"],
            "보기4": template["보기4"],
            "보기5": template["보기5"]
        }
    }

def save_student_result(student_id, student_name, student_grade, exam_data):
    """
    학생의 시험 결과를 저장합니다. 학년별로 정리하여 누적 데이터를 관리합니다.
    
    - student_id: 학생 ID
    - student_name: 학생 이름
    - student_grade: 학생 학년
    - exam_data: 시험 결과 데이터 (정답률, 문제별 결과, 총점 등을 포함)
    """
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False
        
        # 현재 날짜 및 시간
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 학생 결과 워크시트 확인 (학년별로 구분)
            worksheet_name = f"student_results_{student_grade}"
            worksheet_name = worksheet_name.replace(" ", "_").replace("학년", "").strip()
            
            try:
                # 기존 워크시트가 있는지 확인
                results_ws = sheet.worksheet(worksheet_name)
            except Exception as e:
                # 워크시트가 없으면 생성
                results_ws = sheet.add_worksheet(worksheet_name, 1000, 9)
                results_ws.append_row([
                    "학생ID",
                    "이름",
                    "학년",
                    "시험일시",
                    "문제수",
                    "정답수",
                    "정답률",
                    "총점",
                    "분석결과"
                ])
            
            # 결과 데이터 준비
            correct_count = exam_data.get('correct_count', 0)
            total_problems = exam_data.get('total_problems', 0)
            accuracy = exam_data.get('accuracy', 0)
            total_score = exam_data.get('total_score', 0)
            
            # 틀린 문제 유형 분석
            wrong_problems = []
            for problem_id, details in exam_data.get('details', {}).items():
                if not details.get('is_correct', False):
                    problem_data = st.session_state.student_answers.get(problem_id, {})
                    wrong_problems.append({
                        "유형": problem_data.get('문제유형', ''),
                        "키워드": problem_data.get('키워드', '')
                    })
            
            # 취약점 분석
            weaknesses = get_student_weaknesses(student_id)
            weak_areas = []
            if weaknesses:
                sorted_weaknesses = sorted(weaknesses.items(), key=lambda x: x[1]["취약도"], reverse=True)
                weak_areas = [kw for kw, _ in sorted_weaknesses[:3]]
            
            # 분석 결과 생성
            analysis = f"취약 영역: {', '.join(weak_areas) if weak_areas else '없음'}"
            if wrong_problems:
                wrong_types = {}
                for p in wrong_problems:
                    ptype = p.get('유형', '')
                    if ptype:
                        wrong_types[ptype] = wrong_types.get(ptype, 0) + 1
                
                if wrong_types:
                    analysis += f" | 오답 유형: {', '.join([f'{t}({c}개)' for t, c in wrong_types.items()])}"
            
            # 시험 결과 추가
            results_ws.append_row([
                student_id,
                student_name,
                student_grade,
                current_time,
                total_problems,
                correct_count,
                f"{accuracy:.1f}%",
                total_score,
                analysis
            ])
            
            return True
            
        except Exception as e:
            print(f"학생 결과 저장 오류: {e}")
            return False
            
    except Exception as e:
        print(f"학생 결과 저장 오류: {e}")
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