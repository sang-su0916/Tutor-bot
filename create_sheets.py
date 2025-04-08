import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 디버깅을 위한 함수
def create_new_spreadsheet():
    """새 구글 스프레드시트를 생성하고 필요한 워크시트를 설정합니다."""
    print("===== 새 구글 스프레드시트 생성 시작 =====")
    
    # 서비스 계정 파일 확인
    service_account_path = "service_account.json"
    if not os.path.exists(service_account_path):
        print(f"❌ 서비스 계정 파일이 존재하지 않습니다: {service_account_path}")
        return
    
    try:
        # OAuth 인증 범위 설정
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 서비스 계정으로 인증
        print("서비스 계정 파일로 인증 시도 중...")
        creds = Credentials.from_service_account_file(service_account_path, scopes=scope)
        client = gspread.authorize(creds)
        print("✅ gspread 인증 성공")
        
        # 서비스 계정 이메일 출력
        with open(service_account_path, 'r') as f:
            service_account_info = json.load(f)
            service_email = service_account_info.get('client_email', '이메일 없음')
            print(f"📧 서비스 계정 이메일: {service_email}")
            print(f"📋 이 이메일을 스프레드시트 공유 설정에 추가해야 합니다.")
        
        # 새 스프레드시트 생성
        try:
            spreadsheet_title = "Tutor-bot-Data"
            spreadsheet = client.create(spreadsheet_title)
            print(f"✅ 새 스프레드시트 생성 성공: '{spreadsheet.title}'")
            print(f"📝 스프레드시트 ID: {spreadsheet.id}")
            print(f"🔗 링크: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")
            
            # 생성한 스프레드시트 공유 설정
            try:
                # 모든 사람에게 보기 권한 부여 (선택사항)
                # spreadsheet.share(None, perm_type='anyone', role='reader')
                
                # 기본 워크시트 이름 변경
                worksheet = spreadsheet.get_worksheet(0)
                worksheet.update_title("problems")
                
                # 추가 워크시트 생성
                required_sheets = ["student_answers", "student_weaknesses", "students"]
                for sheet_name in required_sheets:
                    spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                
                # problems 워크시트에 헤더 추가
                problems_sheet = spreadsheet.worksheet("problems")
                headers = ["문제ID", "과목", "학년", "문제유형", "난이도", "키워드", "문제내용", 
                           "보기1", "보기2", "보기3", "보기4", "보기5", "정답", "해설"]
                problems_sheet.update('A1:N1', [headers])
                
                # student_answers 워크시트에 헤더 추가
                answers_sheet = spreadsheet.worksheet("student_answers")
                headers = ["학생ID", "학생이름", "학년", "문제ID", "과목", "문제유형", "난이도", 
                           "제출답안", "정답여부", "제출일시"]
                answers_sheet.update('A1:J1', [headers])
                
                # student_weaknesses 워크시트에 헤더 추가
                weaknesses_sheet = spreadsheet.worksheet("student_weaknesses")
                headers = ["학생ID", "키워드", "시도횟수", "정답횟수", "정답률", "최근시도일"]
                weaknesses_sheet.update('A1:F1', [headers])
                
                # students 워크시트에 헤더 추가
                students_sheet = spreadsheet.worksheet("students")
                headers = ["학생ID", "이름", "학년", "실력등급", "등록일"]
                students_sheet.update('A1:E1', [headers])
                
                print("✅ 모든 워크시트 설정 완료")
                
                # .streamlit/secrets.toml 파일에 설정할 정보 제공
                print("\n===== .streamlit/secrets.toml 파일 설정 정보 =====")
                print("다음 정보를 .streamlit/secrets.toml 파일에 추가하세요:")
                print(f"spreadsheet_id = \"{spreadsheet.id}\"")
                print(f"GSHEETS_ID = \"{spreadsheet.id}\"")
                
            except Exception as e:
                print(f"❌ 워크시트 설정 중 오류: {str(e)}")
        except Exception as e:
            print(f"❌ 스프레드시트 생성 실패: {str(e)}")
    except Exception as e:
        print(f"❌ gspread 인증 실패: {str(e)}")
    
    print("===== 새 구글 스프레드시트 생성 완료 =====")
    print("📌 주의: 생성된 스프레드시트를 사용하려면 서비스 계정 이메일에 공유 권한을 부여해야 합니다!")

if __name__ == "__main__":
    create_new_spreadsheet() 