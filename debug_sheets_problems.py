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
                
                # 필수 필드 검증
                required_fields = ["문제ID", "과목", "학년", "문제유형", "난이도", "문제내용", "정답"]
                valid_problems = []
                invalid_problems = []
                
                for idx, problem in enumerate(all_data, 1):
                    missing_fields = [field for field in required_fields if field not in problem or not problem[field]]
                    if missing_fields:
                        invalid_problems.append({
                            "row": idx + 1,
                            "missing_fields": missing_fields,
                            "problem_id": problem.get("문제ID", "없음")
                        })
                    else:
                        valid_problems.append(problem)
                
                print(f"\n✅ 유효한 문제 수: {len(valid_problems)}")
                print(f"❌ 유효하지 않은 문제 수: {len(invalid_problems)}")
                
                if invalid_problems:
                    print("\n유효하지 않은 문제 목록:")
                    for problem in invalid_problems[:5]:  # 처음 5개만 출력
                        print(f"- 행 {problem['row']}: 문제ID {problem['problem_id']}")
                        print(f"  누락된 필드: {', '.join(problem['missing_fields'])}")
                
                # 학년별 문제 수 통계
                grade_stats = {}
                for problem in valid_problems:
                    grade = problem.get("학년", "미지정")
                    grade_stats[grade] = grade_stats.get(grade, 0) + 1
                
                print("\n학년별 문제 수:")
                for grade, count in grade_stats.items():
                    print(f"- {grade}: {count}개")
                
                # 문제 유형별 통계
                type_stats = {}
                for problem in valid_problems:
                    problem_type = problem.get("문제유형", "미지정")
                    type_stats[problem_type] = type_stats.get(problem_type, 0) + 1
                
                print("\n문제 유형별 수:")
                for problem_type, count in type_stats.items():
                    print(f"- {problem_type}: {count}개")
                
                # 첫 번째 유효한 문제 출력
                if valid_problems:
                    print("\n첫 번째 유효한 문제 데이터:")
                    pprint.pprint(valid_problems[0])
                else:
                    print("\n❌ 유효한 문제가 없습니다.")
                
            except gspread.exceptions.WorksheetNotFound:
                print("❌ 'problems' 워크시트를 찾을 수 없습니다")
        except Exception as e:
            print(f"❌ 스프레드시트 열기 실패: {str(e)}")
    except Exception as e:
        print(f"❌ gspread 인증 실패: {str(e)}")
    
    print("===== 구글 시트 문제 불러오기 디버깅 완료 =====")

if __name__ == "__main__":
    debug_problems_sheet() 