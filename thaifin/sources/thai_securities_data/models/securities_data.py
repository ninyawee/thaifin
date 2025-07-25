from pydantic import BaseModel, Field
from typing import Optional


class SecurityData(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., 'PTT', 'KBANK')")
    name: str = Field(..., description="Company name")
    market: str = Field(..., description="Market type (e.g., 'SET', 'mai')")
    industry: Optional[str] = Field(
        ..., description="Industry (e.g., 'อสังหาริมทรัพย์และก่อสร้าง')"
    )
    sector: str = Field(..., description="Sector (e.g., '-')")
    address: Optional[str] = Field(..., description="Company address")
    zip: str = Field(..., description="ZIP code")
    tel: str = Field(..., description="Telephone number")
    fax: str = Field(..., description="Fax number")
    web: Optional[str] = Field(..., description="Company website")
