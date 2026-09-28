from datetime import datetime
from enum import Enum
from typing import List, Optional, Set
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from fastapi import FastAPI, status, Depends
from src import db

app = FastAPI()

db.Base.metadata.create_all(bind=db.engine)

# @app.get("/")
# def read_root():
# 	return {"Hello":"World"}


class PDPStatus(str, Enum):
    ACTIVE = "Active"
    EXPIRING = "Expiring"
    MISSING = "Missing"
    EXPIRED = "Expired"


class PDPData(BaseModel):
    submission_uuid: UUID
    urban_council: str = Field(..., min_length=2, max_length=150)
    pdp_status: PDPStatus
    expiry_year: Optional[int] = Field(..., ge=1, le=9999)
    field_officer_timestamp: datetime

    @model_validator(mode="after")
    def validate_pdp_status(self) -> "PDPData":
        if self.pdp_status in PDPStatus:
            raise ValueError(f"Unknown pdp_status!")
        return self


class BatchPayload(BaseModel):
    records: List[PDPData]


class DroppedItem(BaseModel):
    submission_uuid: str
    urban_council: str
    reason: str


class SyncResponse(BaseModel):
    batch_status: str
    total_received: int
    total_synced: int
    duplicates_dropped: int
    committed_records: List[dict]
    dropped_records: List[DroppedItem]


