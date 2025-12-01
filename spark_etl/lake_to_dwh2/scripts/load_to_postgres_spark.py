from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, to_date, when
import yaml
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL


def get_spark_session():
    """
    SparkSession을 생성하고 반환합니다.
    """
    from pathlib import Path
    import os
    
    # 프로젝트 루트에서 JDBC jar 경로 찾기
    project_root = Path(__file__).resolve().parents[3]
    jdbc_jar = f"{os.path.expanduser('~/spark-3.2.4')}/jars/postgresql-42.7.1.jar"
    
    # JDBC jar를 SPARK_CLASSPATH에 추가
    os.environ['SPARK_CLASSPATH'] = str(jdbc_jar)
    
    spark = SparkSession.builder \
        .appName("ETL_Lake_to_DWH") \
        .config("spark.driver.extraClassPath", str(jdbc_jar)) \
        .config("spark.executor.extraClassPath", str(jdbc_jar)) \
        .getOrCreate()
    
    return spark


def get_jdbc_properties():
    """
    DB_URL을 파싱하여 JDBC 연결 정보를 반환합니다.
    DB_URL 형식: postgresql://user:password@host:port/database
    """
    # postgresql://user:password@host:port/database 파싱
    import re
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, DB_URL)
    
    if not match:
        raise ValueError(f"Invalid DB_URL format: {DB_URL}")
    
    user, password, host, port, database = match.groups()
    
    jdbc_url = f"jdbc:postgresql://{host}:{port}/{database}"
    
    properties = {
        "user": user,
        "password": password,
        "driver": "org.postgresql.Driver"
    }
    
    return jdbc_url, properties


def create_schema(sql_file_path):
    """
    SQL 파일에 정의된 스키마를 PostgreSQL 데이터베이스에 생성합니다.
    Spark에서는 직접 DDL 실행이 제한적이므로 psycopg2 사용
    """
    print(f"스키마 파일 '{sql_file_path}' 실행 중...")
    
    try:
        # psycopg2로 DDL 실행 (Spark는 DDL 실행에 제한적)
        import psycopg2
        from urllib.parse import urlparse
        
        # DB_URL 파싱
        result = urlparse(DB_URL)
        
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        cursor = conn.cursor()
        for command in sql_commands.split(';'):
            stripped_command = command.strip()
            if stripped_command:
                cursor.execute(stripped_command)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("스키마 생성 완료.")
        
    except Exception as e:
        print(f"스키마 생성 중 오류 발생: {e}")
        raise


def load_data(df, table_name):
    """
    변환된 Spark DataFrame을 PostgreSQL에 적재합니다.
    table_name: 'schema.table' 또는 'table' 형식
    """
    if df.count() == 0:
        print(f"적재할 데이터가 없습니다: {table_name}")
        return

    spark = get_spark_session()
    jdbc_url, properties = get_jdbc_properties()
    
    print(f"PostgreSQL에 테이블 '{table_name}' 데이터 적재 시작...")

    # schema.table 분리
    if '.' in table_name:
        schema, table = table_name.split('.', 1)
    else:
        schema = 'public'
        table = table_name

    try:
        # TRUNCATE는 psycopg2로 실행
        import psycopg2
        from urllib.parse import urlparse
        
        result = urlparse(DB_URL)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        
        cursor = conn.cursor()
        cursor.execute(f"TRUNCATE TABLE {schema}.{table} RESTART IDENTITY CASCADE;")
        conn.commit()
        cursor.close()
        conn.close()
        
        # Spark로 데이터 적재
        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", f"{schema}.{table}") \
            .option("user", properties["user"]) \
            .option("password", properties["password"]) \
            .option("driver", properties["driver"]) \
            .mode("append") \
            .save()
        
        row_count = df.count()
        print(f"테이블 '{schema}.{table}' 데이터 적재 완료. {row_count} rows.")
        
    except Exception as e:
        print(f"테이블 '{table_name}' 데이터 적재 중 오류 발생: {e}")
        raise


def load_table_from_db(table_name, yaml_path):
    """
    데이터베이스에서 테이블을 로드하여 Spark DataFrame으로 반환합니다.
    col_types.yaml으로 타입 참고하여 로드함.
    """
    spark = get_spark_session()
    jdbc_url, properties = get_jdbc_properties()
    
    print(f"YAML 파일 '{yaml_path}'에서 타입 정보 로드 중...")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            col_types = yaml.safe_load(f)
        
        # PostgreSQL은 기본적으로 소문자
        col_types_lower = {}
        for type_name, columns in col_types.items():
            if columns:
                col_types_lower[type_name] = [col.lower() for col in columns]
            else:
                col_types_lower[type_name] = []
        
        print(f"✓ YAML 파일 로드 완료")
        
    except FileNotFoundError:
        print(f"경고: YAML 파일을 찾을 수 없습니다: {yaml_path}")
        col_types_lower = {'date': [], 'str': [], 'numeric': []}
    except Exception as e:
        print(f"경고: YAML 파일 로드 중 오류: {e}")
        col_types_lower = {'date': [], 'str': [], 'numeric': []}

    # PostgreSQL에서 데이터 로드
    if '.' in table_name:
        full_table_name = table_name
    else:
        full_table_name = f"public.{table_name}"

    print(f"\nPostgreSQL에서 '{full_table_name}' 테이블 로드 중...")

    try:
        df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", full_table_name) \
            .option("user", properties["user"]) \
            .option("password", properties["password"]) \
            .option("driver", properties["driver"]) \
            .load()
        
        row_count = df.count()
        col_count = len(df.columns)
        print(f"✓ 테이블 로드 완료 ({row_count:,}행, {col_count}개 컬럼)")
        
    except Exception as e:
        print(f"[오류] 테이블 로드 실패: {e}")
        raise

    # 실제 테이블에 존재하는 컬럼만 필터링
    df_columns_lower = [col.lower() for col in df.columns]
    col_mapping = {col.lower(): col for col in df.columns}

    date_cols = [col_mapping[c] for c in col_types_lower.get('date', []) if c in df_columns_lower]
    str_cols = [col_mapping[c] for c in col_types_lower.get('str', []) if c in df_columns_lower]
    numeric_cols = [col_mapping[c] for c in col_types_lower.get('numeric', []) if c in df_columns_lower]

    print(f"\n타입 변환 적용:")
    print(f"  - 날짜 컬럼 ({len(date_cols)}개)")
    print(f"  - 문자열 컬럼 ({len(str_cols)}개)")
    print(f"  - 숫자 컬럼 ({len(numeric_cols)}개)")

    # 타입 변환 적용
    print("\n타입 변환 진행:")

    # 날짜 타입 변환
    for c in date_cols:
        try:
            df = df.withColumn(c, to_date(col(c)))
        except Exception as e:
            print(f"  ✗ {c} 날짜 변환 실패: {e}")

    # 문자열 타입 변환
    for c in str_cols:
        try:
            df = df.withColumn(c, col(c).cast(StringType()))
        except Exception as e:
            print(f"  ✗ {c} 문자열 변환 실패: {e}")

    # 숫자 타입 변환
    for c in numeric_cols:
        try:
            df = df.withColumn(c, col(c).cast(DoubleType()))
        except Exception as e:
            print(f"  ✗ {c} 숫자 변환 실패: {e}")

    return df
