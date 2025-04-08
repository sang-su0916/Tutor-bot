"""
인증 정보 진단 및 수정 스크립트
난이도: Easy
---
이 스크립트는 Google Sheets API 연결을 위한 인증 정보 문제를 진단하고 수정합니다.
"""

import os
import json
import streamlit as st
from pathlib import Path
import traceback

def diagnose_auth_issues():
    """
    인증 정보 문제를 진단하고 수정합니다.
    """
    print("===== 인증 정보 진단 시작 =====")
    issues_found = False
    
    # 1. .streamlit 디렉토리 확인
    streamlit_dir = Path(".streamlit")
    if not streamlit_dir.exists():
        print("문제 발견: .streamlit 디렉토리가 없습니다.")
        os.makedirs(streamlit_dir, exist_ok=True)
        print("조치: .streamlit 디렉토리를 생성했습니다.")
        issues_found = True
    else:
        print("확인: .streamlit 디렉토리가 존재합니다.")
    
    # 2. secrets.toml 파일 확인
    secrets_path = streamlit_dir / "secrets.toml"
    if not secrets_path.exists():
        print("문제 발견: secrets.toml 파일이 없습니다.")
        issues_found = True
    else:
        print("확인: secrets.toml 파일이 존재합니다.")
        
        # secrets.toml 내용 확인
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets_content = f.read()
            
        # 필수 설정 확인
        required_settings = {
            "spreadsheet_id": "스프레드시트 ID",
            "GOOGLE_SERVICE_ACCOUNT_PATH": "서비스 계정 파일 경로",
            "gcp_service_account": "서비스 계정 정보 섹션"
        }
        
        for setting, desc in required_settings.items():
            if setting == "gcp_service_account":
                if "[gcp_service_account]" not in secrets_content:
                    print(f"문제 발견: {desc}가 없습니다.")
                    issues_found = True
                else:
                    print(f"확인: {desc}가 존재합니다.")
            else:
                if setting not in secrets_content:
                    print(f"문제 발견: {setting} ({desc}) 설정이 없습니다.")
                    issues_found = True
                else:
                    print(f"확인: {setting} 설정이 존재합니다.")
    
    # 3. 서비스 계정 JSON 파일 확인
    service_account_path = "service_account.json"
    if not os.path.exists(service_account_path):
        print(f"문제 발견: {service_account_path} 파일이 없습니다.")
        issues_found = True
    else:
        print(f"확인: {service_account_path} 파일이 존재합니다.")
        
        # 서비스 계정 JSON 파일 내용 검증
        try:
            with open(service_account_path, 'r') as f:
                sa_info = json.load(f)
            
            # 필수 필드 확인
            required_fields = ["type", "project_id", "private_key_id", "private_key", 
                               "client_email", "client_id", "auth_uri", "token_uri", 
                               "auth_provider_x509_cert_url", "client_x509_cert_url"]
            
            missing_fields = [field for field in required_fields if field not in sa_info]
            
            if missing_fields:
                print(f"문제 발견: 서비스 계정 JSON 파일에 다음 필드가 누락되었습니다: {', '.join(missing_fields)}")
                issues_found = True
            else:
                print("확인: 서비스 계정 JSON 파일에 모든 필수 필드가 포함되어 있습니다.")
                
            # 서비스 계정 이메일 표시 (공유 설정 확인용)
            if "client_email" in sa_info:
                print(f"서비스 계정 이메일: {sa_info['client_email']}")
                print("이 이메일이 스프레드시트에 '편집자' 권한으로 공유되어 있는지 확인하세요.")
                
        except json.JSONDecodeError:
            print(f"문제 발견: {service_account_path} 파일이 유효한 JSON 형식이 아닙니다.")
            issues_found = True
        except Exception as e:
            print(f"오류 발생: {service_account_path} 파일 처리 중 오류가 발생했습니다: {str(e)}")
            issues_found = True
    
    # 4. .streamlit/secrets.toml과 service_account.json 일치 여부 확인
    if os.path.exists(secrets_path) and os.path.exists(service_account_path):
        try:
            # service_account.json 파일 읽기
            with open(service_account_path, 'r') as f:
                sa_info = json.load(f)
            
            # secrets.toml 파일 내용 확인
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets_content = f.read()
            
            # 서비스 계정 이메일 일치 여부 확인
            if "client_email" in sa_info:
                sa_email = sa_info["client_email"]
                if sa_email not in secrets_content:
                    print(f"문제 발견: secrets.toml 파일에 올바른 서비스 계정 이메일({sa_email})이 없습니다.")
                    issues_found = True
                else:
                    print("확인: 서비스 계정 이메일이 일치합니다.")
        except Exception as e:
            print(f"오류 발생: 파일 비교 중 오류가 발생했습니다: {str(e)}")
            issues_found = True
    
    # 결과 요약
    if issues_found:
        print("\n인증 정보에 문제가 발견되었습니다. 위의 조치 사항을 확인하세요.")
    else:
        print("\n모든 인증 정보가 올바르게 설정되어 있습니다.")
    
    # 인증 정보 수정 제안
    print("\n===== 인증 정보 수정 안내 =====")
    print("1. 인증 정보 자동 업데이트 - create_secrets_toml.py 스크립트를 실행하여 인증 정보를 새로 생성")
    print("2. 인증 정보 수동 수정 - .streamlit/secrets.toml 파일을 직접 편집")
    print("3. Google Cloud Console에서 새 서비스 계정 키 다운로드 - https://console.cloud.google.com/")
    print("4. 스프레드시트 공유 설정 확인 - 서비스 계정 이메일에 편집 권한 부여")
    
    return issues_found

def fix_auth_issues():
    """
    인증 정보 문제를 수정합니다.
    """
    print("\n===== 인증 정보 문제 수정 =====")
    
    # 서비스 계정 JSON 파일이 있는지 확인
    service_account_path = "service_account.json"
    if not os.path.exists(service_account_path):
        print(f"오류: {service_account_path} 파일이 없습니다. 먼저 서비스 계정 키를 다운로드해야 합니다.")
        return
    
    try:
        # 서비스 계정 JSON 파일 읽기
        with open(service_account_path, 'r') as f:
            sa_info = json.load(f)
        
        # 스프레드시트 ID 입력
        spreadsheet_id = input("스프레드시트 ID를 입력하세요 (URL에서 '/d/' 다음과 '/edit' 이전 부분): ").strip()
        if not spreadsheet_id:
            print("오류: 스프레드시트 ID가 입력되지 않았습니다.")
            return
        
        # .streamlit 디렉토리 생성
        streamlit_dir = Path(".streamlit")
        streamlit_dir.mkdir(exist_ok=True)
        
        # secrets.toml 파일 생성
        secrets_path = streamlit_dir / "secrets.toml"
        
        # secrets.toml 파일 내용 생성
        secrets_content = [
            "# 스프레드시트 ID 설정 (URL에서 가져온 정확한 ID)",
            f'spreadsheet_id = "{spreadsheet_id}"',
            f'GSHEETS_ID = "{spreadsheet_id}"',
            "",
            "# 더미 데이터 사용 설정 (Google Sheets 연결 오류 시)",
            "use_dummy_data = false",
            "",
            "# Google Cloud 서비스 계정 파일 경로 (선택사항)",
            f'GOOGLE_SERVICE_ACCOUNT_PATH = "{service_account_path}"',
            "",
            "# Google Cloud 서비스 계정 정보",
            "[gcp_service_account]"
        ]
        
        # 서비스 계정 정보 추가
        for key, value in sa_info.items():
            if key == "private_key":
                # private_key는 여러 줄로 되어 있으므로 큰따옴표로 감싸서 처리
                secrets_content.append(f'{key} = "{value}"')
            else:
                # 다른 필드는 일반 문자열로 처리
                secrets_content.append(f'{key} = "{value}"')
        
        # 파일에 내용 쓰기
        with open(secrets_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(secrets_content))
        
        print(f"성공: {secrets_path} 파일이 업데이트되었습니다.")
        print("\n인증 정보가 성공적으로 업데이트되었습니다.")
        print("이제 'streamlit run main.py' 명령으로 앱을 실행해보세요.")
        
    except Exception as e:
        print(f"오류 발생: 인증 정보 수정 중 오류가 발생했습니다: {str(e)}")
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    print("\n===== Google Sheets API 인증 정보 진단 및 수정 도구 =====\n")
    
    # 인증 정보 진단
    issues_found = diagnose_auth_issues()
    
    # 인증 정보 수정 여부 확인
    if issues_found:
        fix_option = input("\n인증 정보 문제를 자동으로 수정하시겠습니까? (y/n): ").lower().strip()
        if fix_option == 'y':
            fix_auth_issues()
        else:
            print("인증 정보 문제를 수동으로 수정하세요.")
    else:
        print("\n인증 정보 문제가 발견되지 않았습니다. 추가 조치가 필요하지 않습니다.")
        
    print("\n===== 진단 완료 =====") 