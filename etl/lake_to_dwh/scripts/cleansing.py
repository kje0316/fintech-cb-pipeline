import pandas as pd
import numpy as np 

import yaml 

def cleanse_data(df_raw, yaml_path):
    """
    원본 데이터를 정제와 타입 변환
    - df_raw: 컬럼명 영문으로 변경된 원본 데이터프레임 
    """
    
    if df_raw is None:
        return {}

    print("데이터 정제 및 변환 시작...")

    df_raw.drop_duplicates(inplace=True)


    # # 주소지시군구 소수점 제거 
    df_raw['CT_CNTY_GU_CD'] = df_raw['CT_CNTY_GU_CD'].astype('Int64').astype(str)

    # # 재무비율 파생컬럼 덮어쓰기 
    # # R001: 총자본순이익률 (당기순이익 / 자산총계)
    # df_raw['R001'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R002: 자기자본순이익률 (당기순이익 / 자본총계)
    # df_raw['R002'] = df_raw['FN2-3'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R006: 부채비율 (부채총계 / 자본총계)
    # df_raw['R006'] = df_raw['FN1-18'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R007: 유동비율 (유동자산 / 유동부채)
    # df_raw['R007'] = df_raw['FN1-1'] / df_raw['FN1-17'].replace(0, np.nan)

    # # R008: 당좌비율 (당좌자산 / 유동부채)
    # df_raw['R008'] = df_raw['FN1-2'] / df_raw['FN1-17'].replace(0, np.nan)

    # # R012: 이자보상배율 (영업이익 / 이자비용)
    # df_raw['R012'] = df_raw['FN2-5'] / df_raw['FN3-4'].replace(0, np.nan)

    # # R013: 총자산회전율 (매출액 / 자산총계)
    # df_raw['R013'] = df_raw['FN2-1'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R014: 매출채권회전율 (매출액 / 매출채권및기타채권) - (맵핑표의 'FN1-3' 항목 사용)
    # df_raw['R014'] = df_raw['FN2-1'] / df_raw['FN1-3'].replace(0, np.nan)

    # # R015: 영업이익률 (영업이익 / 매출액)
    # df_raw['R015'] = df_raw['FN2-5'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R016: 순이익률 (당기순이익 / 매출액)
    # df_raw['R016'] = df_raw['FN2-3'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R018: 자기자본이익률(ROE) (당기순이익 / 자본총계) - (R002와 동일)
    # df_raw['R018'] = df_raw['FN2-3'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R019: 총자산이익률(ROA) (당기순이익 / 자산총계) - (R001과 동일)
    # df_raw['R019'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R020: 자본집약도 (자산총계 / 매출액) - (총자산회전율의 역수)
    # df_raw['R020'] = df_raw['FN1-13'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R021: 매입채무회전율 (매출원가 / 매입채무및기타채무) - (맵핑표의 'FN1-19' 항목 사용)
    # df_raw['R021'] = df_raw['FN2-2'] / df_raw['FN1-19'].replace(0, np.nan)

    # # R022: 재고자산회전율 (매출원가 / 재고자산)
    # df_raw['R022'] = df_raw['FN2-2'] / df_raw['FN1-4'].replace(0, np.nan)

    # # R023: 총자산순이익률 (당기순이익 / 자산총계) - (R001, R019와 동일)
    # df_raw['R023'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R024: 자본금순이익률 (당기순이익 / 자본금)
    # df_raw['R024'] = df_raw['FN2-3'] / df_raw['FN1-20'].replace(0, np.nan)

    # # R025: 유형자산증가율 ((당기 유형자산 - 전기 유형자산) / 전기 유형자산)
    # df_raw['R025'] = (df_raw['FN1-10'] - df_raw['FN1-10.1']) / df_raw['FN1-10.1'].replace(0, np.nan)



    # 타입 변환
    with open(yaml_path, 'r', encoding="utf-8") as f: 
        column_types = yaml.safe_load(f)

    for col in column_types.get('date', []):
        if col in df_raw.columns:
            df_raw[col] = pd.to_datetime(df_raw[col], format="%Y%m%d", errors='coerce')

    for col in column_types.get('str', []):
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].astype('str').str.strip()

    for col in column_types.get('numeric', []):
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
    
    print('데이터 타입 변환 완료.')

    return df_raw



