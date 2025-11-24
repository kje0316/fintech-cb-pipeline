"""
Spark 세션 및 PostgreSQL 유틸리티 함수
lake_to_dwh2와 동일한 구조
"""
from pyspark.sql import SparkSession
from pathlib import Path
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL


def get_spark_session():
    """
    SparkSession을 생성하고 반환합니다.
    메모리 최적화 버전
    """
    # 프로젝트 루트에서 JDBC jar 경로 찾기
    project_root = Path(__file__).resolve().parents[2]
    jdbc_jar = project_root / "postgresql-42.7.1.jar"
    
    # JDBC jar를 SPARK_CLASSPATH에 추가
    os.environ['SPARK_CLASSPATH'] = str(jdbc_jar)
    
    spark = SparkSession.builder \
        .appName("ETL_DWH_to_DM") \
        .config("spark.driver.extraClassPath", str(jdbc_jar)) \
        .config("spark.executor.extraClassPath", str(jdbc_jar)) \
        .config("spark.executor.memory", "20g") \
        .config("spark.driver.memory", "20g") \
        .config("spark.memory.fraction", "0.8") \
        .config("spark.memory.storageFraction", "0.3") \
        .config("spark.sql.shuffle.partitions", "200") \
        .getOrCreate()
    
    return spark


def get_jdbc_properties():
    """
    DB_URL을 파싱하여 JDBC 연결 정보를 반환합니다.
    DB_URL 형식: postgresql://user:password@host:port/database
    """
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


def execute_sql(sql_file_path):
    """
    SQL 파일을 PostgreSQL에서 실행합니다.
    Spark는 DDL 실행이 제한적이므로 psycopg2 사용
    """
    import psycopg2
    from urllib.parse import urlparse
    
    print(f"SQL 파일 '{sql_file_path}' 실행 중...")
    
    try:
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
        
        print("SQL 실행 완료.")
        
    except Exception as e:
        print(f"SQL 실행 중 오류 발생: {e}")
        raise



def load_to_postgres(df, table_name, mode='append'):
    """
    Spark DataFrame을 PostgreSQL에 적재합니다.
    
    Parameters:
    -----------
    df : DataFrame
        적재할 Spark DataFrame
    table_name : str
        'schema.table' 또는 'table' 형식
    mode : str
        'append' 또는 'overwrite'
    """
    if df.count() == 0:
        print(f"적재할 데이터가 없습니다: {table_name}")
        return
    
    jdbc_url, properties = get_jdbc_properties()
    
    print(f"PostgreSQL에 테이블 '{table_name}' 데이터 적재 시작...")
    
    # schema.table 분리
    if '.' in table_name:
        schema, table = table_name.split('.', 1)
    else:
        schema = 'public'
        table = table_name
    
    try:
        # mode가 'overwrite'인 경우 테이블 존재 확인 후 처리
        if mode == 'overwrite':
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
            
            # 테이블 존재 여부 확인
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = '{schema}' 
                    AND table_name = '{table}'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                # 테이블이 있으면 TRUNCATE
                cursor.execute(f"TRUNCATE TABLE {schema}.{table} RESTART IDENTITY CASCADE;")
                conn.commit()
                print(f"  ✓ TRUNCATE {schema}.{table} 완료")
            else:
                # 테이블이 없으면 새로 생성될 것임
                print(f"  ℹ️ 테이블 {schema}.{table} 없음 - 새로 생성됩니다")
            
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
        print(f"  ✓ 테이블 '{schema}.{table}' 데이터 적재 완료. {row_count:,} rows.")
        
    except Exception as e:
        print(f"테이블 '{table_name}' 데이터 적재 중 오류 발생: {e}")
        raise
