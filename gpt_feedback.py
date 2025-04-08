import streamlit as st
import time
import google.generativeai as genai
from datetime import datetime

def generate_feedback(question, student_answer, correct_answer, explanation):
    """
    Gemini를 사용하여 학생의 답안을 채점하고 피드백을 생성합니다.
    """
    try:
        # API 키 확인
        if "GOOGLE_API_KEY" not in st.secrets:
            # 단답형 또는 객관식 여부 확인
            is_objective = correct_answer.startswith("보기")
            
            # 기본 채점 로직
            if is_objective:
                # 객관식: 정확히 일치해야 함
                is_correct = (student_answer == correct_answer)
            else:
                # 단답형: 대소문자 및 공백 무시하고 비교
                normalized_student = student_answer.lower().strip() if student_answer else ""
                normalized_correct = correct_answer.lower().strip()
                is_correct = (normalized_student == normalized_correct)
            
            score = 100 if is_correct else 0
            return score, "AI 튜터 연결에 실패했습니다. 기본 채점 결과만 제공됩니다."
        
        # Gemini API 키 설정
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # 단답형 또는 객관식 여부 확인
        is_objective = correct_answer.startswith("보기")
        
        # 프롬프트 구성
        if is_objective:
            # 객관식 문제 프롬프트
            prompt = f"""
            [문제]
            {question}

            [학생 답안]
            {student_answer}

            [정답]
            {correct_answer}

            [해설]
            {explanation}

            위 정보를 바탕으로 다음 작업을 수행해주세요:
            1. 학생의 답안이 정답인지 판단 (100점 또는 0점)
            2. 학생의 이해도를 파악하여 친절하고 자세한 피드백 제공
            3. 오답인 경우, 왜 틀렸는지 구체적으로 설명하고 학습 방향 제시
            4. 정답인 경우에도 개념을 더 깊이 이해할 수 있는 추가 설명 제공

            다음 형식으로 출력해주세요:
            점수: [점수]
            피드백: [피드백 내용]
            """
        else:
            # 단답형 문제 프롬프트
            prompt = f"""
            [문제]
            {question}

            [학생 답안]
            {student_answer}

            [정답]
            {correct_answer}

            [해설]
            {explanation}

            위 정보를 바탕으로 다음 작업을 수행해주세요:
            1. 학생의 답안이 정답과 일치하는지 판단하세요. 대소문자, 앞뒤 공백은 무시하고 채점합니다.
            2. 답안이 완전히 일치하면 100점, 그렇지 않으면 0점을 부여합니다.
            3. 학생의 답안에 대한 구체적인 피드백을 제공하세요.
            4. 오답인 경우, 왜 틀렸는지 설명하고 학습 방향을 제시하세요.
            5. 정답인 경우에도 개념 이해를 돕는 추가 설명을 제공하세요.

            다음 형식으로 출력해주세요:
            점수: [점수]
            피드백: [피드백 내용]
            """

        # Gemini API 호출
        try:
            # 모델 생성
            model = genai.GenerativeModel('gemini-pro')
            
            # API 호출
            response = model.generate_content(prompt)
            
            # 응답 파싱
            output = response.text
        except Exception as api_error:
            # API 호출 실패 시 기본 응답 생성
            print(f"Gemini API 호출 실패: {api_error}")
            if is_objective:
                # 객관식: 정확히 일치해야 함
                is_correct = (student_answer == correct_answer)
            else:
                # 단답형: 대소문자 및 공백 무시하고 비교
                normalized_student = student_answer.lower().strip() if student_answer else ""
                normalized_correct = correct_answer.lower().strip()
                is_correct = (normalized_student == normalized_correct)
            
            score = 100 if is_correct else 0
            
            if score == 100:
                return 100, "정답입니다! (API 호출 실패로 기본 피드백만 제공됩니다)"
            else:
                return 0, "틀렸습니다. (API 호출 실패로 기본 피드백만 제공됩니다)"
        
        try:
            # 점수와 피드백 분리
            score_line = [line for line in output.split('\n') if line.startswith('점수:')]
            if not score_line:
                # 점수 라인을 찾지 못하면 기본 채점 로직 사용
                if is_objective:
                    is_correct = (student_answer == correct_answer)
                else:
                    normalized_student = student_answer.lower().strip() if student_answer else ""
                    normalized_correct = correct_answer.lower().strip()
                    is_correct = (normalized_student == normalized_correct)
                
                score = 100 if is_correct else 0
                
                if '정답' in output.lower() and '틀' not in output.lower():
                    score = 100
                elif '틀' in output.lower():
                    score = 0
            else:
                score_line = score_line[0]
                score = 100 if '100' in score_line else 0
            
            feedback_lines = [line for line in output.split('\n') if not line.startswith('점수:')]
            feedback = '\n'.join(feedback_lines).replace('피드백:', '').strip()
            
            return score, feedback
            
        except Exception as parse_error:
            # 응답 파싱 실패 시 기본 응답 생성
            # 단답형 또는 객관식 여부에 따라 다른 기본 채점 로직 적용
            if is_objective:
                # 객관식: 정확히 일치해야 함
                is_correct = (student_answer == correct_answer)
            else:
                # 단답형: 대소문자 및 공백 무시하고 비교
                normalized_student = student_answer.lower().strip() if student_answer else ""
                normalized_correct = correct_answer.lower().strip()
                is_correct = (normalized_student == normalized_correct)
            
            score = 100 if is_correct else 0
            
            if score == 100:
                return 100, "정답입니다! 해설을 읽고 개념을 더 깊이 이해해보세요."
            else:
                return 0, "틀렸습니다. 해설을 잘 읽고 다시 한 번 풀어보세요."
        
    except Exception as e:
        print(f"피드백 생성 중 오류: {e}")
        # 단답형 또는 객관식 여부에 따라 다른 기본 채점 로직 적용
        is_objective = correct_answer.startswith("보기")
        if is_objective:
            # 객관식: 정확히 일치해야 함
            is_correct = (student_answer == correct_answer)
        else:
            # 단답형: 대소문자 및 공백 무시하고 비교
            normalized_student = student_answer.lower().strip() if student_answer else ""
            normalized_correct = correct_answer.lower().strip()
            is_correct = (normalized_student == normalized_correct)
        
        score = 100 if is_correct else 0
        
        if score == 100:
            return 100, "정답입니다! (AI 튜터 연결에 문제가 있어 기본 채점 결과만 제공됩니다)"
        else:
            return 0, "틀렸습니다. (AI 튜터 연결에 문제가 있어 기본 채점 결과만 제공됩니다)" 