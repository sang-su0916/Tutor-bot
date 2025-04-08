import os
import json
import gspread
from google.oauth2.service_account import Credentials
import pprint

# 디버깅을 위한 함수
def debug_problems_sheet():
    """구글 시트의 problems 워크시트를 디버깅합니다."""
    print("===== 구글 시트 문제 불러오기 디버깅 시작 =====")
    
    # 서비스 계정 파일 확인
    service_account_path = "service_account.json"
    if not os.path.exists(service_account_path):
        print(f"❌ 서비스 계정 파일이 존재하지 않습니다: {service_account_path}")
        return
    
    # 스프레드시트 ID 설정
    spreadsheet_id = "1C-LBiJX_ewRS-bJgY2eIKkn9diIAO0PAAJuM_72izGA"
    print(f"확인할 스프레드시트 ID: {spreadsheet_id}")
    
    try:
        # OAuth 인증 범위 설정
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 서비스 계정으로 인증
        print("서비스 계정 파일로 인증 시도 중...")
        creds = Credentials.from_service_account_file(service_account_path, scopes=scope)
        client = gspread.authorize(creds)
        print("✅ gspread 인증 성공")
        
        # 스프레드시트 열기
        try:
            sheet = client.open_by_key(spreadsheet_id)
            print(f"✅ 스프레드시트 열기 성공: '{sheet.title}'")
            
            # problems 워크시트 확인
            try:
                problems_sheet = sheet.worksheet("problems")
                print(f"✅ 'problems' 워크시트 접근 성공")
                
                # 헤더 확인
                headers = problems_sheet.row_values(1)
                print(f"✅ 헤더: {headers}")
                
                # 모든 데이터 가져오기
                all_data = problems_sheet.get_all_records()
                print(f"✅ 총 {len(all_data)}개의 문제 데이터 발견")
                
                # 첫 번째 문제 출력
                if all_data:
                    print("\n첫 번째 문제 데이터:")
                    pprint.pprint(all_data[0])
                    
                    # 필수 필드 확인
                    required_fields = ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "정답"]
                    missing_fields = [field for field in required_fields if field not in all_data[0] or not all_data[0][field]]
                    
                    if missing_fields:
                        print(f"❌ 첫 번째 문제에 필수 필드가 누락되었습니다: {missing_fields}")
                    else:
                        print("✅ 첫 번째 문제의 모든 필수 필드가 존재합니다")
                    
                    # 선택지 필드 확인 (객관식인 경우)
                    if all_data[0].get("문제유형") == "객관식":
                        option_fields = ["보기1", "보기2", "보기3", "보기4", "보기5"]
                        missing_options = [field for field in option_fields if field not in all_data[0] or not all_data[0][field]]
                        
                        if missing_options and len(missing_options) > 1:  # 보기5는 없을 수 있음
                            print(f"❌ 객관식 문제지만 일부 보기가 누락되었습니다: {missing_options}")
                        else:
                            print("✅ 객관식 문제의 보기가 적절히 설정되어 있습니다")
                else:
                    print("❌ 문제 데이터가 없습니다")
            except gspread.exceptions.WorksheetNotFound:
                print("❌ 'problems' 워크시트를 찾을 수 없습니다")
        except Exception as e:
            print(f"❌ 스프레드시트 열기 실패: {str(e)}")
    except Exception as e:
        print(f"❌ gspread 인증 실패: {str(e)}")
    
    print("===== 구글 시트 문제 불러오기 디버깅 완료 =====")

if __name__ == "__main__":
    debug_problems_sheet() 