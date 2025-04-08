import streamlit as st
import pandas as pd
import random
from datetime import datetime
import time
from sheets_utils import connect_to_sheets

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
    if not keyword or not student_id:
        return False  # 키워드나 학생ID가 없으면 업데이트하지 않음
    
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

def get_problem_for_student(student_id, available_problems):
    """
    학생의 취약점을 기반으로 적절한 문제를 추천합니다.
    - student_id: 학생 ID
    - available_problems: 사용 가능한 문제 목록
    """
    if not available_problems:
        return None
    
    import random
    
    # 학생의 취약점 데이터 가져오기
    weaknesses = get_student_weaknesses(student_id)
    
    # 충분한 데이터가 있는지 확인 (최소 5개 이상의 키워드에 대한 데이터가 있어야 함)
    sufficient_data = len(weaknesses) >= 5 and sum(1 for _, data in weaknesses.items() if data['total'] >= 3) >= 3
    
    # 초기 데이터 수집 단계 (다양한 유형의 문제 제공)
    if not sufficient_data:
        # 다양한 키워드가 있는 문제들을 우선적으로 제공
        problems_by_keyword = {}
        
        # 문제를 키워드별로 분류
        for problem in available_problems:
            keywords = problem.get("키워드", "").split(",")
            keywords = [k.strip() for k in keywords if k.strip()]
            
            for keyword in keywords:
                if keyword not in problems_by_keyword:
                    problems_by_keyword[keyword] = []
                problems_by_keyword[keyword].append(problem)
        
        # 학생이 아직 접하지 않은 키워드의 문제를 우선적으로 제공
        unseen_keywords = [k for k in problems_by_keyword.keys() if k not in weaknesses]
        
        if unseen_keywords:
            # 아직 접하지 않은 키워드 중 하나를 무작위로 선택
            selected_keyword = random.choice(unseen_keywords)
            problems = problems_by_keyword[selected_keyword]
            return random.choice(problems)
        else:
            # 모든 키워드를 이미 접했다면, 가장 적게 접한 키워드의 문제 제공
            keywords_count = {k: data['total'] for k, data in weaknesses.items()}
            min_count = min(keywords_count.values()) if keywords_count else 0
            least_seen_keywords = [k for k, count in keywords_count.items() if count == min_count]
            
            if least_seen_keywords:
                selected_keyword = random.choice(least_seen_keywords)
                # 해당 키워드가 있는 문제 필터링
                filtered_problems = [p for p in available_problems if selected_keyword in p.get("키워드", "").split(",")]
                if filtered_problems:
                    return random.choice(filtered_problems)
            
            # 위 조건이 충족되지 않으면 무작위 선택
            return random.choice(available_problems)
    
    # 충분한 데이터가 수집된 후 (취약점 기반 문제 제공)
    else:
        # 취약점 목록이 있으면 취약점 기반으로 문제 선택
        if weaknesses:
            # 확률적으로 취약점 기반 또는 무작위 선택
            if random.random() < 0.7:  # 70% 확률로 취약점 기반 문제 제공
                # 취약점 정도에 따라 가중치 부여
                weighted_keywords = []
                for keyword, data in weaknesses.items():
                    if data['total'] > 0:
                        # 틀린 비율이 높을수록 가중치 증가
                        weight = (data['total'] - data['correct']) / data['total']
                        # 최소 가중치 보장
                        weight = max(0.1, weight)
                        weighted_keywords.extend([keyword] * int(weight * 10))
                
                if weighted_keywords:
                    # 가중치에 따라 키워드 선택
                    selected_keyword = random.choice(weighted_keywords)
                    
                    # 해당 키워드가 있는 문제 필터링
                    filtered_problems = [p for p in available_problems if selected_keyword in p.get("키워드", "").split(",")]
                    
                    if filtered_problems:
                        return random.choice(filtered_problems)
            
            # 30% 확률로 무작위 문제 제공 (또는 위 조건이 충족되지 않은 경우)
            return random.choice(available_problems)
        else:
            # 취약점 데이터가 없으면 무작위 선택
            return random.choice(available_problems)

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

def update_problem_stats(student_id, problem_id, keywords, is_correct):
    """
    문제를 풀고 난 후 학생의 취약점 데이터를 업데이트합니다.
    """
    if not student_id or not problem_id:
        return False
    
    # 키워드가 있으면 각 키워드에 대해 취약점 업데이트
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(',')]
        for keyword in keyword_list:
            if keyword:
                update_student_weakness(student_id, keyword, is_correct)
        return True
    
    return False

def show_student_performance_dashboard(student_id, student_name, grade, level):
    """
    학생의 성적 대시보드를 보여줍니다.
    """
    st.title(f"{student_name} 학생의 학습 발전 현황")
    st.markdown(f"**학년**: {grade} | **실력등급**: {level}")
    
    # 성적 데이터 가져오기
    performance = get_student_performance(student_id)
    
    if not performance:
        st.info("아직 풀이한 문제가 없습니다. 문제를 풀고 다시 확인해주세요.")
        return
    
    # 두 개의 열로 주요 지표 표시
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("총 풀이 문제", performance["total_problems"])
        st.metric("정답 문제", performance["correct_answers"])
    
    with col2:
        st.metric("정답률", f"{performance['accuracy']:.1f}%")
        st.metric("오답 문제", performance["incorrect_answers"])
    
    # 취약점 정보 표시
    st.subheader("취약 영역 분석")
    
    if "weaknesses" in performance and performance["weaknesses"]:
        # 취약점 데이터를 표 형태로 변환
        weak_data = []
        for keyword, stats in performance["weaknesses"]:
            if stats["시도횟수"] >= 2:  # 최소 2번 이상 시도한 경우만 표시
                weak_data.append({
                    "키워드": keyword,
                    "시도 횟수": stats["시도횟수"],
                    "정답률": f"{stats['정답률']*100:.1f}%",
                    "취약도": f"{stats['취약도']*100:.1f}%"
                })
        
        if weak_data:
            # 취약도가 높은 순으로 정렬
            weak_df = pd.DataFrame(weak_data)
            st.dataframe(weak_df, use_container_width=True)
            
            # 상위 3개 취약점에 대한 추천
            st.subheader("중점 학습 추천")
            top_weaknesses = performance["weaknesses"][:3]
            
            for i, (keyword, stats) in enumerate(top_weaknesses, 1):
                if stats["취약도"] > 0.3:  # 취약도가 30% 이상인 경우만
                    st.markdown(f"**{i}. {keyword}** (정답률: {stats['정답률']*100:.1f}%)")
                    st.progress(1 - stats["정답률"])  # 정답률의 반대값으로 프로그레스 바 표시
        else:
            st.info("아직 충분한 데이터가 없습니다. 더 많은 문제를 풀어보세요.")
    else:
        st.info("아직 취약점 데이터가 없습니다. 더 많은 문제를 풀어보세요.")
    
    # 최근 문제 풀이 추이
    st.subheader("최근 풀이 추이")
    
    if "recent_trend" in performance and performance["recent_trend"]:
        # 최근 10개 문제의 정답/오답 표시
        trend_cols = st.columns(min(10, len(performance["recent_trend"])))
        
        for i, correct in enumerate(performance["recent_trend"]):
            with trend_cols[i]:
                if correct:
                    st.markdown("✅")
                else:
                    st.markdown("❌")
    else:
        st.info("아직 문제 풀이 기록이 없습니다.")
