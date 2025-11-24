from pyspark.sql import SparkSession
from pyspark.sql.functions import col, monotonically_increasing_id, row_number, lit
from pyspark.sql.window import Window
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
        from spark_etl.lake_to_dwh2.scripts.load_to_postgres_spark import get_spark_session, get_jdbc_properties
        
        spark = get_spark_session()
        jdbc_url, properties = get_jdbc_properties()

        data_df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "lake.raw_data") \
            .option("user", properties["user"]) \
            .option("password", properties["password"]) \
            .option("driver", properties["driver"]) \
            .load()
        
        row_count = data_df.count()
        col_count = len(data_df.columns)
        print(f"✓ 데이터 로드 완료: {row_count:,}행, {col_count}개 컬럼")

        # 2. 컬럼명을 대문자로 통일
        for column in data_df.columns:
            data_df = data_df.withColumnRenamed(column, column.upper())

        # 3. COMPANY_ID가 이미 있는지 확인
        if 'COMPANY_ID' in data_df.columns:
            print("✓ COMPANY_ID가 이미 존재합니다. 기존 ID 사용.")
            return data_df

        # 4. COMPANY_ID 추가 (두 번째 컬럼에 삽입)
        # Spark에서는 row_number()를 사용하여 순차적 ID 생성
        window = Window.orderBy(lit(1))
        data_df = data_df.withColumn("COMPANY_ID_TEMP", row_number().over(window))
        
        # 컬럼 순서 재배열 (첫 번째 컬럼, COMPANY_ID, 나머지)
        first_col = data_df.columns[0]
        remaining_cols = [c for c in data_df.columns if c not in [first_col, 'COMPANY_ID_TEMP']]
        
        data_df = data_df.select(first_col, 
                                 col("COMPANY_ID_TEMP").alias("COMPANY_ID"), 
                                 *remaining_cols)
        
        print(f"✓ 모든 행에 고유한 COMPANY_ID를 두 번째 컬럼에 부여 완료 (1~{row_count:,}).")

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
    CSV 파일에서 데이터를 로드하고, 두 번째 컬럼에 고유 ID를 부여한 후,
    columns_map.yaml의 영문 컬럼명으로 통일합니다.
    """

    print(f"'{data_path}'에서 데이터 로드 중...")
    print(f"'{column_map_yaml_path}'에서 컬럼 매핑 로드 중...")

    try:
        from spark_etl.lake_to_dwh2.scripts.load_to_postgres_spark import get_spark_session
        
        spark = get_spark_session()
        
        # 1. 원본 데이터 로드 (cp949 인코딩)
        data_df = spark.read \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .option("encoding", "EUC-KR") \
            .csv(data_path)
        
        original_columns_count = len(data_df.columns)

        # 2. columns_map.yaml 로드
        with open(column_map_yaml_path, 'r', encoding='utf-8') as f:
            columns_map = yaml.safe_load(f)

        # 3. 모든 행에 고유한 ID 부여
        window = Window.orderBy(lit(1))
        data_df = data_df.withColumn("COMPANY_ID", row_number().over(window))
        
        print("모든 행에 고유한 ID를 두 번째 컬럼에 부여 완료.")

        # 4. 컬럼명 영문으로 변경
        print("컬럼명 통일 중...")

        # 첫 번째 영문 컬럼명 + COMPANY_ID + 나머지 영문 컬럼명
        new_columns = [list(columns_map.keys())[0], 'COMPANY_ID'] + list(columns_map.keys())[1:]
        
        # 현재 컬럼 순서 (한글 컬럼들 + COMPANY_ID)
        old_columns = data_df.columns
        
        # COMPANY_ID를 제외한 원본 컬럼들
        original_data_cols = [c for c in old_columns if c != 'COMPANY_ID']
        
        # 검증
        if len(original_data_cols) != len(columns_map):
            print(f"경고: 원본 컬럼 수({len(original_data_cols)})와 ")
            print(f"       columns_map 컬럼 수({len(columns_map)})이 일치하지 않습니다.")
        
        # 컬럼명 매핑 생성 (한글 -> 영문)
        # 첫 번째 원본 컬럼 -> 첫 번째 영문명
        # 나머지 원본 컬럼들 -> 나머지 영문명
        rename_map = {}
        for i, old_col in enumerate(original_data_cols):
            if i < len(columns_map):
                new_col = list(columns_map.keys())[i]
                rename_map[old_col] = new_col
        
        # 컬럼명 변경
        for old_name, new_name in rename_map.items():
            data_df = data_df.withColumnRenamed(old_name, new_name)
        
        # COMPANY_ID를 두 번째 위치로 이동
        first_col = list(columns_map.keys())[0]
        remaining_cols = [c for c in list(columns_map.keys())[1:]]
        
        final_col_order = [first_col, 'COMPANY_ID'] + remaining_cols
        data_df = data_df.select(*[col(c) for c in final_col_order])

        print(f"컬럼명 통일 완료 ({len(final_col_order)}개 컬럼).")

        return data_df

    except FileNotFoundError as e:
        print(f"오류: 파일을 찾을 수 없습니다 - {e}")
        return None

    except Exception as e:
        print(f"데이터 추출 및 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None