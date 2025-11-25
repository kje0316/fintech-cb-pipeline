"""
로컬에서 AWS EC2 Spark 통합 파이프라인 원격 실행

통합 ETL 파이프라인:
CSV → Lake → DWH2 (Dimensions + Facts) → DM (원본 + 파생)
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ==================== 설정 ====================
# AWS 접속 정보
SSH_KEY = r"C:\Users\user\.ssh\elice-aws-key.pem"  # 새로 생성한 키 경로로
EC2_HOST = "ubuntu@3.104.157.213"
PROJECT_PATH = "~/fintech-cb-pipeline"

# 로컬 프로젝트 경로
LOCAL_PROJECT_PATH = Path(__file__).parent
# ==============================================


# def sync_code():
#     """로컬 코드를 EC2에 동기화 (Git)"""
#     print_header("코드 동기화 (Git)")
    
#     # 로컬에서 Git push
#     print("\n[로컬] Git 변경사항 확인...")
    
#     # Git status 확인
#     result = subprocess.run(
#         ["git", "status", "--short"],
#         cwd=LOCAL_PROJECT_PATH,
#         capture_output=True,
#         text=True
#     )
    
#     if result.stdout.strip():
#         print(f"변경된 파일:\n{result.stdout}")
        
#         # Git add
#         print("[로컬] Git add...")
#         subprocess.run(
#             ["git", "add", "."],
#             cwd=LOCAL_PROJECT_PATH,
#             capture_output=True
#         )
        
#         # Git commit
#         commit_msg = f"Auto sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
#         print(f"[로컬] Git commit: {commit_msg}")
#         result = subprocess.run(
#             ["git", "commit", "-m", commit_msg],
#             cwd=LOCAL_PROJECT_PATH,
#             capture_output=True,
#             text=True
#         )
        
#         # Git push
#         print("[로컬] Git push...")
#         result = subprocess.run(
#             ["git", "push", "origin", "dev"],
#             cwd=LOCAL_PROJECT_PATH,
#             capture_output=True,
#             text=True
#         )
        
#         if result.returncode == 0:
#             print("✓ 로컬 Git push 완료")
#         else:
#             if "Everything up-to-date" in result.stderr:
#                 print("✓ 이미 최신 상태")
#             else:
#                 print(f"⚠ Git push 경고: {result.stderr}")
#     else:
#         print("✓ 변경사항 없음 (최신 상태)")
    
#     # EC2에서 Git pull
#     print("\n[EC2] Git pull...")
#     returncode = run_remote_command(
#         f"cd {PROJECT_PATH} && git pull origin dev",
#         show_output=True
#     )
    
#     if returncode == 0:
#         print("✓ EC2 코드 동기화 완료\n")
#         return True
#     else:
#         print("✗ EC2 코드 동기화 실패\n")
#         return False

def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_remote_command(command, show_output=True):
    """
    SSH로 원격 명령 실행
    
    Parameters:
    -----------
    command : str
        실행할 명령어
    show_output : bool
        실시간 출력 여부
        
    Returns:
    --------
    int or tuple
        show_output=True: returncode
        show_output=False: (returncode, stdout, stderr)
    """
    ssh_cmd = [
        "ssh",
        "-i", SSH_KEY,
        EC2_HOST,
        command
    ]
    
    if show_output:
        # 실시간 출력
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        return process.returncode
    else:
        # 결과만 받기
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr


def check_connection():
    """EC2 연결 확인"""
    print_header("EC2 연결 확인")
    
    returncode, stdout, stderr = run_remote_command("echo 'Connection OK'", show_output=False)
    
    if returncode == 0:
        print("✓ EC2 연결 성공!")
        print(f"  Host: {EC2_HOST}")
        print(f"  Key: {SSH_KEY}\n")
        return True
    else:
        print(f"✗ EC2 연결 실패: {stderr}\n")
        return False


def sync_code():
    """로컬 코드를 EC2에 동기화 (Git)"""
    print_header("코드 동기화 (Git)")
    
    # 로컬에서 Git push
    print("\n[로컬] Git 변경사항 확인...")
    
    # Git status 확인
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=LOCAL_PROJECT_PATH,
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip():
        print(f"변경된 파일:\n{result.stdout}")
        
        # Git add
        print("[로컬] Git add...")
        subprocess.run(
            ["git", "add", "."],
            cwd=LOCAL_PROJECT_PATH,
            capture_output=True
        )
        
        # Git commit
        commit_msg = f"Auto sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"[로컬] Git commit: {commit_msg}")
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=LOCAL_PROJECT_PATH,
            capture_output=True,
            text=True
        )
        
        # Git push
        print("[로컬] Git push...")
        result = subprocess.run(
            ["git", "push", "origin", "dev"],
            cwd=LOCAL_PROJECT_PATH,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ 로컬 Git push 완료")
        else:
            if "Everything up-to-date" in result.stderr:
                print("✓ 이미 최신 상태")
            else:
                print(f"⚠ Git push 경고: {result.stderr}")
    else:
        print("✓ 변경사항 없음 (최신 상태)")
    
    # EC2에서 Git pull
    print("\n[EC2] Git pull...")
    returncode = run_remote_command(
        f"cd {PROJECT_PATH} && git pull origin dev",
        show_output=True
    )
    
    if returncode == 0:
        print("✓ EC2 코드 동기화 완료\n")
        return True
    else:
        print("✗ EC2 코드 동기화 실패\n")
        return False


def check_spark_cluster():
    """Spark 클러스터 상태 확인 및 시작"""
    print_header("Spark 클러스터 확인")
    
    returncode, stdout, stderr = run_remote_command("jps", show_output=False)
    
    has_master = "Master" in stdout
    has_worker = "Worker" in stdout
    
    if has_master and has_worker:
        print("✓ Spark 클러스터 실행 중")
        print("\n실행 중인 프로세스:")
        for line in stdout.split('\n'):
            if 'Master' in line or 'Worker' in line:
                print(f"  {line}")
        print()
        return True
    else:
        print("⚠ Spark 클러스터 미실행")
        
        if not has_master:
            print("  - Master: 중지됨")
        if not has_worker:
            print("  - Worker: 중지됨")
        
        print("\nSpark 클러스터 시작 중...")
        returncode = run_remote_command("start-spark", show_output=True)
        
        if returncode == 0:
            print("\n✓ Spark 클러스터 시작 완료\n")
            return True
        else:
            print("\n✗ Spark 클러스터 시작 실패\n")
            return False


def run_phase1_lake_to_dwh2():
    """Phase 1: Lake → DWH2 실행"""
    print_header("PHASE 1: Lake → DWH2 Pipeline")
    print("CSV → Lake → DWH2 (Dimensions + Facts)\n")
    
    command = f"cd {PROJECT_PATH} && python3 -m spark_etl.lake_to_dwh2.run_pipe_spark"
    
    returncode = run_remote_command(command, show_output=True)
    
    if returncode == 0:
        print("\n✓ Phase 1 완료: DWH2 테이블 생성 완료")
        return True
    else:
        print("\n✗ Phase 1 실패")
        return False


def run_phase2_dwh_to_dm():
    """Phase 2: DWH2 → DM 실행"""
    print_header("PHASE 2: DWH2 → DM Pipeline")
    print("DWH2 → DM (원본 테이블 + 파생 데이터)\n")
    
    command = f"cd {PROJECT_PATH} && python3 -m spark_etl.main_dm.run_pipeline"
    
    returncode = run_remote_command(command, show_output=True)
    
    if returncode == 0:
        print("\n✓ Phase 2 완료: DM 테이블 및 파생 데이터 생성 완료")
        return True
    else:
        print("\n✗ Phase 2 실패")
        return False


def run_full_pipeline():
    """통합 파이프라인 실행 (둘 다 한 번에)"""
    print_header("통합 파이프라인 실행")
    print("CSV → Lake → DWH2 → DM (전체 과정)\n")
    
    command = f"cd {PROJECT_PATH} && python3 -m spark_etl.run_full_pipeline2"
    
    returncode = run_remote_command(command, show_output=True)
    
    if returncode == 0:
        print("\n✓ 전체 파이프라인 완료!")
        return True
    else:
        print("\n✗ 파이프라인 실패")
        return False


def show_menu():
    """실행 메뉴 표시"""
    print("\n" + "=" * 80)
    print(" 실행할 파이프라인 선택")
    print("=" * 80)
    print("\n[1] 전체 파이프라인 (Lake → DWH2 → DM)")
    print("[2] Phase 1만 실행 (Lake → DWH2)")
    print("[3] Phase 2만 실행 (DWH2 → DM)")
    print("[0] 종료")
    print("\n선택 (0-3): ", end='')
    
    choice = input().strip()
    return choice


def main():
    """메인 실행"""
    print("\n" + "=" * 80)
    print(" AWS Spark 파이프라인 원격 실행 시스템")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 연결 확인
    if not check_connection():
        print("\n❌ EC2 연결 실패. 종료합니다.")
        sys.exit(1)
    
    # 2. 코드 동기화
    if not sync_code():
        print("\n⚠ 코드 동기화 실패. 계속하시겠습니까? (y/n): ", end='')
        if input().lower() != 'y':
            sys.exit(1)
    
    # 3. Spark 클러스터 확인
    if not check_spark_cluster():
        print("\n❌ Spark 클러스터 시작 실패. 종료합니다.")
        sys.exit(1)
    
    # 4. 메뉴 선택
    choice = show_menu()
    
    success = False
    
    if choice == '1':
        # 전체 파이프라인
        success = run_full_pipeline()
        
    elif choice == '2':
        # Phase 1만
        success = run_phase1_lake_to_dwh2()
        
    elif choice == '3':
        # Phase 2만
        success = run_phase2_dwh_to_dm()
        
    elif choice == '0':
        print("\n종료합니다.")
        sys.exit(0)
        
    else:
        print("\n잘못된 선택입니다.")
        sys.exit(1)
    
    # 5. 완료
    print("\n" + "=" * 80)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if success:
        print("\n✅ 파이프라인 실행 성공!")
        print("\n다음 단계:")
        print("  1. 데이터 확인: SELECT * FROM dm.derived_data LIMIT 10;")
        print("  2. API 서버: uvicorn service.api.main:app --reload")
        print("  3. 대시보드: streamlit run service/dashboard/app.py")
        sys.exit(0)
    else:
        print("\n❌ 파이프라인 실행 실패")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)