
import pandas as pd
from sqlalchemy import create_engine, text, types # (⭐️ 수정) types import
import time
import os

# --- 1. columns_map도 import 합니다. ---
from shared.config_loader import config, DB_URL, DB_URL_ADMIN, columns_map

paths = config['paths']
db_config = config['db']
DB_NAME_TO_CREATE = db_config['db_name']
RAW_DATA_CSV_PATH = paths['raw_data']
INDUSTRY_CSV_PATH = paths['industry_codes']
# ---------------------------------------------

def setup_database():
    """1. DB와 3개의 스키마(Lake, DWH, Marts)를 생성합니다."""
    
    engine_admin = create_engine(DB_URL_ADMIN)
    
    print(f"'{DB_NAME_TO_CREATE}' 데이터베이스 생성 시도...")
    try:
        with engine_admin.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME_TO_CREATE}'"))
            if not result.fetchone():
                conn.execute(text(f"CREATE DATABASE {DB_NAME_TO_CREATE}"))
                print(f"DATABASE '{DB_NAME_TO_CREATE}' 생성 완료.")
            else:
                print(f"DATABASE '{DB_NAME_TO_CREATE}' (은)는 이미 존재합니다.")
    except Exception as e:
        print(f"❌ DB 접속 실패: {e}")
        return None

    engine_main = create_engine(DB_URL)

    print("3개 스키마(lake, dwh, marts) 생성 시도...")
    try:
        with engine_main.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT") 
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS lake;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS dwh;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts;"))
        print("스키마 3개 준비 완료.")
        return engine_main 
    
    except Exception as e:
        print(f"❌ 스키마 생성 실패: {e}")
        return None


def load_p1_lake(engine, raw_csv_path):
    """(P1 임무) 60만 건 원본 CSV를 'lake.raw_data'에 적재합니다."""
    print(f"\n[P1] 'lake.raw_data' 테이블 적재 시작 (소스: {raw_csv_path})...")
    start_time = time.time()
    
    # (⭐️ 수정) YAML에서 불러온 영어 컬럼명을 리스트로 만듭니다.
    column_names = list(columns_map.keys())
    
    try:
        chunk_iter = pd.read_csv(
            raw_csv_path, 
            chunksize=50000, 
            low_memory=False, 
            encoding="cp949",
            names=column_names,  # (⭐️ 수정) 영어 컬럼명 강제
            header=0           # (⭐️ 수정) 원본 CSV의 한글 헤더(0번째 줄)를 무시
        )
        
        for i, chunk in enumerate(chunk_iter):
            chunk.to_sql(
                name="raw_data",
                con=engine,
                schema="lake",
                if_exists="append" if i > 0 else "replace",
                index=False
            )
            print(f"  ... {(i+1)*50000}행 적재 완료 ...")
            
        end_time = time.time()
        print(f"[P1] 'lake.raw_data' 적재 완료! (총 {end_time - start_time:.2f}초)")

    except Exception as e:
        print(f"❌ [P1] 'lake.raw_data' 적재 실패: {e}")
        import traceback
        traceback.print_exc()

def load_p1_dwh(engine, industry_csv_path):
    """(P1 임무) 'dwh.dim_industry' 테이블을 적재합니다."""
    print(f"\n[P1] 'dwh.dim_industry' 테이블 적재 시작 (소스: {industry_csv_path})...")
    try:
        df_industry = pd.read_csv(industry_csv_path)
        
        # (⭐️ 수정) Pandas 타입이 아닌 SQLAlchemy 타입을 명시합니다.
        sql_types = {
            'industry_code': types.String(10), 
            'industry_name': types.String(255)
        }
        
        df_industry.to_sql(
            name="dim_industry",
            con=engine,
            schema="dwh",
            if_exists="replace",
            index=False,
            dtype=sql_types  # (⭐️ 수정) SQLAlchemy 타입 사용
        )
        print("[P1] 'dwh.dim_industry' 적재 완료!")
    except Exception as e:
        print(f"❌ [P1] 'dwh.dim_industry' 적재 실패: {e}")

def build_p2_mart_v0(engine):
    """(P2 임무) 'marts.dm_industry_benchmark_v0'를 18개 재무지표로 구축합니다."""
    print("\n[P2] 'marts.dm_industry_benchmark_v0' (18개 지표 전체 버전) 생성 시작...")

    # 18개 재무지표 매핑 (영문 컬럼코드 → metric_code)
    METRICS = {
        'R001': 'total_asset_growth',      # 총자산증가율
        'R002': 'revenue_growth',           # 매출액증가율
        'R006': 'debt_ratio',               # 부채비율
        'R007': 'equity_ratio',             # 자기자본비율
        'R008': 'current_ratio',            # 유동비율
        'R012': 'borrowing_dependency',     # 차입금의존도
        'R013': 'cogs_ratio',               # 매출원가율
        'R014': 'sga_ratio',                # 판관비율
        'R015': 'operating_margin',         # 영업이익률
        'R016': 'net_margin',               # 당기순이익률
        'R018': 'roe',                      # 자기자본이익률(ROE)
        'R019': 'receivable_turnover',      # 매출채권회전율
        'R020': 'inventory_turnover',       # 재고자산회전율
        'R021': 'payable_turnover',         # 매입채무회전율
        'R022': 'total_asset_turnover',     # 총자산회전율
        'R023': 'roa',                      # 총자산순이익률(ROA)
        'R024': 'current_asset_growth',     # 유동자산증가율
        'R025': 'tangible_asset_growth',    # 유형자산증가율
    }

    try:
        # 1. lake.raw_data에서 데이터 읽기
        print("  📂 lake.raw_data에서 데이터 로드 중...")
        query = "SELECT \"SIC_CD_3\", " + ", ".join([f'"{col}"' for col in METRICS.keys()]) + " FROM lake.raw_data"
        df = pd.read_sql(query, engine)
        print(f"  ✅ 로드 완료: {len(df):,}행")

        # 2. 포함 업종 목록 (included_industries.csv)
        industry_csv = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'docs', 'included_industries.csv'
        )
        if os.path.exists(industry_csv):
            included_industries = pd.read_csv(industry_csv)
            industry_codes = included_industries['industry_code'].tolist()
            print(f"  📋 포함 업종: {len(industry_codes)}개")
        else:
            # 파일이 없으면 데이터에서 자동 추출
            industry_codes = df['SIC_CD_3'].unique().tolist()
            print(f"  📋 전체 업종 사용: {len(industry_codes)}개")

        # 3. 업종별 × 지표별 통계 집계
        print(f"  📈 집계 시작: {len(industry_codes)} 업종 × {len(METRICS)} 지표 = {len(industry_codes) * len(METRICS)} 조합")
        results = []

        for industry_code in industry_codes:
            # 해당 업종 필터링
            industry_df = df[df['SIC_CD_3'] == industry_code]

            for col_code, metric_code in METRICS.items():
                # NULL 제외하고 데이터 추출
                data = pd.to_numeric(industry_df[col_code], errors='coerce').dropna()

                # 표본 수가 10개 미만이면 제외
                if len(data) < 10:
                    continue

                # 통계 계산
                results.append({
                    'industry_code': industry_code,
                    'metric_code': metric_code,
                    'count': int(len(data)),
                    'avg_value': float(data.mean()),
                    'median_value': float(data.median()),
                    'std_value': float(data.std()),
                    'min_value': float(data.min()),
                    'max_value': float(data.max()),
                    'p10': float(data.quantile(0.10)),
                    'p25': float(data.quantile(0.25)),
                    'p50': float(data.quantile(0.50)),
                    'p75': float(data.quantile(0.75)),
                    'p90': float(data.quantile(0.90)),
                })

        print(f"  ✅ 집계 완료: {len(results):,}행 생성")

        # 4. DataFrame 생성 및 PostgreSQL에 저장
        mart_df = pd.DataFrame(results)

        # 테이블 삭제 후 재생성
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text("DROP TABLE IF EXISTS marts.dm_industry_benchmark_v0;"))

        # 타입 명시하여 저장
        mart_df.to_sql(
            name='dm_industry_benchmark_v0',
            con=engine,
            schema='marts',
            if_exists='replace',
            index=False,
            dtype={
                'industry_code': types.String(10),
                'metric_code': types.String(50),
                'count': types.Integer,
                'avg_value': types.Numeric(20, 4),
                'median_value': types.Numeric(20, 4),
                'std_value': types.Numeric(20, 4),
                'min_value': types.Numeric(20, 4),
                'max_value': types.Numeric(20, 4),
                'p10': types.Numeric(20, 4),
                'p25': types.Numeric(20, 4),
                'p50': types.Numeric(20, 4),
                'p75': types.Numeric(20, 4),
                'p90': types.Numeric(20, 4),
            }
        )

        print("[P2] 'marts.dm_industry_benchmark_v0' 생성 완료!")
        print(f"     총 {len(mart_df):,}행 적재됨")

    except Exception as e:
        print(f"[P2] ❌ 마트 생성 실패: {e}")
        import traceback
        traceback.print_exc()

# ... (main 함수는 수정할 필요 없음) ...
def main():
    # 0. 파일 경로 검증
    if not os.path.exists(RAW_DATA_CSV_PATH):
        print(f"❌ 에러: 원본 데이터 파일({RAW_DATA_CSV_PATH})을 찾을 수 없습니다.")
        return
    if not os.path.exists(INDUSTRY_CSV_PATH):
        print(f"❌ 에러: 업종 코드 파일({INDUSTRY_CSV_PATH})을 찾을 수 없습니다.")
        return

    # 1. DB 및 스키마 생성
    engine_main = setup_database()
    
    if engine_main is None:
        print("DB 셋업 실패. 스크립트를 종료합니다.")
        return
        
    # 2. P1 - Lake 적재
    load_p1_lake(engine_main, RAW_DATA_CSV_PATH)
    
    # 3. P1 - DWH (업종) 적재
    load_p1_dwh(engine_main, INDUSTRY_CSV_PATH)
    
    # 4. P2 - Mart (간단 버전) 생성
    build_p2_mart_v0(engine_main)

    print("\n✅ 모든 뼈대 구축 작업이 완료되었습니다.")
    print(f"DB: {DB_NAME_TO_CREATE}, Schemas: lake, dwh, marts")

if __name__ == "__main__":
    main()