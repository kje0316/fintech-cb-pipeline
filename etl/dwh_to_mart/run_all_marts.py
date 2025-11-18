"""
데이터 마트 전체 적재 Orchestrator
================================

모든 데이터 마트를 순차적으로 적재하는 메인 스크립트입니다.

실행 순서:
1. dm_industry_financial_ratios_stats - 대분류 업종별 재무비율 통계 (19개 업종 × 18개 지표)
2. mart_market_kpi_monthly - 월별 시장 KPI (12개월)
3. mart_industry_default_trend - 대분류 업종별 월별 부도 추세 (19개 업종 × 12개월)
4. mart_credit_grade_distribution_monthly - 월별 신용등급 분포 (12개월 × 11개 등급)
5. mart_industry_risk_ranking - 대분류 업종별 리스크 랭킹 (19개 업종)

실행 방법:
  python etl/dwh_to_mart/run_all_marts.py
  python etl/dwh_to_mart/run_all_marts.py --rebuild  # 테이블 재생성 후 적재

소요 시간: 약 5-10분
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class MartOrchestrator:
    def __init__(self, rebuild=False):
        self.rebuild = rebuild
        self.start_time = datetime.now()
        self.results = []

    def print_header(self):
        """실행 헤더 출력"""
        print("\n" + "="*100)
        print("  데이터 마트 전체 적재 Orchestrator".center(100))
        print("  fintech-cb-pipeline".center(100))
        print("="*100)
        print(f"\n시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"재구축 모드: {'ON (테이블 재생성)' if self.rebuild else 'OFF'}\n")

    def run_script(self, script_path, description, args=None):
        """
        Python 스크립트 실행

        Parameters:
        -----------
        script_path : str
            실행할 스크립트 경로 (프로젝트 루트 기준)
        description : str
            스크립트 설명
        args : list, optional
            추가 인자
        """
        print("\n" + "-"*100)
        print(f"[{len(self.results) + 1}] {description}")
        print("-"*100)

        start_time = time.time()

        # 스크립트 실행
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )

            elapsed_time = time.time() - start_time

            if result.returncode == 0:
                print(result.stdout)
                self.results.append({
                    'script': script_path,
                    'description': description,
                    'status': '✓ SUCCESS',
                    'elapsed_time': elapsed_time
                })
                print(f"\n✓ 완료 (소요시간: {elapsed_time:.2f}초)")
                return True
            else:
                print(result.stdout)
                print(result.stderr)
                self.results.append({
                    'script': script_path,
                    'description': description,
                    'status': '✗ FAILED',
                    'elapsed_time': elapsed_time,
                    'error': result.stderr
                })
                print(f"\n✗ 실패 (소요시간: {elapsed_time:.2f}초)")
                return False

        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            self.results.append({
                'script': script_path,
                'description': description,
                'status': '✗ TIMEOUT',
                'elapsed_time': elapsed_time
            })
            print(f"\n✗ 타임아웃 (10분 초과)")
            return False

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results.append({
                'script': script_path,
                'description': description,
                'status': '✗ ERROR',
                'elapsed_time': elapsed_time,
                'error': str(e)
            })
            print(f"\n✗ 오류: {str(e)}")
            return False

    def print_summary(self):
        """실행 결과 요약 출력"""
        end_time = datetime.now()
        total_elapsed = (end_time - self.start_time).total_seconds()

        print("\n\n" + "="*100)
        print("  실행 결과 요약".center(100))
        print("="*100 + "\n")

        print(f"{'#':<5} {'스크립트':<50} {'상태':<15} {'소요시간':<15}")
        print("-"*100)

        for i, result in enumerate(self.results, 1):
            script_name = Path(result['script']).name
            status = result['status']
            elapsed = f"{result['elapsed_time']:.2f}초"

            print(f"{i:<5} {script_name:<50} {status:<15} {elapsed:<15}")

        print("-"*100)

        success_count = sum(1 for r in self.results if r['status'] == '✓ SUCCESS')
        failed_count = sum(1 for r in self.results if '✗' in r['status'])

        print(f"\n성공: {success_count}개 / 실패: {failed_count}개 / 총: {len(self.results)}개")
        print(f"전체 소요 시간: {total_elapsed:.2f}초 ({total_elapsed/60:.2f}분)")

        if failed_count == 0:
            print("\n" + "="*100)
            print("  ✓ 모든 마트 적재 완료!".center(100))
            print("="*100)
            return True
        else:
            print("\n" + "="*100)
            print("  ✗ 일부 마트 적재 실패 - 위 오류 확인 필요".center(100))
            print("="*100)
            return False

    def run_all(self):
        """모든 마트 적재 실행"""
        self.print_header()

        # 1. 테이블 스키마 재생성 (rebuild 모드)
        if self.rebuild:
            print("\n[재구축 모드] 마트 테이블 스키마 재생성 중...")
            success = self.run_script(
                "etl/dwh_to_mart/build_dm_industry_financial_stats.py",
                "재무비율 통계 마트 테이블 생성",
                ["--rebuild"]
            )
            if not success:
                print("\n✗ 테이블 생성 실패. 중단합니다.")
                return False

        # 2. 대분류 업종별 재무비율 통계
        self.run_script(
            "etl/dwh_to_mart/load_dm_industry_financial_ratios_stats.py",
            "대분류 업종별 재무비율 통계 마트 적재 (19개 업종 × 18개 지표)"
        )

        # 3. 월별 시장 KPI
        self.run_script(
            "etl/dwh_to_mart/python/load_mart_market_kpi_monthly.py",
            "월별 시장 KPI 마트 적재 (Altman Z-Score 포함, 12개월)"
        )

        # 4. 대분류 업종별 월별 부도 추세
        self.run_script(
            "etl/dwh_to_mart/python/load_mart_industry_default_trend.py",
            "대분류 업종별 월별 부도 추세 마트 적재 (19개 업종 × 12개월)"
        )

        # 5. 월별 신용등급 분포
        self.run_script(
            "etl/dwh_to_mart/python/load_mart_credit_grade_distribution.py",
            "월별 신용등급 분포 마트 적재 (12개월 × 11개 등급)"
        )

        # 6. 대분류 업종별 리스크 랭킹
        self.run_script(
            "etl/dwh_to_mart/python/load_mart_industry_risk_ranking.py",
            "대분류 업종별 리스크 랭킹 마트 적재 (19개 업종, TOP 5 위험/안전)"
        )

        # 최종 요약
        return self.print_summary()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='데이터 마트 전체 적재 Orchestrator')
    parser.add_argument('--rebuild', action='store_true',
                        help='마트 테이블을 삭제하고 재생성 (기존 데이터 삭제됨)')
    args = parser.parse_args()

    orchestrator = MartOrchestrator(rebuild=args.rebuild)

    try:
        success = orchestrator.run_all()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n✗ 예상치 못한 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
