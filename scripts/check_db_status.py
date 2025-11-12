"""
데이터베이스 상태 확인 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL
from sqlalchemy import create_engine, text

engine = create_engine(DB_URL)

print("\n" + "="*80)
print("데이터베이스 상태 확인")
print("="*80)

with engine.connect() as conn:
    # 스키마 확인
    print("\n[1] 스키마 목록:")
    print("-"*80)
    result = conn.execute(text("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name IN ('lake', 'dwh', 'marts', 'public')
        ORDER BY schema_name
    """))
    schemas = [row[0] for row in result]
    for schema in schemas:
        print(f"  ✓ {schema}")

    if not schemas:
        print("  ✗ lake, dwh, marts 스키마가 없습니다!")

    # 각 스키마별 테이블 확인
    for schema in ['lake', 'dwh', 'marts']:
        print(f"\n[2] {schema} 스키마의 테이블:")
        print("-"*80)
        result = conn.execute(text(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = '{schema}'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]

        if tables:
            for table in tables:
                # 행 개수 확인
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}"))
                    count = count_result.scalar()
                    print(f"  ✓ {schema}.{table}: {count:,} rows")
                except Exception as e:
                    print(f"  ✗ {schema}.{table}: 조회 실패 ({e})")
        else:
            print(f"  ✗ {schema} 스키마에 테이블이 없습니다!")

print("\n" + "="*80)
