import pandas as pd
import os
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine
from load_to_postgres import load_table_from_db
# 설정
table_name = "dim_company"            # 불러올 테이블 이름 
yaml_path = "./config/col_types.yaml" # 컬럼 타입 정의 yaml 파일

df = load_table_from_db(table_name, yaml_path)
print("✓ 데이터 로드 및 타입 변환 완료!")

print(f"\n{'='*70}")
print(f"테이블 크기: {df.shape}")

print(f"\n{'='*70}")
print("데이터프레임 정보:")
df.info()

print(f"\n{'='*70}")
print(f"'{table_name}' 테이블의 상위 5개 행:")
print(df.head())

