"""
secrets.toml 생성 도우미 - Streamlit 앱을 위한 secrets 파일 생성
난이도: Easy
---
이 스크립트는 Streamlit 앱에서 사용할 .streamlit/secrets.toml 파일을 생성합니다.
Google Sheets API 연결에 필요한 설정을 입력받아 저장합니다.
"""

import os
import json
from pathlib import Path

def create_secrets_toml():
    """
    사용자 입력을 받아 .streamlit/secrets.toml 파일을 생성합니다.
    """
    print("=== Streamlit secrets.toml 파일 생성 도우미 ===")
    
    # .streamlit 디렉토리 생성
    streamlit_dir = Path(".streamlit")
    if not streamlit_dir.exists():
        streamlit_dir.mkdir(exist_ok=True)
        print(".streamlit 디렉토리가 생성되었습니다.")
    
    # secrets.toml 파일 경로
    secrets_file = streamlit_dir / "secrets.toml"
    
    # 파일이 이미 존재하는 경우 경고
    if secrets_file.exists():
        print(f"경고: {secrets_file} 파일이 이미 존재합니다.")
        overwrite = input("기존 파일을 덮어쓰시겠습니까? (y/n): ").lower().strip()
        if overwrite != 'y':
            print("작업이 취소되었습니다.")
            return
    
    # 스프레드시트 ID 입력
    spreadsheet_id = input("스프레드시트 ID를 입력하세요 (URL에서 '/d/' 다음과 '/edit' 이전 부분): ").strip()
    
    # service_account.json 파일 읽기
    service_account_path = input("서비스 계정 JSON 파일 경로를 입력하세요 (기본값: service_account.json): ").strip() or "service_account.json"
    
    try:
        with open(service_account_path, 'r') as f:
            service_account_info = json.load(f)
        print(f"{service_account_path} 파일을 읽었습니다.")
    except FileNotFoundError:
        print(f"오류: {service_account_path} 파일을 찾을 수 없습니다.")
        service_account_info = None
    except json.JSONDecodeError:
        print(f"오류: {service_account_path} 파일이 유효한 JSON 형식이 아닙니다.")
        service_account_info = None
    
    # OpenAI API 키 (선택사항)
    use_openai = input("OpenAI API를 사용하시겠습니까? (y/n, 기본값: n): ").lower().strip() == 'y'
    openai_api_key = ""
    if use_openai:
        openai_api_key = input("OpenAI API 키를 입력하세요: ").strip()
    
    # Google Gemini API 키 (선택사항)
    use_gemini = input("Google Gemini API를 사용하시겠습니까? (y/n, 기본값: n): ").lower().strip() == 'y'
    google_api_key = ""
    if use_gemini:
        google_api_key = input("Google Gemini API 키를 입력하세요: ").strip()
    
    # secrets.toml 파일 내용 생성
    content = []
    
    # 스프레드시트 ID 설정
    content.append("# 스프레드시트 ID 설정")
    content.append(f'spreadsheet_id = "{spreadsheet_id}"')
    content.append(f'GSHEETS_ID = "{spreadsheet_id}"')
    content.append("")
    
    # 서비스 계정 파일 경로
    content.append("# Google Cloud 서비스 계정 파일 경로")
    content.append(f'GOOGLE_SERVICE_ACCOUNT_PATH = "{os.path.basename(service_account_path)}"')
    content.append("")
    
    # 더미 데이터 사용 설정
    content.append("# 더미 데이터 사용 설정 (Google Sheets 연결 오류 시)")
    content.append("use_dummy_data = false")
    content.append("")
    
    # OpenAI API 키 (있는 경우)
    if use_openai and openai_api_key:
        content.append("# OpenAI API 설정")
        content.append(f'OPENAI_API_KEY = "{openai_api_key}"')
        content.append("")
    
    # Google Gemini API 키 (있는 경우)
    if use_gemini and google_api_key:
        content.append("# Google Gemini API 키")
        content.append(f'GOOGLE_API_KEY = "{google_api_key}"')
        content.append("")
    
    # 서비스 계정 정보 (있는 경우)
    if service_account_info:
        content.append("# Google Cloud 서비스 계정 정보")
        content.append("[gcp_service_account]")
        
        # 서비스 계정 정보 추가
        for key, value in service_account_info.items():
            if key == "private_key":
                # private_key는 여러 줄로 되어 있으므로 큰따옴표로 감싸서 처리
                content.append(f'{key} = "{value}"')
            else:
                # 다른 필드는 일반 문자열로 처리
                content.append(f'{key} = "{value}"')
    
    # 파일에 내용 쓰기
    try:
        with open(secrets_file, 'w') as f:
            f.write('\n'.join(content))
        print(f"성공: {secrets_file} 파일이 생성되었습니다.")
    except Exception as e:
        print(f"오류: 파일 생성 실패 - {e}")
    
    print("\n설정이 완료되었습니다. 이제 'streamlit run main.py' 명령으로 앱을 실행해보세요.")

if __name__ == "__main__":
    create_secrets_toml() 