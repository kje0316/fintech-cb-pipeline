from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import pandas as pd
import yaml



def get_db_engine():
    """
    .env 파일에서 접속 정보를 로드하여 SQLAlchemy 엔진을 생성하고 반환합니다.
    """
    load_dotenv()
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        raise ValueError("데이터베이스 접속 정보가 .env 파일에 없습니다.")
        
    db_url = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    return create_engine(db_url)




def create_schema(sql_file_path):
    """
    SQL 파일에 정의된 스키마를 PostgreSQL 데이터베이스에 생성합니다.
    """
    engine = get_db_engine()
    print(f"스키마 파일 '{sql_file_path}' 실행 중...")
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        with engine.connect() as connection:
            for command in sql_commands.split(';'):
                stripped_command = command.strip()
                if stripped_command:
                    connection.execute(text(stripped_command))
            connection.commit()
        print("스키마 생성 완료.")
    except Exception as e:
        print(f"스키마 생성 중 오류 발생: {e}")
        raise



def load_data(df, table_name):
    """
    변환된 데이터프레임을 PostgreSQL에 적재합니다.
    """
    if df.empty:
        print(f"적재할 데이터가 없습니다: {table_name}")
        return

    engine = get_db_engine()
    print(f"PostgreSQL에 테이블 '{table_name}' 데이터 적재 시작...")
    try:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))
            df.to_sql(table_name, connection, if_exists='append', index=False)
        print(f"테이블 '{table_name}' 데이터 적재 완료. {len(df)} rows.")
    except Exception as e:
        print(f"테이블 '{table_name}' 데이터 적재 중 오류 발생: {e}")





def load_table_from_db(table_name, yaml_path): 
    """
    데이터베이스에서 테이블을 로드하여 데이터프레임으로 반환합니다.
    col_types.yaml으로 타입 참고하여 로드함. 
    """
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
        # print(f"  - date 타입: {len(col_types_lower.get('date', []))}개")
        # print(f"  - str 타입: {len(col_types_lower.get('str', []))}개")
        # print(f"  - numeric 타입: {len(col_types_lower.get('numeric', []))}개")

    except FileNotFoundError:
        print(f"경고: YAML 파일을 찾을 수 없습니다: {yaml_path}")
        col_types_lower = {'date': [], 'str': [], 'numeric': []}
    except Exception as e:
        print(f"경고: YAML 파일 로드 중 오류: {e}")
        col_types_lower = {'date': [], 'str': [], 'numeric': []}


    # ============================================================
    # 3. PostgreSQL에서 데이터 로드

    print(f"\nPostgreSQL에서 '{table_name}' 테이블 로드 중...")

    try:
        engine = get_db_engine()
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        
        print(f"✓ 테이블 로드 완료 ({len(df):,}행, {len(df.columns)}개 컬럼)")
        
    except Exception as e:
        print(f"[오류] 테이블 로드 실패: {e}")
        raise

    # ============================================================
    # 4. 실제 테이블에 존재하는 컬럼만 필터링

    df_columns_lower = [col.lower() for col in df.columns]
    col_mapping = {col.lower(): col for col in df.columns}

    date_cols = [col_mapping[col] for col in col_types_lower.get('date', []) if col in df_columns_lower]
    str_cols = [col_mapping[col] for col in col_types_lower.get('str', []) if col in df_columns_lower]
    numeric_cols = [col_mapping[col] for col in col_types_lower.get('numeric', []) if col in df_columns_lower]

    print(f"\n타입 변환 적용:")
    print(f"  - 날짜 컬럼 ({len(date_cols)}개)")
    print(f"  - 문자열 컬럼 ({len(str_cols)}개)")
    print(f"  - 숫자 컬럼 ({len(numeric_cols)}개)")

    # ============================================================
    # 5. 타입 변환 적용

    print("\n타입 변환 진행:")

    # 날짜 타입 변환
    for col in date_cols:
        try:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            # print(f"  ✓ {col} → datetime64[ns]")
        except Exception as e:
            print(f"  ✗ {col} 날짜 변환 실패: {e}")

    # 문자열 타입 변환
    for col in str_cols:
        try:
            df[col] = df[col].astype('string')
            # print(f"  ✓ {col} → string")
        except Exception as e:
            print(f"  ✗ {col} 문자열 변환 실패: {e}")

    # 숫자 타입 변환
    for col in numeric_cols:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # print(f"  ✓ {col} → float64")
        except Exception as e:
            print(f"  ✗ {col} 숫자 변환 실패: {e}")

    return df