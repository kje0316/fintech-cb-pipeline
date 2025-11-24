from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, isnan, isnull, trim, to_date, 
    udf, expr, percentile_approx, count, avg, max as spark_max, abs as spark_abs
)
from pyspark.sql.types import IntegerType, StringType, DoubleType, DateType
from pyspark.sql.window import Window
import yaml
from shared.config_loader import config


def cleanse_data(df_raw, yaml_path):
    """
    원본 데이터를 정제와 타입 변환 (Spark 버전)
    
    클렌징 전략 (Root Cause 기반 - 원인 먼저, 결과 나중):
    1. 중복 제거
    2. 경과일수 컬럼 → 5개 위험도 카테고리 변환 (999999999 = 이벤트 없음)
    3. Leaf 컬럼(기본 항목) 음수 제거 (물리적 정확성)
    4. Leaf 컬럼 IQR 이상치 제거 (통계적 정확성, 설정 기반)
    5. 파생컬럼 재계산 (17개 재무비율, 정제된 Leaf로 계산, 설정 기반)
    6. 파생컬럼 이상치 검증 (Optional, 설정 기반)
    7. 주소지시군구 타입 변환
    8. 타입 변환 (date/str/numeric)
    """

    if df_raw is None:
        return None

    print("데이터 정제 및 변환 시작...")

    # 1. 중복 제거
    df_raw = df_raw.dropDuplicates()

    # 2. 경과일수 컬럼 → 5개 카테고리 변환
    print("  - 경과일수 컬럼을 5개 구간으로 범주화 중...")

    def categorize_days(days):
        """
        경과일수를 5개 위험도 카테고리로 변환
        0: 이벤트 없음 (999999999)
        1: 장기 경과 (2년 초과)
        2: 중기 경과 (1-2년)
        3: 단기 경과 (3개월-1년)
        4: 최근 발생 (3개월 이내)
        """
        if days is None:
            return None
        if days == 999999999 or days == 999999999.0:
            return 0
        elif days > 730:
            return 1
        elif days > 365:
            return 2
        elif days > 90:
            return 3
        else:
            return 4

    categorize_days_udf = udf(categorize_days, IntegerType())

    # 경과일수 컬럼 목록
    days_since_cols = {
        'D2B000002': '신용도판단정보공공정보최근발생일자로부터경과일수',
        'D2B000003': '신용도판단정보공공정보최근해제일자로부터경과일수',
    }

    for col_name, description in days_since_cols.items():
        if col_name in df_raw.columns:
            df_raw = df_raw.withColumn(col_name, categorize_days_udf(col(col_name)))
            print(f"    ✓ {description} ({col_name}) 변환 완료")

    # 3. Leaf 컬럼 음수 제거
    print("  - Leaf 컬럼 이상치 제거 중...")

    positive_leaf_cols = {
        'FN1_7': '현금',
        'FN1_8': '현금등가물',
        'FN1_9': '상품유가증권',
        'FN1_10': '현금성자산',
        'FN1_11': '매출채권',
        'FN1_4': '재고자산',
        'FN1_6': '재공품',
        'FN1_5': '유형자산',
        'FN1_11_3': '무형자산',
        'FN1_11_4': '투자자산',
        'FN1_15': '단기차입금',
        'FN1_16': '차입금',
        'FN1_17': '매입채무',
        'FN1_20': '자기자본(납입자본금)',
        'FN1_21': '자본잉여금',
        'FN1_22': '이익잉여금',
        'FN2_1': '매출액',
        'FN2_2': '매출원가',
        'FN2_3': '판매비와관리비',
        'FN2_4': '금융비용',
        'FN3_4_1': '이자비용',
    }

    negative_counts = {}
    for col_name, description in positive_leaf_cols.items():
        if col_name in df_raw.columns:
            # 음수를 NULL로 변경
            negative_count = df_raw.filter(col(col_name) < 0).count()
            if negative_count > 0:
                negative_counts[description] = negative_count
                df_raw = df_raw.withColumn(
                    col_name,
                    when(col(col_name) < 0, lit(None)).otherwise(col(col_name))
                )

    if negative_counts:
        total = sum(negative_counts.values())
        print(f"    ✓ {total}건의 음수 값을 NULL로 변환:")
        for name, count in sorted(negative_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      - {name}: {count}건")

    # 4. Leaf 컬럼 IQR 이상치 제거
    leaf_outlier_config = config.get('cleansing', {}).get('leaf_outlier_removal', {})

    if leaf_outlier_config.get('enabled', True):
        threshold = leaf_outlier_config.get('iqr_threshold', 1.5)
        print(f"  - Leaf 컬럼 이상치 제거 중 (IQR {threshold}배)...")

        target_leaf_cols = leaf_outlier_config.get('target_columns', [])
        leaf_names = {
            'FN1_13': '자산총계',
            'FN1_1': '유동자산',
            'FN1_2': '비유동자산',
            'FN1_3': '당좌자산',
            'FN1_4': '재고자산',
            'FN1_11': '매출채권',
            'FN1_19': '부채총계',
            'FN1_14': '유동부채',
            'FN1_18': '비유동부채',
            'FN1_16': '차입금',
            'FN1_15': '단기차입금',
            'FN1_17': '매입채무',
            'FN1_24': '자본총계',
            'FN1_22': '이익잉여금',
            'FN2_1': '매출액',
            'FN2_2': '매출원가',
            'FN2_3': '판매비와관리비',
            'FN2_5': '영업손익',
            'FN2_10': '당기순이익',
            'FN3_2': '영업활동현금흐름',
        }

        leaf_outlier_counts = {}
        for col_name in target_leaf_cols:
            if col_name in df_raw.columns:
                # IQR 계산
                quantiles = df_raw.filter(col(col_name).isNotNull()).approxQuantile(col_name, [0.25, 0.75], 0.01)
                
                if len(quantiles) == 2:
                    Q1, Q3 = quantiles
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR

                    # 이상치 개수 계산
                    outlier_count = df_raw.filter(
                        (col(col_name) < lower_bound) | (col(col_name) > upper_bound)
                    ).count()

                    if outlier_count > 0:
                        leaf_outlier_counts[leaf_names.get(col_name, col_name)] = outlier_count
                        
                        # 이상치를 NULL로 변환
                        df_raw = df_raw.withColumn(
                            col_name,
                            when(
                                (col(col_name) < lower_bound) | (col(col_name) > upper_bound),
                                lit(None)
                            ).otherwise(col(col_name))
                        )

        if leaf_outlier_counts:
            total = sum(leaf_outlier_counts.values())
            print(f"    ✓ {total:,}건의 Leaf 이상치를 NULL로 변환:")
            for name, count in sorted(leaf_outlier_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      - {name}: {count:,}건")
        else:
            print(f"    ✓ 이상치 없음")

    # 5. 파생컬럼 재계산 (재무비율)
    derived_config = config.get('cleansing', {}).get('derived_columns', {})

    if derived_config.get('enabled', True):
        print("  - 파생컬럼 재계산 중 (21개 재무비율, 고신뢰도만)...")

        # 재무비율 정의
        ratios_to_recalc = {
            # 재무상태표 비율
            'R006': ('FN1_19', 'FN1_24', True, '부채비율'),
            'R007': ('FN1_24', 'FN1_13', True, '자기자본비율'),
            'R008': ('FN1_1', 'FN1_14', True, '유동비율'),
            
            # 손익계산서 비율
            'R013': ('FN2_2', 'FN2_1', True, '매출원가율'),
            'R014': ('FN2_3', 'FN2_1', True, '판관비율'),
            'R015': ('FN2_5', 'FN2_1', True, '영업이익율'),
            'R016': ('FN2_10', 'FN2_1', True, '당기순이익율'),
            'R018': ('FN2_10', 'FN1_24', False, '자기자본이익률(ROE)'),
            'R023': ('FN2_10', 'FN1_13', True, '총자산순이익률(ROA)'),
            
            # 활동성 비율
            'R020': ('FN2_2', 'FN1_4', False, '재고자산회전율'),
            
            # 증가율
            'R001': ('FN1_13', 'FN1_13_1', True, '총자산증가율'),
            'R002': ('FN2_1', 'FN2_1_1', True, '매출액증가율'),
            'R019': ('FN2_1', 'FN1_11', False, '매출채권회전율'),
            
            # N 시리즈
            'N001': ('FN1_15', 'FN1_13', True, '단기차입금의존도'),
            'N008': ('FN3_2', 'FN2_1', True, 'OCF/매출액비율'),
            'N012': ('FN2_1', 'FN1_24', False, '총자본회전율'),
        }

        recalc_count = 0
        for ratio_code, (numerator, denominator, is_percent, desc) in ratios_to_recalc.items():
            if ratio_code not in df_raw.columns:
                continue

            # 특수 계산
            if ratio_code == 'R001':
                # 총자산증가율 = (자산총계 - 자산총계(전기)) / 자산총계 × 100
                df_raw = df_raw.withColumn(
                    ratio_code,
                    when(
                        col(numerator).isNotNull() & col(denominator).isNotNull() & (col(numerator) != 0),
                        ((col(numerator) - col(denominator)) / col(numerator)) * 100
                    ).otherwise(0)
                )
                recalc_count += 1

            elif ratio_code == 'R002':
                # 매출액증가율 = (매출액 - 전기매출액) / 전기매출액 × 100
                df_raw = df_raw.withColumn(
                    ratio_code,
                    when(
                        col(numerator).isNotNull() & col(denominator).isNotNull() & (col(denominator) != 0),
                        ((col(numerator) - col(denominator)) / col(denominator)) * 100
                    ).otherwise(0)
                )
                recalc_count += 1

            elif ratio_code == 'R019':
                # 매출채권회전율 = 매출액 / 평균매출채권
                prev_col = 'FN1_11_1'
                if prev_col in df_raw.columns:
                    df_raw = df_raw.withColumn(
                        ratio_code,
                        when(
                            col(numerator).isNotNull() & col(denominator).isNotNull() & col(prev_col).isNotNull(),
                            col(numerator) / ((col(denominator) + col(prev_col)) / 2)
                        ).otherwise(0)
                    )
                else:
                    df_raw = df_raw.withColumn(
                        ratio_code,
                        when(
                            col(numerator).isNotNull() & col(denominator).isNotNull() & (col(denominator) != 0),
                            col(numerator) / col(denominator)
                        ).otherwise(0)
                    )
                recalc_count += 1

            elif numerator in df_raw.columns and denominator in df_raw.columns:
                # 일반 비율 계산
                ratio_expr = when(
                    col(numerator).isNotNull() & col(denominator).isNotNull() & (col(denominator) != 0),
                    col(numerator) / col(denominator)
                ).otherwise(0)

                if is_percent:
                    ratio_expr = ratio_expr * 100

                df_raw = df_raw.withColumn(ratio_code, ratio_expr)
                recalc_count += 1

        # N 시리즈 complex 계산
        if 'N003' in df_raw.columns and 'FN1_1' in df_raw.columns and 'FN1_14' in df_raw.columns and 'FN2_1' in df_raw.columns:
            # N003 = 매출액 / (유동자산 - 유동부채)
            df_raw = df_raw.withColumn(
                'N003',
                when(
                    col('FN2_1').isNotNull() & col('FN1_1').isNotNull() & col('FN1_14').isNotNull() & 
                    ((col('FN1_1') - col('FN1_14')) != 0),
                    col('FN2_1') / (col('FN1_1') - col('FN1_14'))
                ).otherwise(0)
            )
            recalc_count += 1

        if 'N005' in df_raw.columns and 'FN2_1' in df_raw.columns and 'FN2_2' in df_raw.columns:
            # N005 = ((매출액 - 매출원가) / 매출액) × 100
            df_raw = df_raw.withColumn(
                'N005',
                when(
                    col('FN2_1').isNotNull() & col('FN2_2').isNotNull() & (col('FN2_1') != 0),
                    ((col('FN2_1') - col('FN2_2')) / col('FN2_1')) * 100
                ).otherwise(0)
            )
            recalc_count += 1

        print(f"    ✓ {recalc_count}개 재무비율 재계산 완료")

    # 6. 파생컬럼 이상치 제거 (Optional)
    outlier_config = config.get('cleansing', {}).get('outlier_removal', {})

    if outlier_config.get('enabled', True):
        threshold = outlier_config.get('iqr_threshold', 1.5)
        print(f"  - 파생컬럼 이상치 검증 중 (IQR {threshold}배)...")

        target_cols = outlier_config.get('target_columns', [])
        ratio_names = {
            'R006': '부채비율',
            'R007': '자기자본비율',
            'R008': '유동비율',
            'R012': '차입금의존도',
            'R013': '매출원가율',
            'R014': '판관비율',
            'R019': '매출채권회전율',
            'R020': '재고자산회전율',
            'R021': '매입채무회전율',
            'R022': '총자산회전율',
        }

        outlier_counts = {}
        for col_name in target_cols:
            if col_name in df_raw.columns:
                quantiles = df_raw.filter(col(col_name).isNotNull()).approxQuantile(col_name, [0.25, 0.75], 0.01)
                
                if len(quantiles) == 2:
                    Q1, Q3 = quantiles
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR

                    outlier_count = df_raw.filter(
                        (col(col_name) < lower_bound) | (col(col_name) > upper_bound)
                    ).count()

                    if outlier_count > 0:
                        outlier_counts[ratio_names.get(col_name, col_name)] = outlier_count
                        
                        df_raw = df_raw.withColumn(
                            col_name,
                            when(
                                (col(col_name) < lower_bound) | (col(col_name) > upper_bound),
                                lit(None)
                            ).otherwise(col(col_name))
                        )

        if outlier_counts:
            total = sum(outlier_counts.values())
            print(f"    ✓ {total:,}건의 이상치를 NULL로 변환:")
            for name, count in sorted(outlier_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      - {name}: {count:,}건")
        else:
            print(f"    ✓ 이상치 없음")

    # 7. 주소지시군구 타입 변환
    if 'CT_CNTY_GU_CD' in df_raw.columns:
        df_raw = df_raw.withColumn(
            'CT_CNTY_GU_CD',
            col('CT_CNTY_GU_CD').cast(IntegerType()).cast(StringType())
        )

    # 8. 타입 변환
    with open(yaml_path, 'r', encoding="utf-8") as f:
        column_types = yaml.safe_load(f)

    # 날짜 타입 변환
    for col_name in column_types.get('date', []):
        if col_name in df_raw.columns:
            df_raw = df_raw.withColumn(
                col_name,
                to_date(col(col_name).cast(StringType()), "yyyyMMdd")
            )

    # 문자열 타입 변환
    for col_name in column_types.get('str', []):
        if col_name in df_raw.columns:
            df_raw = df_raw.withColumn(
                col_name,
                trim(col(col_name).cast(StringType()))
            )

    # 숫자 타입 변환
    for col_name in column_types.get('numeric', []):
        if col_name in df_raw.columns:
            df_raw = df_raw.withColumn(
                col_name,
                col(col_name).cast(DoubleType())
            )

    print('데이터 타입 변환 완료.')

    return df_raw
