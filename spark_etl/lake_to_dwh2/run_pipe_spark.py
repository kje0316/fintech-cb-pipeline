import yaml
from spark_etl.lake_to_dwh2.scripts.extract_spark import extract_data, extract_from_lake
from spark_etl.lake_to_dwh2.scripts.cleansing_spark import cleanse_data
from spark_etl.lake_to_dwh2.scripts.build_dw_spark import create_dims, create_facts
from spark_etl.lake_to_dwh2.scripts.load_to_postgres_spark import create_schema, get_spark_session
from shared.config_loader import config

# Define paths (shared/config_loader에서 가져옴)
RAW_DATA_PATH = config['paths']['raw_data']
COLUMN_REFERENCE_PATH = config['paths']['columns_map']  # columns_map.yaml 사용
COL_TYPES_PATH = 'config/col_types.yaml'
DW_COLUMNS_PATH = 'config/dw_columns2.yaml'
SCHEMA_SQL_PATH = 'spark_etl/lake_to_dwh2/schema_dwh2.sql'

# ETL 데이터 소스 설정 (config에서 읽기)
ETL_SOURCE = config.get('etl', {}).get('source', 'csv')


def run_pipeline():
    """
    전체 ETL 파이프라인을 실행합니다. (Spark 버전)
    """
    print("--- Starting ETL Pipeline (Spark Version) ---")

    # SparkSession 초기화
    spark = get_spark_session()
    print(f"✓ SparkSession 초기화 완료")
    print(f"  - App Name: {spark.sparkContext.appName}")
    print(f"  - Spark Version: {spark.version}")

    # 1. Extract data
    print(f"\nStep 2: Extracting data from '{ETL_SOURCE}'...")

    if ETL_SOURCE == 'lake':
        # lake.raw_data 테이블에서 데이터 추출
        df_raw = extract_from_lake(COLUMN_REFERENCE_PATH)
    elif ETL_SOURCE == 'csv':
        # CSV 파일에서 데이터 추출
        df_raw = extract_data(RAW_DATA_PATH, COLUMN_REFERENCE_PATH)
    else:
        print(f"✗ 알 수 없는 ETL 소스: {ETL_SOURCE}")
        print("  config/local_settings.yaml의 etl.source를 'lake' 또는 'csv'로 설정하세요.")
        spark.stop()
        return

    if df_raw is None:
        print("Data extraction failed. Aborting pipeline.")
        spark.stop()
        return
    
    print(f"Data extraction successful. Rows: {df_raw.count()}, Columns: {len(df_raw.columns)}")

    # 2. Cleanse data
    print("\nStep 3: Cleansing data...")
    cleaned_data = cleanse_data(df_raw, COL_TYPES_PATH)
    print(f"Data cleansing successful. Rows: {cleaned_data.count()}, Columns: {len(cleaned_data.columns)}")

    # 3. Create Schema
    print("\nStep 1: Creating database schema...")
    create_schema(SCHEMA_SQL_PATH)
    print("Schema creation successful.")

    # 4. Build Data Warehouse
    print("\nStep 4: Building Data Warehouse...")
    with open(DW_COLUMNS_PATH, 'r', encoding='utf-8') as f:
        dw_columns = yaml.safe_load(f)
    
    print("  - Creating and loading dimension tables...")
    dim_company, dim_time, dim_industry = create_dims(cleaned_data, dw_columns)

    print("  - Creating and loading fact tables...")
    create_facts(cleaned_data, dim_company, dim_time, dw_columns)
    print("Data Warehouse build completed successfully.")
    
    print("\n--- ETL Pipeline Finished ---")
    
    # SparkSession 종료
    spark.stop()
    print("✓ SparkSession 종료 완료")


if __name__ == "__main__":
    run_pipeline()
