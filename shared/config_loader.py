# shared/config_loader.py (수정)

import yaml
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 자동 탐지
# shared/ 폴더의 부모 디렉토리가 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

CONFIG_FILE_PATH = PROJECT_ROOT / "config" / "local_settings.yaml"

def load_yaml(file_path):
    """YAML 파일을 읽어 딕셔너리로 반환합니다."""
    # Path 객체를 문자열로 변환
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"❌ 설정 파일({file_path})이 없습니다. "
            f"config/local_settings.example.yaml을 복사해서 생성하세요."
        )
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

# 1. Load local settings
config = load_yaml(CONFIG_FILE_PATH)

# DB URLs
db_cfg = config['db']
db_name = db_cfg['db_name']
db_user = db_cfg['user']
db_pass = db_cfg.get('password', '') # 비밀번호가 없는 경우도 처리
db_host = db_cfg['host']
db_port = db_cfg['port']

DB_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
DB_URL_ADMIN = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"

# 2. (⭐️ 신규) 컬럼 매핑 파일의 "내용"도 불러옵니다.
# 상대 경로를 절대 경로로 변환
COLUMNS_MAP_RELATIVE = config['paths']['columns_map']
COLUMNS_MAP_PATH = PROJECT_ROOT / COLUMNS_MAP_RELATIVE
columns_map = load_yaml(COLUMNS_MAP_PATH)