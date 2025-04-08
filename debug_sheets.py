import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 디버깅을 위한 함수
def debug_sheets_connection():
    """구글 시트 연결을 디버깅합니다."""
    print("===== 구글 시트 연결 디버깅 시작 =====")
    
    # 1. 서비스 계정 파일 확인
    service_account_path = "service_account.json"
    if os.path.exists(service_account_path):
        print(f"✅ 서비스 계정 파일 확인: {service_account_path} 파일이 존재합니다.")
        
        # 파일 내용 확인
        try:
            with open(service_account_path, 'r', encoding='utf-8') as f:
                service_account_info = json.load(f)
                print(f"✅ 서비스 계정 이메일: {service_account_info.get('client_email', '이메일 정보 없음')}")
        except Exception as e:
            print(f"❌ 서비스 계정 파일 읽기 오류: {str(e)}")
    else:
        print(f"❌ 서비스 계정 파일이 존재하지 않습니다: {service_account_path}")
    
    # 2. 스프레드시트 ID 확인
    spreadsheet_id = "1C-LBiJX_ewRS-bJgY2eIKkn9diIAO0PAAJuM_72izGA"
    print(f"확인할 스프레드시트 ID: {spreadsheet_id}")
    
    # 3. API 연결 시도
    try:
        # OAuth 인증 범위 설정
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 서비스 계정으로 인증
        print("서비스 계정 파일로 인증 시도 중...")
        creds = Credentials.from_service_account_file(service_account_path, scopes=scope)
        client = gspread.authorize(creds)
        print("✅ gspread 인증 성공")
        
        # 스프레드시트 열기 시도
        print(f"스프레드시트 ID로 시트 열기 시도: {spreadsheet_id}")
        try:
            sheet = client.open_by_key(spreadsheet_id)
            print(f"✅ 스프레드시트 열기 성공: '{sheet.title}'")
            
            # 워크시트 목록 확인
            worksheets = sheet.worksheets()
            print(f"✅ 워크시트 목록: {', '.join([ws.title for ws in worksheets])}")
            
            # 첫 번째 워크시트의 첫 행 읽기 시도
            if worksheets:
                first_worksheet = worksheets[0]
                try:
                    first_row = first_worksheet.row_values(1)
                    print(f"✅ 첫 번째 워크시트('{first_worksheet.title}')의 첫 행 읽기 성공: {first_row}")
                except Exception as e:
                    print(f"❌ 워크시트 데이터 읽기 오류: {str(e)}")
            
            print("✅ 구글 시트 연결 및 데이터 접근 모두 성공!")
        except gspread.exceptions.APIError as e:
            print(f"❌ Google API 오류: {str(e)}")
            print("🔍 가능한 원인: API 할당량 초과, 권한 문제, 잘못된 스프레드시트 ID 등")
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ 스프레드시트를 찾을 수 없습니다: {spreadsheet_id}")
            print("🔍 가능한 원인: 잘못된 스프레드시트 ID 또는 서비스 계정에 공유되지 않은 시트")
        except Exception as e:
            print(f"❌ 스프레드시트 열기 오류: {str(e)}")
    except Exception as e:
        print(f"❌ gspread 인증 오류: {str(e)}")
    
    print("===== 구글 시트 연결 디버깅 완료 =====")

if __name__ == "__main__":
    debug_sheets_connection() 