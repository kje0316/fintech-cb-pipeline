CREATE TABLE {{DM_SCHEMA}}.derived_data AS
SELECT
    fs.company_sk,
    fs.time_sk,
    
    -- =============================
    -- 금액·규모 파생
    -- =============================
    
    -- fn1_10: 유동자산 합계
    (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0)) AS fn1_10,
    
    -- fn1_13: 자산총계
    (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) AS fn1_13,
    
    -- fn1_19: 부채총계
    (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) AS fn1_19,
    
    -- fn1_24: 자본총계 = 자산총계 - 부채총계
    (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
    (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) AS fn1_24,
    
    -- fn2_2_1: 매출총이익 = 매출액 - 매출원가
    (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0)) AS fn2_2_1,
    
    -- fn2_5: 영업이익 = 매출총이익 - 판관비
    (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) AS fn2_5,
    
    -- fn2_3_1: 법인세차감전순이익
    ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
     COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) AS fn2_3_1,
    
    -- fn2_10: 당기순이익
    (((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
      COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) AS fn2_10,
    
    -- fn2_3_4: 당기순이익(계속사업)
    ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
       COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) - 
     COALESCE(fs.fn2_3_5, 0)) AS fn2_3_4,
    
    -- fn3_1: 감가상각비 총합
    (COALESCE(fs.fn3_2, 0) + COALESCE(fs.fn3_2_1, 0) + COALESCE(fs.fn3_2_2, 0)) AS fn3_1,
    
    -- fn3_11: 운전자본 = 유동자산 - 유동부채
    (COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)) AS fn3_11,
    
    -- fn3_11_1: 순운전자본 = 자기자본 - fn1_10
    (COALESCE(fs.fn1_16, 0) - 
     (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0))) AS fn3_11_1,
    
    -- fn3_7: EBIT
    ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
     COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0) + COALESCE(fs.fn2_4, 0)) AS fn3_7,
    
    -- fn3_3: 자기자본회전율
    CASE 
        WHEN COALESCE(fs.fn3_2, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn1_16, 0) / NULLIF(fs.fn3_2, 0)
    END AS fn3_3,
    
    -- fn3_4: 영업이익률
    CASE 
        WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) / NULLIF(fs.fn2_4, 0)
    END AS fn3_4,
    
    -- fn3_5: EBIT마진
    CASE 
        WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
              COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0) + COALESCE(fs.fn2_4, 0)) / NULLIF(fs.fn2_4, 0)
    END AS fn3_5,
    
    -- fn3_10: 이자보상배율
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE (COALESCE(fs.fn3_10_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
    END AS fn3_10,
    
    -- =============================
    -- 재무비율 (R 계열)
    -- =============================
    
    -- 성장성 비율
    -- r001: 자산증가율
    CASE 
        WHEN COALESCE(fs.fn1_13_1, 0) = 0 THEN NULL
        ELSE (((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - COALESCE(fs.fn1_13_1, 0)) / 
              NULLIF(fs.fn1_13_1, 0)) * 100
    END AS r001,
    
    -- r002: 매출액증가율
    CASE 
        WHEN COALESCE(fs.fn2_1_1, 0) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_1_1, 0)) / NULLIF(fs.fn2_1_1, 0)) * 100
    END AS r002,
    
    -- r003: 영업이익증가율
    CASE 
        WHEN COALESCE(fs.fn2_5_1, 0) = 0 THEN NULL
        ELSE (((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) - 
               COALESCE(fs.fn2_5_1, 0)) / NULLIF(fs.fn2_5_1, 0)) * 100
    END AS r003,
    
    -- r004: 당기순이익증가율
    CASE 
        WHEN COALESCE(fs.fn2_10_1, 0) = 0 THEN NULL
        ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0) - 
               COALESCE(fs.fn2_10_1, 0)) / NULLIF(fs.fn2_10_1, 0)) * 100
    END AS r004,
    
    -- 안정성 비율
    -- r006: 부채비율
    CASE 
        WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) / 
              NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
    END AS r006,
    
    -- r007: 자기자본비율
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE (((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
               (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) / 
              NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
    END AS r007,
    
    -- r008: 유동비율
    CASE 
        WHEN COALESCE(fs.fn1_14, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn1_1, 0) / NULLIF(fs.fn1_14, 0)) * 100
    END AS r008,
    
    -- r009: 당좌비율
    CASE 
        WHEN COALESCE(fs.fn1_14, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn1_3, 0) / NULLIF(fs.fn1_14, 0)) * 100
    END AS r009,
    
    -- r012: 자기자본순이익률
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE (COALESCE(fs.fn1_16, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
    END AS r012,
    
    -- 수익성 비율
    -- r013: 매출원가율
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn2_1, 0)) * 100
    END AS r013,
    
    -- r014: 판관비율
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn2_3, 0) / NULLIF(fs.fn2_1, 0)) * 100
    END AS r014,
    
    -- r015: 영업이익률
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) / 
              NULLIF(fs.fn2_1, 0)) * 100
    END AS r015,
    
    -- r016: 순이익률
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
              NULLIF(fs.fn2_1, 0)) * 100
    END AS r016,
    
    -- r018: ROE (자기자본순이익률)
    CASE 
        WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
        ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
              NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
    END AS r018,
    
    -- r023: ROA (총자산순이익률)
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
              NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
    END AS r023,
    
    -- 활동성 비율
    -- r019: 총자산회전율
    CASE 
        WHEN COALESCE(fs.fn1_11, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_1, 0) / NULLIF(fs.fn1_11, 0)
    END AS r019,
    
    -- r020: 매출채권회전율
    CASE 
        WHEN COALESCE(fs.fn1_4, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn1_4, 0)
    END AS r020,
    
    -- r021: 재고자산회전율
    CASE 
        WHEN COALESCE(fs.fn1_17, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn1_17, 0)
    END AS r021,
    
    -- r022: 자기자본회전율
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)
    END AS r022,
    
    -- =============================
    -- 추가 지표 (N 계열)
    -- =============================
    
    -- n001: 차입금의존도
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
        ELSE (COALESCE(fs.fn1_15, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
    END AS n001,
    
    -- n002: 순운전자본비율
    CASE 
        WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn1_16, 0) - 
               (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0))) / 
              NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
    END AS n002,
    
    -- n003: 운전자본회전율
    CASE 
        WHEN (COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)), 0)
    END AS n003,
    
    -- n004: 매출액순이익률
    CASE 
        WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
        ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
              NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
    END AS n004,
    
    -- n005: 매출총이익률
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0)) / NULLIF(fs.fn2_1, 0)) * 100
    END AS n005,
    
    -- n006: EBITDA마진
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE (COALESCE(fs.fn3_8, 0) / NULLIF(fs.fn2_1, 0)) * 100
    END AS n006,
    
    -- n008: 감가상각비율
    CASE 
        WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn3_2, 0) / NULLIF(fs.fn2_1, 0)
    END AS n008,
    
    -- n010: EBITDA배수
    CASE 
        WHEN COALESCE(fs.fn3_8, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn1_16, 0) / NULLIF(fs.fn3_8, 0)
    END AS n010,
    
    -- n011: 이자비용비율
    CASE 
        WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
        ELSE COALESCE(fs.fn3_8, 0) / NULLIF(fs.fn2_4, 0)
    END AS n011,
    
    -- n012: 자기자본회전율2
    CASE 
        WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
        ELSE COALESCE(fs.fn2_1, 0) / 
             NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                     (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)
    END AS n012
    
FROM {{DM_SCHEMA}}.fact_financial_statement fs