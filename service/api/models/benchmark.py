# pydantic 모델
from pydantic import BaseModel
from typing import Optional

class BenchmarkResponse(BaseModel):
    industry_code: str
    metric_code: str
    count: int
    avg_value: Optional[float] = None
    median_value: Optional[float] = None
    std_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None

    class Config:
        orm_mode = True
        
        