import gspread
import uuid
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import sys

def setup_sheets():
    """
    Google Sheets 초기 설정 및 샘플 데이터 추가
    """
    print("===== Google Sheets 설정 시작 =====\n")
    
    # 서비스 계정 파일 경로 입력
    service_account_path = input("서비스 계정 JSON 파일 경로를 입력하세요: ")
    if not os.path.exists(service_account_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {service_account_path}")
        sys.exit(1)
    
    # Google Sheet ID 입력
    default_sheet_id = "1qVmVfUJUYLQKC67fJQXTd-nVVq0PsUcsvKxs2-3XJ2w"  # 기본값 (사용자가 생성한 빈 스프레드시트)
    sheet_id = input(f"Google Sheets ID를 입력하세요 (기본값: {default_sheet_id}): ") or default_sheet_id
    
    try:
        # 서비스 계정 인증
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_path, scope)
        client = gspread.authorize(creds)
        
        # 스프레드시트 열기
        print(f"스프레드시트 ID {sheet_id}에 접속 중...")
        sheet = client.open_by_key(sheet_id)
        
        # 워크시트 초기화 (problems)
        try:
            problems_sheet = sheet.worksheet("problems")
            # 워크시트가 존재하면 모든 데이터 삭제하고 새로 설정
            problems_sheet.clear()
            print("기존 problems 워크시트를 초기화합니다.")
        except gspread.exceptions.WorksheetNotFound:
            # 워크시트가 없으면 새로 생성
            problems_sheet = sheet.add_worksheet(title="problems", rows=100, cols=20)
            print("problems 워크시트를 생성했습니다.")
        
        # 헤더 설정
        problems_sheet.update("A1:I1", [["문제ID", "문제내용", "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "해설"]])
        
        # 샘플 데이터 추가
        sample_problems = [
            [
                str(uuid.uuid4()),
                "What is the correct form of the verb 'write' in the present perfect tense?",
                "having written",
                "has wrote",
                "has written",
                "have been writing",
                "had written",
                "보기3",
                "Present perfect tense는 'have/has + past participle' 형태로, 'write'의 past participle은 'written'입니다."
            ],
            [
                str(uuid.uuid4()),
                "Choose the correct sentence with the appropriate use of articles.",
                "I saw an unicorn in the forest yesterday.",
                "She is the best student in an class.",
                "He bought a new car, and the car is red.",
                "We had the dinner at restaurant last night.",
                "I need a advice about this problem.",
                "보기3",
                "관사 사용에서 'an'은 모음 소리로 시작하는 단어 앞에, 'a'는 자음 소리로 시작하는 단어 앞에 사용됩니다. 특정 대상을 지칭할 때 'the'를 사용합니다."
            ],
            [
                str(uuid.uuid4()),
                "Which option contains the correct comparative and superlative forms of the adjective 'good'?",
                "good, gooder, goodest",
                "good, better, best",
                "good, more good, most good",
                "well, better, best",
                "good, well, best",
                "보기2",
                "'good'의 비교급은 'better', 최상급은 'best'입니다. 이는 불규칙 형용사로 'more good'이나 'most good' 형태로 변화하지 않습니다."
            ]
        ]
        
        # 샘플 데이터 삽입
        for i, problem in enumerate(sample_problems):
            problems_sheet.update(f"A{i+2}:I{i+2}", [problem])
        
        print(f"{len(sample_problems)}개의 샘플 문제가 추가되었습니다.")
        
        # 워크시트 초기화 (student_answers)
        try:
            answers_sheet = sheet.worksheet("student_answers")
            # 워크시트가 존재하면 모든 데이터 삭제하고 새로 설정
            answers_sheet.clear()
            print("기존 student_answers 워크시트를 초기화합니다.")
        except gspread.exceptions.WorksheetNotFound:
            # 워크시트가 없으면 새로 생성
            answers_sheet = sheet.add_worksheet(title="student_answers", rows=100, cols=20)
            print("student_answers 워크시트를 생성했습니다.")
        
        # 헤더 설정
        answers_sheet.update("A1:G1", [["학생ID", "이름", "문제ID", "제출답안", "점수", "피드백", "제출시간"]])
        
        print("student_answers 워크시트가 초기화되었습니다.")
        
        # .streamlit/secrets.toml 파일 업데이트
        try:
            secrets_path = ".streamlit/secrets.toml"
            if os.path.exists(secrets_path):
                with open(secrets_path, "r", encoding="utf-8") as file:
                    lines = file.readlines()
                
                # GSHEETS_ID 업데이트
                found = False
                for i, line in enumerate(lines):
                    if line.startswith("GSHEETS_ID"):
                        lines[i] = f'GSHEETS_ID = "{sheet_id}"\n'
                        found = True
                        break
                
                if not found:
                    lines.append(f'\nGSHEETS_ID = "{sheet_id}"\n')
                
                with open(secrets_path, "w", encoding="utf-8") as file:
                    file.writelines(lines)
                
                print(f".streamlit/secrets.toml 파일이 업데이트되었습니다 (GSHEETS_ID: {sheet_id})")
        except Exception as e:
            print(f".streamlit/secrets.toml 파일 업데이트 오류: {e}")
        
        print("\n===== Google Sheets 설정 완료 =====")
        print(f"스프레드시트 ID: {sheet_id}")
        print("샘플 문제 추가됨, 학생 답변 시트 초기화됨")
        
    except Exception as e:
        print(f"Google Sheets 설정 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_sheets() 