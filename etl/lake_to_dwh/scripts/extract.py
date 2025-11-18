import pandas as pd
import yaml
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def extract_from_lake(column_map_yaml_path):
    """
    PostgreSQL lake.raw_data 테이블에서 데이터를 로드하고,
    두 번째 컬럼에 고유 ID(COMPANY_ID)를 부여합니다.

    lake.raw_data는 이미 영문 컬럼명을 가지고 있지만,
    COMPANY_ID가 없으므로 추가해야 합니다.
    """

    print(f"PostgreSQL lake.raw_data 테이블에서 데이터 로드 중...")

    try:
        # 1. DB에서 데이터 로드
        from etl.lake_to_dwh.scripts.load_to_postgres import get_db_engine
        engine = get_db_engine()

        data_df = pd.read_sql("SELECT * FROM lake.raw_data", engine)
        print(f"✓ 데이터 로드 완료: {len(data_df):,}행, {len(data_df.columns)}개 컬럼")

        # 2. 컬럼명을 대문자로 통일
        data_df.columns = data_df.columns.str.upper()

        # 3. COMPANY_ID가 이미 있는지 확인
        if 'COMPANY_ID' in data_df.columns:
            print("✓ COMPANY_ID가 이미 존재합니다. 기존 ID 사용.")
            return data_df

        # 4. COMPANY_ID 추가 (두 번째 컬럼에 삽입)
        unique_ids = pd.Series(range(1, len(data_df)+1), name='COMPANY_ID')

        if len(data_df.columns) < 1:
            raise ValueError("테이블에 컬럼이 충분하지 않습니다.")

        # 두 번째 위치에 COMPANY_ID 삽입
        data_df.insert(1, 'COMPANY_ID', unique_ids)
        print(f"✓ 모든 행에 고유한 COMPANY_ID를 두 번째 컬럼에 부여 완료 (1~{len(data_df):,}).")

        # 5. columns_map.yaml 로드 (검증용)
        print(f"'{column_map_yaml_path}'에서 컬럼 매핑 로드 중...")
        with open(column_map_yaml_path, 'r', encoding='utf-8') as f:
            columns_map = yaml.safe_load(f)

        # 컬럼 수 검증
        expected_columns = len(columns_map) + 1  # +1 for COMPANY_ID
        if len(data_df.columns) != expected_columns:
            print(f"⚠ 경고: 컬럼 수 불일치 - 실제: {len(data_df.columns)}, 예상: {expected_columns}")

        print(f"✓ 데이터 추출 완료 ({len(data_df.columns)}개 컬럼).")
        return data_df

    except Exception as e:
        print(f"✗ lake.raw_data에서 데이터 추출 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_data(data_path, column_map_yaml_path):
    """
    데이터를 로드하고, 두 번째 컬럼에 고유 ID를 부여한 후,
    columns_map.yaml의 영문 컬럼명으로 통일합니다.
    """

    print(f"'{data_path}'에서 데이터 로드 중...")
    print(f"'{column_map_yaml_path}'에서 컬럼 매핑 로드 중...")

    try:
        # 1. 원본 데이터 로드
        data_df = pd.read_csv(data_path, encoding='cp949')
        original_columns_count = len(data_df.columns)

        # 2. columns_map.yaml 로드
        with open(column_map_yaml_path, 'r', encoding='utf-8') as f:
            columns_map = yaml.safe_load(f)

        # 3. 모든 행에 고유한 ID 부여 (두 번째 컬럼에 삽입)
        unique_ids = pd.Series(range(1, len(data_df)+1), name='COMPANY_ID')
        if len(data_df.columns) < 1:
            raise ValueError("원본 데이터에 컬럼이 충분하지 않아 ID를 두 번째 컬럼에 삽입할 수 없습니다.")
        data_df.insert(1, 'COMPANY_ID', unique_ids)
        print("모든 행에 고유한 ID를 두 번째 컬럼에 부여 완료.")

        # 4. 컬럼명 영문으로 변경
        print("컬럼명 통일 중...")

        # columns_map에서 영문 컬럼명 리스트 생성
        # (원본 데이터 컬럼 개수 + COMPANY_ID = columns_map 개수 + 1)
        if len(data_df.columns) != len(columns_map) + 1:
            print(f"경고: ID 삽입 후 데이터 컬럼 수({len(data_df.columns)})와 ")
            print(f"       columns_map 컬럼 수 + 1({len(columns_map) + 1})이 일치하지 않습니다.")
            # 원본 컬럼 개수가 맞는지 확인
            if original_columns_count != len(columns_map):
                raise ValueError(f"원본 데이터 컬럼 수({original_columns_count})와 columns_map({len(columns_map)})이 일치하지 않습니다.")

        # 첫 번째 컬럼 + COMPANY_ID + 나머지 컬럼들
        new_columns = [list(columns_map.keys())[0], 'COMPANY_ID'] + list(columns_map.keys())[1:]
        data_df.columns = new_columns

        print(f"컬럼명 통일 완료 ({len(new_columns)}개 컬럼).")

        return data_df

    except FileNotFoundError as e:
        print(f"오류: 파일을 찾을 수 없습니다 - {e}")
        return None

    except Exception as e: # Catch general exceptions for robustness
        print(f"데이터 추출 및 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None
