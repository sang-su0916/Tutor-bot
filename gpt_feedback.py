import openai
import streamlit as st
import time
from datetime import datetime

def generate_feedback(question, student_answer, correct_answer, explanation):
    """
    GPT를 사용하여 학생의 답안을 채점하고 피드백을 생성합니다.
    """
    try:
        # API 키 확인
        if "OPENAI_API_KEY" not in st.secrets:
            return 0 if student_answer != correct_answer else 100, "AI 튜터 연결에 실패했습니다. 기본 채점 결과만 제공됩니다."
        
        # OpenAI API 키 설정
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        
        # 프롬프트 구성
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

        # API 호출
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 학생들의 답안을 채점하고 친절한 피드백을 제공하는 AI 튜터입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            request_timeout=30
        )

        # 응답 파싱
        output = response.choices[0].message.content.strip()
        
        try:
            # 점수와 피드백 분리
            score_line = [line for line in output.split('\n') if line.startswith('점수:')][0]
            score = 100 if '100' in score_line else 0
            
            feedback_lines = [line for line in output.split('\n') if not line.startswith('점수:')]
            feedback = '\n'.join(feedback_lines).replace('피드백:', '').strip()
            
            return score, feedback
            
        except Exception as parse_error:
            # 응답 파싱 실패 시 기본 응답 생성
            if student_answer == correct_answer:
                return 100, "정답입니다! 해설을 읽고 개념을 더 깊이 이해해보세요."
            else:
                return 0, "틀렸습니다. 해설을 잘 읽고 다시 한 번 풀어보세요."
        
    except openai.error.RateLimitError:
        # API 사용량 초과
        if student_answer == correct_answer:
            return 100, "정답입니다! (AI 서버가 혼잡하여 상세 피드백은 잠시 후에 확인해주세요)"
        else:
            return 0, "틀렸습니다. (AI 서버가 혼잡하여 상세 피드백은 잠시 후에 확인해주세요)"
        
    except openai.error.AuthenticationError:
        # 인증 오류
        if student_answer == correct_answer:
            return 100, "정답입니다! (AI 튜터 연결에 문제가 있어 기본 채점 결과만 제공됩니다)"
        else:
            return 0, "틀렸습니다. (AI 튜터 연결에 문제가 있어 기본 채점 결과만 제공됩니다)"
        
    except openai.error.APIError:
        # API 오류
        if student_answer == correct_answer:
            return 100, "정답입니다! (일시적인 오류로 기본 채점 결과만 제공됩니다)"
        else:
            return 0, "틀렸습니다. (일시적인 오류로 기본 채점 결과만 제공됩니다)"
        
    except Exception as e:
        # 기타 오류
        if student_answer == correct_answer:
            return 100, "정답입니다! (피드백 생성에 실패하여 기본 채점 결과만 제공됩니다)"
        else:
            return 0, "틀렸습니다. (피드백 생성에 실패하여 기본 채점 결과만 제공됩니다)" 