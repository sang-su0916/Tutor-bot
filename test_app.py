import os
import sys
from sheets_utils import connect_to_sheets, get_random_problem, save_student_answer
from gpt_feedback import get_openai_client, generate_feedback
import streamlit as st
import uuid
from datetime import datetime

def test_google_sheets_connection():
    """Google Sheets 연결 테스트"""
    print("🔍 Google Sheets 연결 테스트...")
    try:
        sheet = connect_to_sheets()
        if sheet:
            print("✅ Google Sheets 연결 성공!")
            return True
        else:
            print("❌ Google Sheets 연결 실패")
            return False
    except Exception as e:
        print(f"❌ Google Sheets 연결 오류: {e}")
        return False

def test_get_problem():
    """문제 불러오기 테스트"""
    print("\n🔍 문제 불러오기 테스트...")
    try:
        problem = get_random_problem()
        if problem:
            print("✅ 문제 불러오기 성공!")
            print(f"- 문제 내용: {problem.get('문제내용', '정보 없음')}")
            print(f"- 보기1: {problem.get('보기1', '정보 없음')}")
            print(f"- 정답: {problem.get('정답', '정보 없음')}")
            return True
        else:
            print("❌ 문제 불러오기 실패")
            return False
    except Exception as e:
        print(f"❌ 문제 불러오기 오류: {e}")
        return False

def test_openai_connection():
    """OpenAI API 연결 테스트"""
    print("\n🔍 OpenAI API 연결 테스트...")
    try:
        client = get_openai_client()
        if client:
            print("✅ OpenAI API 연결 성공!")
            return True
        else:
            print("❌ OpenAI API 연결 실패")
            return False
    except Exception as e:
        print(f"❌ OpenAI API 연결 오류: {e}")
        return False

def test_feedback_generation():
    """채점 및 피드백 생성 테스트"""
    print("\n🔍 채점 및 피드백 생성 테스트...")
    try:
        # 문제 정보 딕셔너리 생성
        problem_dict = {
            "문제내용": "What is the correct form of the verb 'write' in the present perfect tense?",
            "정답": "보기3",
            "해설": "Present perfect tense는 'have/has + past participle' 형태로, 'write'의 past participle은 'written'입니다.",
            "문제유형": "객관식",
            "보기정보": {
                "보기1": "writed",
                "보기2": "wrote",
                "보기3": "written",
                "보기4": "writing"
            }
        }
        student_answer = "보기3"
        
        score, feedback = generate_feedback(problem_dict, student_answer)
        
        if score is not None and feedback:
            print("✅ 채점 및 피드백 생성 성공!")
            print(f"- 점수: {score}")
            print(f"- 피드백: {feedback}")
            return True
        else:
            print("❌ 채점 및 피드백 생성 실패")
            return False
    except Exception as e:
        print(f"❌ 채점 및 피드백 생성 오류: {e}")
        return False

def test_save_answer():
    """답변 저장 테스트"""
    print("\n🔍 답변 저장 테스트...")
    try:
        student_id = str(uuid.uuid4())
        student_name = "테스트_학생"
        problem_id = str(uuid.uuid4())
        submitted_answer = "보기3"
        score = 100
        feedback = "정답입니다! 'write'의 과거분사형은 'written'이 맞습니다."
        
        result = save_student_answer(student_id, student_name, problem_id, submitted_answer, score, feedback)
        
        if result:
            print("✅ 답변 저장 성공!")
            return True
        else:
            print("❌ 답변 저장 실패")
            return False
    except Exception as e:
        print(f"❌ 답변 저장 오류: {e}")
        return False

def run_all_tests():
    """모든 테스트 실행"""
    print("===== GPT 학습 피드백 웹앱 테스트 시작 =====\n")
    
    # 테스트 결과 저장
    results = {
        "Google Sheets 연결": test_google_sheets_connection(),
        "문제 불러오기": test_get_problem(),
        "OpenAI API 연결": test_openai_connection(),
        "채점 및 피드백 생성": test_feedback_generation(),
        "답변 저장": test_save_answer()
    }
    
    # 테스트 결과 요약
    print("\n===== 테스트 결과 요약 =====")
    all_passed = True
    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 오류를 확인하세요.")
    
    return all_passed

if __name__ == "__main__":
    # 환경 변수 설정을 위해 .streamlit/secrets.toml 파일 확인
    if not os.path.exists(".streamlit/secrets.toml"):
        print("❌ .streamlit/secrets.toml 파일이 없습니다.")
        print("테스트를 실행하기 전에 .streamlit/secrets.toml 파일을 설정해주세요.")
        sys.exit(1)
    
    run_all_tests() 