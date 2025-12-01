"""
DWH → DM 파이프라인 실행 (Spark 버전)
lake_to_dwh2와 동일한 구조
"""
from datetime import datetime
from pathlib import Path

# spark_etl 경로 설정
from spark_etl.main_dm.config import (
    TABLES_TO_COPY,
    ENABLE_CONSTRAINTS,
    ENABLE_VALIDATION,
    CREATE_INDEXES,
    EXECUTION_MODE,
    DM_SCHEMA
)

from spark_etl.main_dm.spark_utils import get_spark_session, load_to_postgres
from spark_etl.main_dm.scripts import (
    copy_dwh_tables_to_dm,
    validate_data_quality,
    add_constraints_to_dm,
    add_derived_data_constraints,
    create_derived_data,
    create_indexes
)


def main():
    """
    메인 파이프라인 실행
    """
    start_time = datetime.now()
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*12 + "DWH → DM 구축 시작 (Spark 버전)" + " "*17 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"실행 모드: {EXECUTION_MODE}")
    
    # ===== dm 스키마 생성 =====
    print("\n스키마 준비 중...")
    try:
        import psycopg2
        from urllib.parse import urlparse
        from shared.config_loader import DB_URL
        
        result = urlparse(DB_URL)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        
        cursor = conn.cursor()
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {DM_SCHEMA};")
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ 스키마 '{DM_SCHEMA}' 준비 완료\n")
        
    except Exception as e:
        print(f"✗ 스키마 생성 오류: {e}")
        raise
    
    try:
        # SparkSession 초기화
        spark = get_spark_session()
        print(f"\n✓ SparkSession 초기화 완료")
        print(f"  - App Name: {spark.sparkContext.appName}")
        print(f"  - Spark Version: {spark.version}")
        
        # ===== STEP 1: DWH 테이블 추출 =====
        dataframes = copy_dwh_tables_to_dm(TABLES_TO_COPY)
        
        step1_time = datetime.now()
        print(f"\n⏱️ STEP 1 소요 시간: {(step1_time - start_time).seconds}초")
        
        # ===== STEP 2: 데이터 품질 검증 =====
        if ENABLE_VALIDATION:
            validation_passed = validate_data_quality(dataframes)
            
            step2_time = datetime.now()
            print(f"\n⏱️ STEP 2 소요 시간: {(step2_time - step1_time).seconds}초")
            
            if not validation_passed:
                print("\n⚠️ 경고: 데이터 품질 문제가 발견되었습니다.")
                print("계속 진행하시겠습니까?")
                user_input = input("계속하려면 'y' 입력: ")
                if user_input.lower() != 'y':
                    print("작업 중단됨")
                    spark.stop()
                    return
        else:
            print("\n⏭️ STEP 2 스킵 (검증 비활성화)")
            step2_time = datetime.now()
        
        # ===== STEP 3: 제약조건 검증 =====
        if ENABLE_CONSTRAINTS:
            add_constraints_to_dm(spark, dataframes)
            
            step3_time = datetime.now()
            print(f"\n⏱️ STEP 3 소요 시간: {(step3_time - step2_time).seconds}초")
        else:
            print("\n⏭️ STEP 3 스킵 (제약조건 검증 비활성화)")
            step3_time = step2_time
        
        # ===== STEP 4: 파생 데이터 생성 =====
        derived_df = create_derived_data(spark, dataframes['fact_financial_statement'])
        
        if ENABLE_CONSTRAINTS:
            add_derived_data_constraints(spark, derived_df)
        
        dataframes['derived_data'] = derived_df
        
        step4_time = datetime.now()
        print(f"\n⏱️ STEP 4 소요 시간: {(step4_time - step3_time).seconds}초")
        
        # ===== STEP 5: 데이터 저장 =====
        print("\n" + "="*70)
        print("STEP 5: PostgreSQL 저장")
        print("="*70 + "\n")
        
        for table_name, df in dataframes.items():
            load_to_postgres(df, f"{DM_SCHEMA}.{table_name}", mode='overwrite')
        
        step5_time = datetime.now()
        print(f"\n⏱️ STEP 5 소요 시간: {(step5_time - step4_time).seconds}초")
        
        # ===== STEP 6: 인덱스/파티셔닝 정보 =====
        if CREATE_INDEXES:
            create_indexes(spark, dataframes)
        
        # ===== STEP 7: PostgreSQL 제약조건 추가 =====
        if ENABLE_CONSTRAINTS:
            print("\n" + "="*70)
            print("STEP 7: PostgreSQL 제약조건 추가")
            print("="*70 + "\n")
            
            try:
                # postgres_constraints.py 실행
                from spark_etl.main_dm.scripts.dm_constraints import add_constraints
                add_constraints()
                
                step7_time = datetime.now()
                print(f"\n⏱️ STEP 7 소요 시간: {(step7_time - step5_time).seconds}초")
                
            except ImportError as e:
                print(f"  ⚠️ postgres_constraints.py를 찾을 수 없습니다: {e}")
                print("  수동으로 실행하세요: python -m spark_etl.main_dm.scripts.postgres_constraints")
            except Exception as e:
                print(f"  ⚠️ 제약조건 추가 실패: {e}")
                print("  (데이터 무결성을 확인하세요)")
        
        # ===== 완료 =====
        end_time = datetime.now()
        total_seconds = (end_time - start_time).seconds
        
        print("\n" + "╔" + "="*68 + "╗")
        print("║" + " "*20 + "✓ DM 구축 완료!" + " "*25 + "║")
        print("╚" + "="*68 + "╝")
        
        print(f"\n완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"총 소요 시간: {total_seconds // 60}분 {total_seconds % 60}초")
        
        # 요약 정보
        print("\n" + "="*70)
        print("구축 요약")
        print("="*70)
        
        print("\n생성된 테이블:")
        for table_name, df in dataframes.items():
            row_count = df.count()
            col_count = len(df.columns)
            print(f"  - {DM_SCHEMA}.{table_name}: {row_count:,}행 x {col_count}컬럼")
        
        print(f"\nPostgreSQL 저장 완료: {DM_SCHEMA} 스키마")
        
        if ENABLE_CONSTRAINTS:
            print("제약조건 추가 완료: PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL")
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # SparkSession 종료
        spark = get_spark_session()
        spark.stop()
        print("\n✓ SparkSession 종료 완료")


if __name__ == "__main__":
    main()