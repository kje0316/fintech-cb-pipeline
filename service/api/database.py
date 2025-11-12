# service/api/database.py
"""
PostgreSQL 데이터베이스 연결 관리
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import sys
import os

# 프로젝트 루트를 Python path에 추가 (shared 모듈 import를 위해)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.config_loader import DB_URL

# SQLAlchemy 엔진 생성
# pool_size: 동시 연결 수
# max_overflow: pool_size를 초과하여 생성 가능한 최대 연결 수
# pool_recycle: 연결 재사용 시간 (초)
engine = create_engine(
    DB_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # 1시간
    echo=False  # SQL 쿼리 로깅 (개발 시 True로 설정 가능)
)

# 세션 팩토리 생성 (ORM 사용 시)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency로 사용할 데이터베이스 세션 제공

    사용 예:
    @app.get("/example")
    def example(db: Session = Depends(get_db)):
        result = db.execute(text("SELECT * FROM table"))
        return result
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_connection():
    """
    직접 connection을 반환 (context manager 사용)

    사용 예:
    with get_connection() as conn:
        result = conn.execute(text("SELECT * FROM table"))
    """
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결 테스트"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL 연결 성공!")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        return False

if __name__ == "__main__":
    # 이 파일을 직접 실행하면 연결 테스트
    test_connection()
