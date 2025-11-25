"""
엑셀 입력 템플릿 생성 스크립트
30개 필수 입력 컬럼 + 샘플 데이터
"""
import pandas as pd
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows


def create_excel_template():
    """엑셀 템플릿 파일 생성"""

    # 템플릿 저장 경로
    template_dir = Path("templates")
    template_dir.mkdir(exist_ok=True)
    template_path = template_dir / "재무정보_입력템플릿.xlsx"

    # 엑셀 워크북 생성
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # 기본 시트 제거

    # ======================================
    # Sheet 1: 입력 가이드
    # ======================================
    ws_guide = wb.create_sheet("입력가이드", 0)

    guide_data = [
        ["재무정보 입력 템플릿", "", "", ""],
        ["", "", "", ""],
        ["사용 방법", "", "", ""],
        ["1. '데이터입력' 시트로 이동하세요", "", "", ""],
        ["2. 30개 필수 컬럼에 기업 재무 데이터를 입력하세요", "", "", ""],
        ["3. '샘플데이터' 시트를 참고하여 형식을 확인하세요", "", "", ""],
        ["4. 입력 완료 후 파일을 저장하세요", "", "", ""],
        ["5. 웹사이트에서 이 파일을 업로드하세요", "", "", ""],
        ["", "", "", ""],
        ["필수 입력 항목 (37개)", "", "", ""],
        ["", "", "", ""],
        ["카테고리", "항목 수", "설명", ""],
        ["재무상태표(당기)", "12개", "자산, 부채, 자본, 유형자산, 매입채무 등", ""],
        ["손익계산서", "8개", "매출, 영업이익, 당기순이익 등", ""],
        ["현금흐름/기타", "6개", "현금흐름, EBIT, EBITDA 등", ""],
        ["전년도 데이터", "4개", "자산, 매출, 유동자산, EBITDA (성장성 계산)", ""],
        ["기업정보", "2개", "종업원수, 외감여부", ""],
        ["연체정보", "7개", "연체 과목수, 연체일수, 세금체납", ""],
        ["", "", "", ""],
        ["주의사항", "", "", ""],
        ["• 모든 금액은 천원 단위로 입력하세요", "", "", ""],
        ["• 연체정보가 없으면 0을 입력하세요", "", "", ""],
        ["• 외감여부는 Y 또는 N으로 입력하세요", "", "", ""],
        ["• 이자비용(fn2_4)은 선택사항입니다", "", "", ""],
    ]

    for row_idx, row_data in enumerate(guide_data, 1):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws_guide.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 1:  # 제목
                cell.font = Font(size=16, bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            elif row_idx in [3, 10, 19]:  # 섹션 제목
                cell.font = Font(size=12, bold=True)
                cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    ws_guide.column_dimensions['A'].width = 30
    ws_guide.column_dimensions['B'].width = 15
    ws_guide.column_dimensions['C'].width = 40

    # ======================================
    # Sheet 2: 데이터 입력 (가로 형식)
    # ======================================
    ws_input = wb.create_sheet("데이터입력", 1)

    # 컬럼 정의 (37개)
    columns = [
        # 재무상태표 (12개)
        ("fn1_13", "자산총계(당기)", "천원"),
        ("fn1_1", "유동자산(당기)", "천원"),
        ("fn1_4", "재고자산", "천원"),
        ("fn1_11", "매출채권", "천원"),
        ("fn1_19", "부채총계", "천원"),
        ("fn1_24", "자본총계", "천원"),
        ("fn1_14", "유동부채", "천원"),
        ("fn1_15", "단기차입금", "천원"),
        ("fn1_16", "차입금", "천원"),
        ("fn1_유형자산", "유형자산(당기)", "천원"),
        ("fn1_매입채무", "매입채무", "천원"),
        ("fn3_적립금", "적립금", "천원"),

        # 손익계산서 (8개)
        ("fn2_1", "매출액(당기)", "천원"),
        ("fn2_2", "매출원가", "천원"),
        ("fn2_2_1", "매출총이익", "천원"),
        ("fn2_3", "판매비와관리비", "천원"),
        ("fn2_5", "영업이익(당기)", "천원"),
        ("fn2_5_1", "영업이익(전기)", "천원"),
        ("fn2_10", "당기순이익(당기)", "천원"),
        ("fn2_10_1", "당기순이익(전기)", "천원"),

        # 현금흐름/기타 (6개)
        ("fn3_1", "현금흐름", "천원"),
        ("fn3_2", "영업활동현금흐름", "천원"),
        ("fn3_7", "EBIT", "천원"),
        ("fn3_8", "EBITDA(당기)", "천원"),
        ("fn3_11_1", "순차입금", "천원"),
        ("fn2_4", "이자비용", "천원"),

        # 전년도 데이터 (4개) - 성장성 계산용
        ("fn1_13_전기", "자산총계(전기)", "천원"),
        ("fn2_1_전기", "매출액(전기)", "천원"),
        ("fn1_1_전기", "유동자산(전기)", "천원"),
        ("fn3_8_전기", "EBITDA(전기)", "천원"),

        # 기업정보 (2개)
        ("empe_cnt", "종업원수", "명"),
        ("wg_gb", "외감여부", "Y/N"),

        # 연체정보 (7개)
        ("da0d00029", "연체과목수(1년내발생)", "개"),
        ("da0d00026", "연체과목수(1년내유지)", "개"),
        ("da0d00035_1", "최장연체일수(1년)", "일"),
        ("da0d00035_2", "최장연체일수(기타)", "일"),
        ("da0d00033_1", "최장연체일수(3개월)", "일"),
        ("db0d00006", "30일이상연체(미해제)", "개"),
        ("d2b000002", "세금체납", "999999999=없음"),
    ]

    # 1행: 컬럼명 (fn1_13, fn1_1, ...)
    for col_idx, (col_name, _, _) in enumerate(columns, 1):
        cell = ws_input.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True, color="FFFFFF", size=9)
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 2행: 항목명 (자산총계, 유동자산, ...)
    for col_idx, (_, col_desc, _) in enumerate(columns, 1):
        cell = ws_input.cell(row=2, column=col_idx, value=col_desc)
        cell.font = Font(bold=True, size=9)
        cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 3행: 단위 (천원, 명, Y/N, ...)
    for col_idx, (_, _, unit) in enumerate(columns, 1):
        cell = ws_input.cell(row=3, column=col_idx, value=unit)
        cell.font = Font(size=8, italic=True)
        cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 4행: 입력 행 (사용자가 여기에 데이터 입력)
    for col_idx in range(1, len(columns) + 1):
        cell = ws_input.cell(row=4, column=col_idx, value="")
        cell.fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")

    # 열 너비 조정
    for col_idx in range(1, len(columns) + 1):
        ws_input.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 12

    # 행 높이 조정
    ws_input.row_dimensions[2].height = 30

    # ======================================
    # Sheet 3: 샘플 데이터 (가로 형식)
    # ======================================
    ws_sample = wb.create_sheet("샘플데이터", 2)

    # 샘플 데이터 (정상 기업 예시)
    sample_data = {
        # 재무상태표 (12개)
        "fn1_13": 100000,
        "fn1_1": 60000,
        "fn1_4": 15000,
        "fn1_11": 20000,
        "fn1_19": 60000,
        "fn1_24": 40000,
        "fn1_14": 30000,
        "fn1_15": 10000,
        "fn1_16": 25000,
        "fn1_유형자산": 35000,
        "fn1_매입채무": 12000,
        "fn3_적립금": 8000,
        # 손익계산서 (8개)
        "fn2_1": 500000,
        "fn2_2": 350000,
        "fn2_2_1": 150000,
        "fn2_3": 80000,
        "fn2_5": 30000,
        "fn2_5_1": 25000,
        "fn2_10": 20000,
        "fn2_10_1": 15000,
        # 현금흐름/기타 (6개)
        "fn3_1": 22000,
        "fn3_2": 25000,
        "fn3_7": 32000,
        "fn3_8": 38000,
        "fn3_11_1": 15000,
        "fn2_4": 2000,
        # 전년도 데이터 (4개)
        "fn1_13_전기": 90000,
        "fn2_1_전기": 450000,
        "fn1_1_전기": 55000,
        "fn3_8_전기": 35000,
        # 기업정보 (2개)
        "empe_cnt": 50,
        "wg_gb": "Y",
        # 연체정보 (7개 - 정상 기업)
        "da0d00029": 0,
        "da0d00026": 0,
        "da0d00035_1": 0,
        "da0d00035_2": 0,
        "da0d00033_1": 0,
        "db0d00006": 0,
        "d2b000002": 999999999
    }

    # 1행: 컬럼명
    for col_idx, (col_name, _, _) in enumerate(columns, 1):
        cell = ws_sample.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True, color="FFFFFF", size=9)
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 2행: 항목명
    for col_idx, (_, col_desc, _) in enumerate(columns, 1):
        cell = ws_sample.cell(row=2, column=col_idx, value=col_desc)
        cell.font = Font(bold=True, size=9)
        cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 3행: 단위
    for col_idx, (_, _, unit) in enumerate(columns, 1):
        cell = ws_sample.cell(row=3, column=col_idx, value=unit)
        cell.font = Font(size=8, italic=True)
        cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 4행: 샘플 값
    for col_idx, (col_name, _, _) in enumerate(columns, 1):
        cell = ws_sample.cell(row=4, column=col_idx, value=sample_data.get(col_name, 0))
        cell.fill = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 열 너비 조정
    for col_idx in range(1, len(columns) + 1):
        ws_sample.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 12

    # 행 높이 조정
    ws_sample.row_dimensions[2].height = 30

    # 파일 저장
    wb.save(template_path)
    print(f"✅ 엑셀 템플릿 생성 완료: {template_path}")
    print(f"   - 시트 1: 입력가이드 (사용 방법)")
    print(f"   - 시트 2: 데이터입력 (37개 필수 컬럼)")
    print(f"   - 시트 3: 샘플데이터 (정상 기업 예시)")
    print(f"   ※ 클러스터링 피처 70개 전부 생성 가능")

    return template_path


if __name__ == "__main__":
    template_path = create_excel_template()
    print(f"\n템플릿 파일 위치: {template_path.absolute()}")
