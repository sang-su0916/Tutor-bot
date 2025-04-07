import openai
import streamlit as st
import os

def get_openai_client():
    """
    OpenAI API 클라이언트를 생성하고 반환합니다.
    """
    try:
        # 환경변수에서 API 키 가져오기
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # 환경변수에 없으면 Streamlit secrets에서 시도
            api_key = st.secrets.get("OPENAI_API_KEY")
            
        if not api_key:
            st.error("OpenAI API 키가 설정되지 않았습니다.")
            return None
            
        client = openai.OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"OpenAI API 클라이언트 생성 오류: {e}")
        return None

def generate_feedback(problem_content, student_answer, correct_answer, explanation):
    """
    GPT를 사용하여 학생 답변에 대한 채점 및 피드백을 생성합니다.
    
    Args:
        problem_content (str): 문제 내용
        student_answer (str): 학생의 답변 (예: '보기1', '보기2', 등)
        correct_answer (str): 정답 (예: '보기1', '보기2', 등)
        explanation (str): 문제 해설
        
    Returns:
        tuple: (점수, 피드백) - 점수는 0~100 사이의 정수, 피드백은 문자열
    """
    try:
        client = get_openai_client()
        if not client:
            return None, "API 연결 오류로 채점을 완료할 수 없습니다."
        
        # 프롬프트 구성
        prompt = f"""
        ## 문제
        {problem_content}
        
        ## 학생 답안
        {student_answer}
        
        ## 정답
        {correct_answer}
        
        ## 문제 해설
        {explanation}
        
        ---
        
        위 정보를 바탕으로 학생의 답안을 채점하고 교육적인 피드백을 제공해주세요.
        학생이 선택한 답안이 정답과 일치하면 100점, 그렇지 않으면 0점을 부여합니다.
        점수와 함께 학생에게 도움이 될 구체적인 설명을 포함하세요.
        
        응답 형식:
        점수: [0 또는 100]
        피드백: [학생을 위한 교육적인 피드백]
        """
        
        # GPT API 호출
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "당신은 학생들에게 도움이 되는 교육적인 피드백을 제공하는 영어 교사입니다."},
                      {"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500
        )
        
        # 응답 텍스트 추출
        response_text = response.choices[0].message.content.strip()
        
        # 점수와 피드백 분리
        lines = response_text.split('\n')
        score_line = next((line for line in lines if line.startswith('점수:')), None)
        
        if score_line:
            # 점수 추출 및 정수로 변환
            try:
                score = int(score_line.split(':')[1].strip())
            except:
                score = 100 if student_answer == correct_answer else 0
        else:
            score = 100 if student_answer == correct_answer else 0
        
        # 피드백 추출 (점수 라인 이후의 모든 텍스트)
        feedback_start = next((i for i, line in enumerate(lines) if line.startswith('피드백:')), None)
        
        if feedback_start is not None:
            feedback = '\n'.join(lines[feedback_start:]).replace('피드백:', '').strip()
        else:
            feedback = '\n'.join(lines).strip()
        
        return score, feedback
        
    except Exception as e:
        st.error(f"GPT 피드백 생성 오류: {e}")
        # 오류 발생 시 기본 피드백 제공
        if student_answer == correct_answer:
            return 100, "정답입니다! 더 자세한 피드백은 현재 제공할 수 없습니다."
        else:
            return 0, f"오답입니다. 정답은 {correct_answer}입니다. 더 자세한 피드백은 현재 제공할 수 없습니다." 