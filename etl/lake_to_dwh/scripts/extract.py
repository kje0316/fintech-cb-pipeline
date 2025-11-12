import pandas as pd

def extract_data(data_path, column_reference_path):
    """
    데이터를 로드하고, 두 번째 컬럼에 고유 ID를 부여한 후,
    참조 파일의 영문 컬럼명으로 통일합니다.
    """

    print(f"'{data_path}'에서 데이터 로드 중...")
    print(f"'{column_reference_path}'에서 컬럼 참조 데이터 로드 중...")
    
    try:
        data_df = pd.read_csv(data_path, encoding='cp949')
        column_ref_df = pd.read_csv(column_reference_path, encoding='cp949')
        
        # 1. 모든 행에 고유한 ID 부여
        unique_ids = pd.Series(range(1, len(data_df)+1), name='COMPANY_ID') 
 
        if len(data_df.columns) < 1:
            raise ValueError("원본 데이터에 컬럼이 충분하지 않아 ID를 두 번째 컬럼에 삽입할 수 없습니다.")
        data_df.insert(1, 'COMPANY_ID', unique_ids)
        print("모든 행에 고유한 ID를 두 번째 컬럼에 부여 완료.")

        # 2. 컬럼명 영문으로 변경
        print("컬럼명 통일 중...")
        if len(data_df.columns) != len(column_ref_df.columns):
            print(f"경고: ID 컬럼 삽입 후 원본 데이터({len(data_df.columns)}개)와 컬럼 참조 파일({len(column_ref_df.columns)}개)의 컬럼 수가 일치하지 않습니다.")
            raise ValueError("ID 컬럼 삽입 후 원본 데이터와 컬럼 참조 파일의 컬럼 수가 일치하지 않습니다.")
        
        new_columns = list(column_ref_df.columns)
        new_columns[1] = 'COMPANY_ID'
        data_df.columns = new_columns

        print("컬럼명 통일 완료.")

        return data_df
    
    except FileNotFoundError as e:
        print(f"오류: 파일을 찾을 수 없습니다 - {e}")
        return None

    except Exception as e: # Catch general exceptions for robustness
        print(f"데이터 추출 및 처리 중 오류 발생: {e}")
        return None
