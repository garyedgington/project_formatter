from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ---------------------------------------------------------------------------
# Format endpoint
# ---------------------------------------------------------------------------

SUPPORTED_FROM = {"csv", "xml", "markdown"}
SUPPORTED_TO   = {"json", "html"}

VALID_PAIRS = {
    ("csv",      "json"),
    ("xml",      "json"),
    ("markdown", "html"),
}


class FormatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input: str = Field(..., description="Raw input content to convert")
    from_format: str = Field(..., alias="from", description="Source format: csv | xml | markdown")
    to_format:   str = Field(..., alias="to",   description="Target format: json | html")


class FormatResponse(BaseModel):
    result: str = Field(..., description="Converted output content")
    valid:  Optional[bool]       = Field(default=None, description="Structural validity (only present when ?validate=true)")
    errors: Optional[list[str]]  = Field(default=None, description="Structural errors   (only present when ?validate=true and valid=false)")
