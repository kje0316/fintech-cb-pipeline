"""
데이터 품질 검증
"""
from sqlalchemy import text
from ..config import DM_SCHEMA


def validate_data_quality(engine):
    """
    제약조건 추가 전 데이터 품질 검증
    """
    print("\n" + "="*70)
    print("STEP 2: 데이터 품질 검증")
    print("="*70 + "\n")
    
    validation_passed = True
    
    with engine.begin() as conn:
        # 1. dim_company PK 중복 체크
        print("[1/5] dim_company PK 중복 체크...")
        result = conn.execute(text(f"""
            SELECT company_sk, COUNT(*) as cnt
            FROM {DM_SCHEMA}.dim_company
            GROUP BY company_sk
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        if duplicates:
            print(f"  ❌ PK 중복 발견: {len(duplicates)}건")
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
        
        # 2. dim_company NULL 체크
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.dim_company
            WHERE company_sk IS NULL OR company_id IS NULL
        """))
        null_count = result.scalar()
        if null_count > 0:
            print(f"  ❌ NULL 값 발견: {null_count}건")
            validation_passed = False
        else:
            print("  ✓ 필수 컬럼 NULL 없음")
        
        # 3. dim_time PK 중복 체크
        print("\n[2/5] dim_time PK 중복 체크...")
        result = conn.execute(text(f"""
            SELECT time_sk, COUNT(*) as cnt
            FROM {DM_SCHEMA}.dim_time
            GROUP BY time_sk
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        if duplicates:
            print(f"  ❌ PK 중복 발견: {len(duplicates)}건")
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
        
        # 4. fact_financial_statement PK 중복 체크
        print("\n[3/5] fact_financial_statement PK 중복 체크...")
        result = conn.execute(text(f"""
            SELECT company_sk, time_sk, COUNT(*) as cnt
            FROM {DM_SCHEMA}.fact_financial_statement
            GROUP BY company_sk, time_sk
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        if duplicates:
            print(f"  ❌ PK 중복 발견: {len(duplicates)}건")
            validation_passed = False
        else:
            print("  ✓ PK 중복 없음")
        
        # 5. fact_financial_statement FK 참조 무결성
        print("\n[4/5] fact_financial_statement FK 참조 무결성 체크...")
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.fact_financial_statement f
            LEFT JOIN {DM_SCHEMA}.dim_company c ON f.company_sk = c.company_sk
            WHERE c.company_sk IS NULL
        """))
        orphan_count = result.scalar()
        if orphan_count > 0:
            print(f"  ❌ 참조 무결성 위반 (company_sk): {orphan_count}건")
            validation_passed = False
        else:
            print("  ✓ company_sk 참조 무결성 정상")
        
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.fact_financial_statement f
            LEFT JOIN {DM_SCHEMA}.dim_time t ON f.time_sk = t.time_sk
            WHERE t.time_sk IS NULL
        """))
        orphan_count = result.scalar()
        if orphan_count > 0:
            print(f"  ❌ 참조 무결성 위반 (time_sk): {orphan_count}건")
            validation_passed = False
        else:
            print("  ✓ time_sk 참조 무결성 정상")
        
        # 6. fact_credit_behavior FK 참조 무결성
        print("\n[5/5] fact_credit_behavior FK 참조 무결성 체크...")
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.fact_credit_behavior f
            LEFT JOIN {DM_SCHEMA}.dim_company c ON f.company_sk = c.company_sk
            WHERE c.company_sk IS NULL
        """))
        orphan_count = result.scalar()
        if orphan_count > 0:
            print(f"  ❌ 참조 무결성 위반 (company_sk): {orphan_count}건")
            validation_passed = False
        else:
            print("  ✓ company_sk 참조 무결성 정상")
    
    print("\n" + "="*70)
    if validation_passed:
        print("✅ 데이터 품질 검증 통과 - 제약조건 추가 가능")
    else:
        print("⚠️ 데이터 품질 문제 발견 - 수정 후 제약조건 추가 권장")
    print("="*70)
    
    return validation_passed
