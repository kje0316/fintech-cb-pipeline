"""
데이터 품질 검증 (Spark 버전)
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict


def validate_data_quality(dataframes: Dict[str, DataFrame]) -> bool:
    """
    제약조건 추가 전 데이터 품질 검증
    
    Parameters:
    -----------
    dataframes : dict
        {table_name: DataFrame} 딕셔너리
    
    Returns:
    --------
    bool
        모든 검증 통과 시 True
    """
    print("\n" + "="*70)
    print("STEP 2: 데이터 품질 검증 (Spark)")
    print("="*70 + "\n")
    
    validation_passed = True
    
    # ============================================
    # 1. dim_company PK 중복 체크
    # ============================================
    print("[1/5] dim_company PK 중복 체크...")
    
    if 'dim_company' in dataframes:
        df = dataframes['dim_company']
        
        # PK 중복 체크
        duplicates = df.groupBy('company_sk').count().filter(F.col('count') > 1)
        dup_count = duplicates.count()
        
        if dup_count > 0:
            print(f"  ❌ PK 중복 발견: {dup_count}건")
            duplicates.show(5)
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
        
        # NULL 체크
        null_count = df.filter(
            F.col('company_sk').isNull() | F.col('company_id').isNull()
        ).count()
        
        if null_count > 0:
            print(f"  ❌ NULL 값 발견: {null_count}건")
            validation_passed = False
        else:
            print("  ✓ 필수 컬럼 NULL 없음")
    
    # ============================================
    # 2. dim_time PK 중복 체크
    # ============================================
    print("\n[2/5] dim_time PK 중복 체크...")
    
    if 'dim_time' in dataframes:
        df = dataframes['dim_time']
        
        duplicates = df.groupBy('time_sk').count().filter(F.col('count') > 1)
        dup_count = duplicates.count()
        
        if dup_count > 0:
            print(f"  ❌ PK 중복 발견: {dup_count}건")
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
    
    # ============================================
    # 3. fact_financial_statement PK 중복 체크
    # ============================================
    print("\n[3/5] fact_financial_statement PK 중복 체크...")
    
    if 'fact_financial_statement' in dataframes:
        df = dataframes['fact_financial_statement']
        
        duplicates = df.groupBy('company_sk', 'time_sk').count().filter(F.col('count') > 1)
        dup_count = duplicates.count()
        
        if dup_count > 0:
            print(f"  ❌ PK 중복 발견: {dup_count}건")
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
    
    # ============================================
    # 4. fact_financial_statement FK 참조 무결성
    # ============================================
    print("\n[4/5] fact_financial_statement FK 참조 무결성 체크...")
    
    if 'fact_financial_statement' in dataframes and 'dim_company' in dataframes:
        fact_df = dataframes['fact_financial_statement']
        dim_company = dataframes['dim_company']
        
        # company_sk 참조 무결성 (LEFT ANTI JOIN)
        orphans = fact_df.join(
            dim_company.select('company_sk'),
            'company_sk',
            'left_anti'
        )
        orphan_count = orphans.count()
        
        if orphan_count > 0:
            print(f"  ❌ 참조 무결성 위반 (company_sk): {orphan_count}건")
            validation_passed = False
        else:
            print("  ✓ company_sk 참조 무결성 정상")
        
        # time_sk 참조 무결성
        if 'dim_time' in dataframes:
            dim_time = dataframes['dim_time']
            
            orphans = fact_df.join(
                dim_time.select('time_sk'),
                'time_sk',
                'left_anti'
            )
            orphan_count = orphans.count()
            
            if orphan_count > 0:
                print(f"  ❌ 참조 무결성 위반 (time_sk): {orphan_count}건")
                validation_passed = False
            else:
                print("  ✓ time_sk 참조 무결성 정상")
    
    # ============================================
    # 5. fact_credit_behavior FK 참조 무결성
    # ============================================
    print("\n[5/5] fact_credit_behavior FK 참조 무결성 체크...")
    
    if 'fact_credit_behavior' in dataframes and 'dim_company' in dataframes:
        fact_df = dataframes['fact_credit_behavior']
        dim_company = dataframes['dim_company']
        
        orphans = fact_df.join(
            dim_company.select('company_sk'),
            'company_sk',
            'left_anti'
        )
        orphan_count = orphans.count()
        
        if orphan_count > 0:
            print(f"  ❌ 참조 무결성 위반 (company_sk): {orphan_count}건")
            validation_passed = False
        else:
            print("  ✓ company_sk 참조 무결성 정상")
    
    print("\n" + "="*70)
    if validation_passed:
        print("✅ 데이터 품질 검증 통과 - 다음 단계 진행 가능")
    else:
        print("⚠️ 데이터 품질 문제 발견 - 수정 후 재검증 권장")
    print("="*70)
    
    return validation_passed
