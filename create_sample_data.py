import pandas as pd
import os

# 예측할 샘플 데이터 생성 스크립트
# 로컬에 캐시된 Parquet 데이터에서 5개의 행만 가져와 sample_for_prediction.csv로 저장

DUMP_DIR = 'ml/clustering/data/dump/training_dataset_partitioned'
OUTPUT_FILE = 'sample_for_prediction.csv'

print(f"'{DUMP_DIR}'에서 데이터를 로드하여 샘플 파일을 생성합니다...")

if not os.path.exists(DUMP_DIR):
    print(f"오류: 데이터 덤프 디렉토리가 없습니다. '{DUMP_DIR}'")
    print("먼저 'run_experiment.py'를 한번 실행하여 덤프 데이터를 생성해주세요.")
else:
    df = pd.read_parquet(DUMP_DIR)
    df.head(5).to_csv(OUTPUT_FILE, index=False)
    print(f"샘플 데이터 파일 '{OUTPUT_FILE}'이 성공적으로 생성되었습니다. (5 rows)")
