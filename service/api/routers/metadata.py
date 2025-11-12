from fastapi import APIRouter
from typing import List
from ..services import metadata_service

# (수정) 2개의 모델을 모두 import 합니다.
from ..models.metadata import CodeNameMapping, ColumnMapping 

router = APIRouter()

@router.get(
    "/industries", 
    response_model=List[CodeNameMapping], # (이건 OK)
    summary="업종 코드/이름 매핑 조회"
)
async def get_industry_codes():
    return metadata_service.get_industry_mappings()


@router.get(
    "/columns", 
    response_model=List[ColumnMapping], # (⭐️ 수정) CodeNameMapping -> ColumnMapping
    summary="컬럼(지표) 코드/이름 매핑 조회"
)
async def get_column_codes():
    return metadata_service.get_column_mappings()