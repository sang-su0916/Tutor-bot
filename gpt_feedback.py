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
            당신은 영어 교육 전문가이자 학생들에게 상세하고 유익한 피드백을 제공하는 교육 튜터입니다.
            
            [문제]
            {question}

            [학생 답안]
            {student_answer}

            [정답]
            {correct_answer}

            [해설]
            {explanation}

            위 정보를 바탕으로 다음과 같이 명확하고 교육적인 첨삭 피드백을 제공해주세요:

            1. 학생의 답안이 정답인지 오답인지 판단하고 점수(100점 또는 0점)를 부여하세요.
            2. 학생이 선택한 답안에 대해 상세한 분석을 제공하세요.
            3. 오답일 경우, 왜 틀렸는지 명확하게 설명하고 정답과의 차이점을 설명하세요.
            4. 해당 문제와 관련된 핵심 개념이나 문법 규칙을 설명하세요.
            5. 유사한 문제를 해결하기 위한 학습 전략이나 팁을 제공하세요.
            6. 학생의 이해도를 높이기 위한 추가 예제나 설명을 제공하세요.
            7. 격려와 동기부여의 메시지를 포함하세요.

            답변은 다음 형식으로 작성해주세요:
            점수: [100 또는 0]
            
            [첨삭 피드백 - 2-3문단의 상세한 내용]
            """
        else:
            # 단답형 문제 프롬프트
            prompt = f"""
            당신은 영어 교육 전문가이자 학생들에게 상세하고 유익한 피드백을 제공하는 교육 튜터입니다.
            
            [문제]
            {question}

            [학생 답안]
            {student_answer}

            [정답]
            {correct_answer}

            [해설]
            {explanation}

            위 정보를 바탕으로 다음과 같이 명확하고 교육적인 첨삭 피드백을 제공해주세요:

            1. 학생의 답안이 정답인지 오답인지 판단하세요. (대소문자, 앞뒤 공백은 무시하고 채점)
            2. 정답 여부에 따라 점수(100점 또는 0점)를 부여하세요.
            3. 학생의 답안에 대한 구체적인 분석을 제공하세요.
            4. 오답일 경우:
               - 왜 틀렸는지 명확하게 설명하세요
               - 정답과의 차이점을 상세히 분석하세요
               - 오답을 선택한 이유에 대한 가능한 오해를 설명하세요
            5. 해당 문제와 관련된 핵심 개념, 문법 규칙, 어휘 지식을 설명하세요.
            6. 이 개념을 더 잘 이해하기 위한 추가 예시나 연습 방법을 제안하세요.
            7. 격려와 동기부여의 메시지로 마무리하세요.

            답변은 다음 형식으로 작성해주세요:
            점수: [100 또는 0]
            
            [첨삭 피드백 - 2-3문단의 상세한 내용]
            """

        # Gemini API 호출
        try:
            # 모델 생성 - gemini-1.5-flash 모델 사용 (안정적인 모델)
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 800,
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ]
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
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