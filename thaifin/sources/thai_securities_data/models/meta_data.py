from __future__ import annotations
from pydantic import BaseModel, Field

class MetaData(BaseModel):
    last_updated: str = Field(..., description="The last updated timestamp of the metadata.")
    total_securities: int = Field(..., description="The total number of securities available.")

    class Markets(BaseModel):
        SET: int = Field(..., description="Number of securities in the SET market.")
        mai: int = Field(..., description="Number of securities in the mai market.")

    markets: Markets = Field(..., description="Market-level data for securities.")

    sectors: dict[str, int] = Field(..., description="Dynamic sector data with sector names as keys and counts as values.")

    data_source: str = Field(..., description="The data source URL for the metadata.")

    class ApiEndpoints(BaseModel):
        all_securities: str = Field(..., description="API endpoint for all securities data.")
        compact: str = Field(..., description="API endpoint for compact securities data.")
        metadata: str = Field(..., description="API endpoint for metadata.")
        by_sector: str = Field(..., description="API endpoint for sector-wise securities data.")
        market_set: str = Field(..., description="API endpoint for SET market data.")
        market_mai: str = Field(..., description="API endpoint for mai market data.")

    api_endpoints: ApiEndpoints = Field(..., description="API endpoints for accessing securities data.")

    class ExportInfo(BaseModel):
        generated_by: str = Field(..., description="The generator of the export information.")
        files_exported: list[str] = Field(..., description="List of files exported.")
        export_schema: dict[str, str] = Field(..., alias="schema", description="Schema mapping field names to descriptions.")

    export_info: ExportInfo = Field(..., description="Export information for the metadata.")
