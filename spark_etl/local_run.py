"""
로컬에서 AWS EC2 Spark 통합 파이프라인 원격 실행

통합 ETL 파이프라인:
CSV → Lake → DWH2 (Dimensions + Facts) → DM (원본 + 파생)
각 팀원의 로컬 Docker PostgreSQL에 자동 저장
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ==================== 설정 ====================
# AWS 접속 정보
SSH_KEY = r"C:\Users\user\.ssh\elice-aws-key.pem"
EC2_HOST = "ubuntu@3.104.157.213"
PROJECT_PATH = "~/fintech-cb-pipeline"

print(f"\n🔍 연결 정보:")
print(f"  - SSH 키: {SSH_KEY}")
print(f"  - 키 존재: {Path(SSH_KEY).exists()}")
print(f"  - EC2 호스트: {EC2_HOST}")

# 로컬 프로젝트 경로
LOCAL_PROJECT_PATH = Path(__file__).parent
# ==============================================


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_remote_command(command, show_output=True):
    """
    SSH로 원격 명령 실행 (인코딩 문제 해결)
    """
    ssh_cmd = [
        "ssh",
        "-i", SSH_KEY,
        EC2_HOST,
        command
    ]
    
    if show_output:
        try:
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            for line in process.stdout:
                try:
                    print(line, end='')
                except UnicodeEncodeError:
                    print(line.encode('utf-8', errors='ignore').decode('utf-8'), end='')
            
            process.wait()
            return process.returncode
            
        except Exception as e:
            print(f"\n⚠️ 출력 중 에러 (무시): {e}")
            return 0
    else:
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            print(f"\n⚠️ 명령 실행 에러: {e}")
            return 1, "", str(e)


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


def setup_db_tunnel():
    """로컬 DB → EC2 포트 포워딩 생성"""
    print_header("DB 터널 설정")
    
    # 로컬 Docker PostgreSQL 확인
    print("로컬 Docker PostgreSQL 확인 중...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=my_postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "my_postgres" not in result.stdout:
            print("⚠️ 로컬 Docker PostgreSQL이 실행되지 않았습니다.")
            print("\n다음 명령어를 실행하세요:")
            print("  docker-compose up -d")
            return False, None
        
        print("✓ 로컬 PostgreSQL 실행 중\n")
    except Exception as e:
        print(f"⚠️ Docker 확인 실패: {e}")
        return False, None
    
    # 로컬 포트 포워딩 생성 (백그라운드 프로세스)
    print("DB 터널 생성 중...")
    print("  로컬 PC에서 EC2로 터널 생성")
    print("  로컬 5432 ← 터널 ← EC2 15432")
    
    # SSH 터널 프로세스 시작 (백그라운드)
    tunnel_cmd = [
        "ssh",
        "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=60",
        "-o", "ServerAliveCountMax=3",
        "-R", "15432:localhost:5432",  # EC2:15432 → 로컬:5432
        "-N",  # 명령 실행 안 함
        EC2_HOST
    ]
    
    try:
        # 백그라운드로 터널 프로세스 시작
        tunnel_process = subprocess.Popen(
            tunnel_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 터널이 생성될 시간 대기
        import time
        time.sleep(3)
        
        # 프로세스가 살아있는지 확인
        if tunnel_process.poll() is None:
            print("✓ DB 터널 생성 완료\n")
            return True, tunnel_process
        else:
            stdout, stderr = tunnel_process.communicate()
            print(f"✗ 터널 생성 실패: {stderr}\n")
            return False, None
            
    except Exception as e:
        print(f"✗ 터널 생성 오류: {e}\n")
        return False, None


def cleanup_db_tunnel(tunnel_process):
    """DB 터널 정리"""
    if tunnel_process and tunnel_process.poll() is None:
        try:
            tunnel_process.terminate()
            tunnel_process.wait(timeout=5)
        except:
            try:
                tunnel_process.kill()
            except:
                pass


def check_spark_cluster():
    """Spark 클러스터 상태 확인 및 시작"""
    print_header("Spark 클러스터 확인")
    
    print("\n클러스터 상태 확인 중...")
    
    ssh_cmd = [
        "ssh",
        "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        EC2_HOST,
        "jps | grep -E 'Master|Worker'"
    ]
    
    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        output = result.stdout
    except Exception as e:
        print(f"✗ 상태 확인 실패: {e}")
        output = ""
    
    master_running = "Master" in output
    worker_running = "Worker" in output
    
    if master_running and worker_running:
        print("✓ Spark 클러스터 실행 중")
        print("  - Master: 실행 중")
        print("  - Worker: 실행 중\n")
        return True
    
    print("⚠ Spark 클러스터 미실행")
    print(f"  - Master: {'실행 중' if master_running else '중지됨'}")
    print(f"  - Worker: {'실행 중' if worker_running else '중지됨'}")
    
    print("\nSpark 클러스터 시작 중...")
    
    returncode = run_remote_command(
        "export SPARK_HOME=~/spark-3.2.4 && "
        "$SPARK_HOME/sbin/start-master.sh && "
        "sleep 5 && "
        "$SPARK_HOME/sbin/start-worker.sh spark://ip-172-31-4-65.ap-southeast-2.compute.internal:7077",
        show_output=True
    )
    
    if returncode == 0:
        print("✓ Spark 클러스터 시작 완료\n")
        return True
    else:
        print("✗ Spark 클러스터 시작 실패")
        return False


def run_full_pipeline():
    """통합 파이프라인 실행"""
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


def main():
    """메인 실행"""
    print("\n" + "=" * 80)
    print(" AWS Spark 파이프라인 → 로컬 DB 저장")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    tunnel_process = None
    
    try:
        # 1. 연결 확인
        if not check_connection():
            print("\n❌ EC2 연결 실패. 종료합니다.")
            sys.exit(1)
        
        # 2. DB 터널 설정
        success, tunnel_process = setup_db_tunnel()
        if not success:
            print("\n❌ DB 터널 설정 실패. 종료합니다.")
            sys.exit(1)
             
        # 3. Spark 클러스터 확인
        if not check_spark_cluster():
            print("\n❌ Spark 클러스터 시작 실패. 종료합니다.")
            sys.exit(1)
        
        # 4. 전체 파이프라인 자동 실행
        print("\n🚀 전체 파이프라인 자동 실행")
        pipeline_success = run_full_pipeline()
        
        # 5. 완료
        print("\n" + "=" * 80)
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if pipeline_success:
            print("\n✅ 파이프라인 실행 성공!")
            print("\n💾 데이터가 로컬 Docker PostgreSQL에 저장되었습니다!")
            print("\n데이터 확인:")
            print("  docker exec -it my_postgres psql -U hengu -d dbdb")
            print("  \\dt dm.*")
            print("  SELECT * FROM dm.derived_data LIMIT 5;")
            sys.exit(0)
        else:
            print("\n❌ 파이프라인 실행 실패")
            sys.exit(1)
    
    finally:
        # 터널 정리
        if tunnel_process:
            print("\n터널 정리 중...")
            cleanup_db_tunnel(tunnel_process)
            print("✓ 정리 완료")


if __name__ == "__main__":
    tunnel_process = None
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 사용자에 의해 중단되었습니다.")
        if 'tunnel_process' in locals() and tunnel_process:
            cleanup_db_tunnel(tunnel_process)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if 'tunnel_process' in locals() and tunnel_process:
            cleanup_db_tunnel(tunnel_process)
        sys.exit(1)