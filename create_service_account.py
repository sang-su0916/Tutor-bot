"""
인증 정보 생성 도우미 - Google Sheets API 인증을 위한 서비스 계정 설정 가이드
난이도: Easy
---
이 스크립트는 Google Sheets API 연결을 위한 설정 방법을 안내합니다.
직접 실행하는 스크립트가 아니라 안내서 역할을 합니다.
"""

# Google 서비스 계정 및 API 인증 설정 가이드
import os

def print_guide():
    """
    Google 서비스 계정 설정 가이드 출력
    """
    guide = """
==========================================================
Google Sheets API 인증 설정 가이드
==========================================================

1. Google Cloud Platform 프로젝트 생성 (또는 기존 프로젝트 사용)
   - https://console.cloud.google.com/ 접속
   - 새 프로젝트 생성 또는 기존 프로젝트 선택

2. Google Sheets API 및 Google Drive API 활성화
   - 'API 및 서비스' 메뉴 > '라이브러리' 선택
   - 'Google Sheets API' 검색 후 활성화
   - 'Google Drive API' 검색 후 활성화

3. 서비스 계정 생성
   - 'API 및 서비스' > '사용자 인증 정보' 메뉴 선택
   - '사용자 인증 정보 만들기' > '서비스 계정' 선택
   - 서비스 계정 이름 입력 및 생성 완료
   - 생성된 서비스 계정 이메일 주소 기록 (나중에 스프레드시트 공유 시 필요)

4. 서비스 계정 키 생성
   - 생성된 서비스 계정 클릭
   - '키' 탭 선택 > '키 추가' > 'JSON' 선택
   - 다운로드된 JSON 파일을 프로젝트 루트 디렉토리에 'service_account.json'으로 저장

5. Google 스프레드시트 생성 및 공유 설정
   - Google Drive에서 새 스프레드시트 생성
   - 스프레드시트 ID 기록 (URL에서 '/d/' 다음과 '/edit' 이전 부분)
   - 스프레드시트 상단 '공유' 버튼 클릭
   - 3단계에서 생성한 서비스 계정 이메일 주소 입력
   - 권한을 '편집자'로 설정하고 공유

6. .streamlit/secrets.toml 파일 설정
   a. 프로젝트 루트에 .streamlit 디렉토리 생성 (없는 경우)
   b. .streamlit 디렉토리 안에 secrets.toml 파일 생성
   c. 아래 내용 추가 (실제 값으로 대체):

   ```
   # 스프레드시트 ID 설정
   spreadsheet_id = "여기에_스프레드시트_ID_입력"
   
   # Google Cloud 서비스 계정 파일 경로
   GOOGLE_SERVICE_ACCOUNT_PATH = "service_account.json"
   
   # 더미 데이터 사용 설정 (Google Sheets 연결 오류 시)
   use_dummy_data = false
   
   # 서비스 계정 키 정보 설정 (JSON 파일 대체용)
   [gcp_service_account]
   type = "service_account"
   project_id = "서비스_계정_JSON의_project_id_값"
   private_key_id = "서비스_계정_JSON의_private_key_id_값"
   private_key = "서비스_계정_JSON의_private_key_값"
   client_email = "서비스_계정_JSON의_client_email_값"
   client_id = "서비스_계정_JSON의_client_id_값"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "서비스_계정_JSON의_client_x509_cert_url_값"
   universe_domain = "googleapis.com"
   ```

7. 서비스 계정 키 파일에서 값 추출
   - service_account.json 파일을 열고, 위 설정의 각 항목에 맞는 값을 복사하여 secrets.toml에 붙여넣기
   - 특히 private_key는 여러 줄로 되어 있으므로 정확히 복사하고, 줄바꿈 문자(\n)를 포함해야 함

8. 서비스 계정 키 보안
   - service_account.json 파일은 민감한 정보를 포함하므로 안전하게 관리
   - .gitignore에 service_account.json을 추가하여 실수로 버전 관리에 포함되지 않도록 설정

9. 설정 테스트
   - setup_sheets.py 스크립트를 실행하여 인증 설정이 올바르게 완료되었는지 확인
   - streamlit run main.py 명령으로 애플리케이션 실행 후 Google Sheets 연결 확인

==========================================================
학습 키워드: Google Cloud Platform, API Key, Service Account, OAuth2, Google Sheets API, 인증 자격 증명
==========================================================
"""
    print(guide)

    # .streamlit 디렉토리 존재 확인 및 안내
    if not os.path.exists(".streamlit"):
        print("알림: '.streamlit' 디렉토리가 현재 프로젝트에 존재하지 않습니다.")
        print("     위 안내에 따라 '.streamlit' 디렉토리를 먼저 생성해주세요.")
    
    # secrets.toml 파일 존재 확인 및 안내
    if not os.path.exists(".streamlit/secrets.toml"):
        print("알림: '.streamlit/secrets.toml' 파일이 현재 프로젝트에 존재하지 않습니다.")
        print("     위 안내에 따라 파일을 생성하고 필요한 설정을 추가해주세요.")
    else:
        print("알림: '.streamlit/secrets.toml' 파일이 이미 존재합니다.")
        print("     필요한 경우 위 안내에 따라 파일 내용을 업데이트해주세요.")
    
    # service_account.json 파일 존재 확인 및 안내
    if not os.path.exists("service_account.json"):
        print("알림: 'service_account.json' 파일이 현재 프로젝트에 존재하지 않습니다.")
        print("     위 안내에 따라 서비스 계정 키를 생성하고 다운로드 받아주세요.")
    else:
        print("알림: 'service_account.json' 파일이 이미 존재합니다.")
        print("     해당 파일이 유효한 서비스 계정 키 파일인지 확인해주세요.")

if __name__ == "__main__":
    print_guide() 