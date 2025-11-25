"""
DWH → DM 파이프라인 실행
"""
from sqlalchemy import create_engine
from shared.config_loader import DB_URL
from etl.main_dm.config import (
    ENABLE_CONSTRAINTS, 
    ENABLE_VALIDATION,
    CREATE_INDEXES
)
from etl.main_dm.scripts import (
    copy_dwh_tables_to_dm,
    validate_data_quality,
    add_constraints_to_dm,
    add_derived_data_constraints,
    create_derived_data,
    create_indexes
)


def main():
    """메인 파이프라인 실행"""
    
    # DB 엔진 생성
    engine = create_engine(DB_URL, echo=False, future=True)
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "DWH → DM 구축 시작 (제약조건 포함)" + " "*16 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        # ===== STEP 1: DWH 테이블 복사 =====
        copy_dwh_tables_to_dm(engine)
        
        # ===== STEP 2: 데이터 품질 검증 (선택적) =====
        if ENABLE_VALIDATION:
            validation_passed = validate_data_quality(engine)
            
            if not validation_passed:
                print("\n⚠️ 경고: 데이터 품질 문제가 발견되었습니다.")
                print("계속 진행하시겠습니까? 제약조건 추가 시 오류가 발생할 수 있습니다.")
                user_input = input("계속하려면 'y' 입력: ")
                if user_input.lower() != 'y':
                    print("작업 중단됨")
                    return
        
        # ===== STEP 3: 제약조건 추가 (선택적) =====
        if ENABLE_CONSTRAINTS:
            add_constraints_to_dm(engine)
        
        # ===== STEP 4: 파생 데이터 생성 =====
        create_derived_data(engine)
        
        if ENABLE_CONSTRAINTS:
            add_derived_data_constraints(engine)
        
        if CREATE_INDEXES:
            create_indexes(engine)
        
        # ===== 완료 =====
        print("\n" + "╔" + "="*68 + "╗")
        print("║" + " "*17 + "✓ DM 구축 완료! (제약조건 포함)" + " "*18 + "║")
        print("╚" + "="*68 + "╝")
        
        print("\n생성된 테이블:")
        print("  - dm.dim_company (PK, FK, UNIQUE)")
        print("  - dm.dim_industry (PK, UNIQUE)")
        print("  - dm.dim_time (PK)")
        print("  - dm.fact_credit_behavior (PK, FK)")
        print("  - dm.fact_financial_statement (PK, FK)")
        print("  - dm.derived_data (PK, FK) ⭐")
        
        if ENABLE_CONSTRAINTS:
            print("\n제약조건 요약:")
            print("  ✓ Primary Key: 모든 테이블")
            print("  ✓ Foreign Key: Fact 테이블 → Dimension 테이블")
            print("  ✓ NOT NULL: 필수 컬럼 (PK, 비즈니스 키)")
            print("  ✓ UNIQUE: 비즈니스 키 (company_id, industry_code)")
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
