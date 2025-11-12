from pydantic import BaseModel
from typing import List

# 1. "업종" API를 위한 모델 (키: industry_code, industry_name)
class CodeNameMapping(BaseModel):
    industry_code: str
    industry_name: str

# 2. "컬럼" API를 위한 모델 (키: code, name)
class ColumnMapping(BaseModel):
    code: str
    name: str

