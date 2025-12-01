"""
DWH 테이블 추출 (Spark 버전)
lake_to_dwh2와 동일한 구조
"""
from pyspark.sql import DataFrame
from typing import Dict
from ..config import DWH_SCHEMA, JDBC_PARTITION_CONFIGS
from ..spark_utils import get_spark_session, get_jdbc_properties


def copy_dwh_tables_to_dm(table_list: list) -> Dict[str, DataFrame]:
    """
    DWH의 모든 테이블을 Spark DataFrame으로 추출
    
    Parameters:
    -----------
    table_list : list
        추출할 테이블 목록
    
    Returns:
    --------
    dict
        {table_name: DataFrame} 형태의 딕셔너리
    """
    print("\n" + "="*70)
    print("STEP 1: DWH 테이블 → Spark DataFrame 추출")
    print("="*70 + "\n")
    
    spark = get_spark_session()
    jdbc_url, properties = get_jdbc_properties()
    
    dataframes = {}
    
    for table_name in table_list:
        print(f"[추출 중] {DWH_SCHEMA}.{table_name}...")
        
        full_table = f"{DWH_SCHEMA}.{table_name}"
        
        # 파티션 설정 확인
        partition_config = JDBC_PARTITION_CONFIGS.get(table_name)
        
        # 기본 읽기 (소규모 테이블)
        if partition_config is None:
            df = spark.read \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", full_table) \
                .option("user", properties["user"]) \
                .option("password", properties["password"]) \
                .option("driver", properties["driver"]) \
                .load()
        
        # 파티션 읽기 (대규모 테이블)
        else:
            df = spark.read \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", full_table) \
                .option("user", properties["user"]) \
                .option("password", properties["password"]) \
                .option("driver", properties["driver"]) \
                .option("partitionColumn", partition_config['partitionColumn']) \
                .option("lowerBound", partition_config['lowerBound']) \
                .option("upperBound", partition_config['upperBound']) \
                .option("numPartitions", partition_config['numPartitions']) \
                .load()
            
            print(f"  (병렬 읽기: {partition_config['numPartitions']}개 파티션)")
        
        # 캐싱 (재사용 시 성능 향상)
        # df.cache()
        
        # 통계 출력
        row_count = df.count()
        col_count = len(df.columns)
        
        print(f"  ✓ {table_name} 추출 완료: {row_count:,}행 x {col_count}컬럼")
        
        dataframes[table_name] = df
    
    print("\n" + "="*70)
    print(f"✅ 총 {len(dataframes)}개 테이블 추출 완료")
    print("="*70)
    
    # 전체 통계
    total_rows = sum(df.count() for df in dataframes.values())
    print(f"\n전체 데이터: {total_rows:,}행")
    
    return dataframes
