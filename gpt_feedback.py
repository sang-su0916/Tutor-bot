import streamlit as st
import time
import google.generativeai as genai
from datetime import datetime

def generate_feedback(problem, student_answer, student_id="", student_name=""):
    """
    학생의 답변에 대한 피드백을 생성하는 함수
    
    Args:
        problem: 문제 정보 딕셔너리
        student_answer: 학생이 제출한 답변
        student_id: 학생 ID (선택)
        student_name: 학생 이름 (선택)
    
    Returns:
        tuple: (점수, 피드백 텍스트)
    """
    try:
        problem_type = problem.get("문제유형", "객관식")
        
        # 객관식 문제
        if problem_type == "객관식":
            prompt = f"""
            당신은 학생들에게 고품질의 교육적 피드백을 제공하는 교육 전문가 AI입니다. 항상 일관되고 상세한 피드백을 제공해야 합니다.
            
            ## 학생 정보
            {f'학생 ID: {student_id}' if student_id else ''}
            {f'학생 이름: {student_name}' if student_name else ''}
            
            ## 문제 정보
            과목: {problem.get('과목', '알 수 없음')}
            학년: {problem.get('학년', '알 수 없음')}
            난이도: {problem.get('난이도', '알 수 없음')}
            문제 유형: 객관식
            
            ## 문제 내용
            {problem.get('문제내용', '문제 내용 없음')}
            
            ## 보기
            {problem.get('보기정보', '보기 없음')}
            
            ## 학생 답변
            학생이 선택한 답: {student_answer}
            
            ## 정답
            정답: {problem.get('정답', '정답 없음')}
            
            ## 해설
            {problem.get('해설', '해설 없음')}
            
            ## 지시사항
            1. 학생의 답안을 평가하고 점수를 부여하세요 (맞았으면 100점, 틀렸으면 0점).
            2. 각 보기에 대해 왜 그것이 정답인지 또는 오답인지 상세히 분석하세요.
            3. 학생이 선택한 답변이 왜 맞았는지 또는 틀렸는지 구체적으로 설명하세요.
            4. 틀린 경우, 학생이 왜 그런 선택을 했을지 분석하고, 해당 개념을 더 잘 이해할 수 있는 방법을 제안하세요.
            5. 관련된 핵심 개념에 대한 간결하지만 명확한 설명을 제공하세요.
            6. 유사한 문제를 풀 때 도움이 될 문제 해결 전략을 제시하세요.
            7. 학생에게 격려와 동기부여 메시지를 포함하세요.
            8. 표, 단계별 설명 등 다양한 형식을 활용하여 이해하기 쉽게 설명하세요.
            
            ## 피드백 형식
            반드시 다음과 같은 형식으로 답변해주세요:
            
            ## 점수: [0 또는 100]
            
            ## 정답 분석
            [정답과 학생 답변에 대한 자세한 분석]
            
            ## 핵심 개념 설명
            [관련된 핵심 개념에 대한 명확한 설명]
            
            ## 학습 조언
            [앞으로의 학습에 도움이 될 구체적인 조언]
            
            ## 격려 메시지
            [학생에게 전하는 긍정적인 메시지]
            """
            
        # 주관식 문제
        else:
            prompt = f"""
            당신은 학생들에게 고품질의 교육적 피드백을 제공하는 교육 전문가 AI입니다. 항상 일관되고 상세한 피드백을 제공해야 합니다.
            
            ## 학생 정보
            {f'학생 ID: {student_id}' if student_id else ''}
            {f'학생 이름: {student_name}' if student_name else ''}
            
            ## 문제 정보
            과목: {problem.get('과목', '알 수 없음')}
            학년: {problem.get('학년', '알 수 없음')}
            난이도: {problem.get('난이도', '알 수 없음')}
            문제 유형: 주관식
            
            ## 문제 내용
            {problem.get('문제내용', '문제 내용 없음')}
            
            ## 학생 답변
            {student_answer}
            
            ## 모범 답안
            {problem.get('정답', '정답 없음')}
            
            ## 해설
            {problem.get('해설', '해설 없음')}
            
            ## 지시사항
            1. 학생의 답안을 상세히 분석하고 0-100점 사이의 점수를 부여하세요. 주관식 답변 채점 기준은 다음과 같습니다:
               - 90-100점: 완벽하게 이해하고 모든 핵심 개념을 포함한 탁월한 답변
               - 70-89점: 대부분의 핵심 개념을 이해하고 있으나 일부 설명이 미흡한 우수한 답변
               - 50-69점: 기본 개념은 이해했으나 중요한 부분이 누락된 보통 수준의 답변
               - 30-49점: 일부 관련 개념을 포함하지만 주요 오류가 있는 미흡한 답변
               - 0-29점: 핵심 개념을 거의 이해하지 못한 부족한 답변
            
            2. 학생 답변의 강점과 약점을 구체적으로 분석하세요:
               - 정확한 개념이나 잘 표현된 부분 지적
               - 누락된 핵심 개념이나 오해한 부분 지적
               - 표현 방식이나 논리 구조에 대한 피드백
            
            3. 모범 답안과 비교하여 학생 답변의 차이점을 명확히 설명하세요.
            
            4. 잘못된 개념이나 오해가 있다면 올바른 설명과 함께 교정하세요.
            
            5. 해당 주제에 대한 이해를 높이기 위한 구체적인 학습 전략, 추가 자료, 또는 연습 방법을 제안하세요.
            
            6. 학생에게 격려와 동기부여 메시지를 포함하세요.
            
            ## 피드백 형식
            반드시 다음과 같은 형식으로 답변해주세요:
            
            ## 점수: [0-100]
            
            ## 답변 분석
            [학생 답변의 강점과 약점에 대한 상세한 분석]
            
            ## 핵심 개념 설명
            [학생이 놓친 개념이나 오해한 부분에 대한 명확한 설명]
            
            ## 모범 답안 비교
            [학생 답변과 모범 답안의 차이점 분석]
            
            ## 학습 조언
            [앞으로의 학습에 도움이 될 구체적인 조언]
            
            ## 격려 메시지
            [학생에게 전하는 긍정적인 메시지]
            """
        
        # Gemini 모델 호출 - 최적화된 설정
        model = genai.GenerativeModel('gemini-1.5-flash',
                                     safety_settings=[
                                         {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                         {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                         {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                                         {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                                     ],
                                     generation_config={
                                         "temperature": 0.3,  # 더 일관된 결과를 위해 낮은 온도 설정
                                         "top_p": 0.92,
                                         "top_k": 40,
                                         "max_output_tokens": 2048,
                                         "response_mime_type": "text/plain",  # 텍스트 형식으로 일관되게 응답
                                     })
        
        # 최대 3번 재시도 로직 추가
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = model.generate_content(prompt)
                feedback = response.text
                
                # 응답이 유효한지 확인
                if feedback and len(feedback) > 50:  # 최소 응답 길이 확인
                    # 점수 추출 시도
                    try:
                        score_line = next((line for line in feedback.split('\n') if "## 점수:" in line or "##점수:" in line), "## 점수: 0")
                        score_str = score_line.split(":")[-1].strip()
                        # 숫자만 추출
                        score = int(''.join(filter(str.isdigit, score_str)))
                    except:
                        # 객관식인 경우 정답 여부로 점수 결정
                        if problem_type == "객관식" and problem.get("정답") == student_answer:
                            score = 100
                        elif problem_type == "객관식":
                            score = 0
                        else:
                            score = 50  # 기본값 - 주관식이고 점수 추출 실패
                    
                    break
                else:
                    retry_count += 1
                    time.sleep(1)  # 재시도 전 잠시 대기
            except Exception as e:
                print(f"피드백 생성 시도 {retry_count+1} 실패: {str(e)}")
                retry_count += 1
                time.sleep(1)
        
        # 결과 반환
        if retry_count < max_retries:
            return (score, feedback)
        else:
            raise Exception("최대 재시도 횟수 초과")
    
    except Exception as e:
        print(f"피드백 생성 중 오류 발생: {str(e)}")
        # 객관식인 경우 정답 여부로 점수 결정
        if problem_type == "객관식" and problem.get("정답") == student_answer:
            score = 100
        else:
            score = 0
            
        default_feedback = f"""
        ## 점수: {score}
        
        ## 피드백
        현재 피드백 서비스에 일시적인 문제가 있습니다. 
        기본적인 채점 결과만 제공해 드립니다.
        
        정답: {problem.get('정답', '정답 정보 없음')}
        해설: {problem.get('해설', '해설 정보 없음')}
        """
        return (score, default_feedback)