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


@app.post(
    "/api/v1/sync/pdp-batch",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_pdp_batch(payload: BatchPayload, db: Session = Depends(db.get_db)):
    seen: Set[str] = set()
    committed: List[dict] = []
    dropped: List[dict] = []

    for item in payload.records:
        item = PDPData.validate_pdp_status()
        # Promote Idempotency
        uuid_str = str(item.submission_uuid)
        db_item = db.query(db.PDPModel).filter(db.PDPModel.id == uuid_str).first()
        if uuid_str in seen or db_item is not None:
            reason = (
                f"Duplicate submission_uuid '{uuid_str}' detected. It has been dropped."
                if uuid_str in seen
                else f"Submission_uuid '{uuid_str}' already saved."
            )
            # Add duplicate to dropped set
            dropped.append(
                DroppedItem(
                    submission_uuid=uuid_str,
                    urban_council=item.urban_council,
                    reason=reason,
                )
            )
            continue
        seen.add(uuid_str)
        # Save to the db
        save_db_item = db.PDPModel(
            id=uuid_str,
            urban_council=item.urban_council,
            pdp_status=item.pdp_status.value,
            expiry_year=item.expiry_year,
            field_officer_timestamp=item.field_officer_timestamp.isoformat(),
            committed_at=datetime.now().isoformat(),
        )
        db.add(save_db_item)
        db.commit()
        db.refresh(save_db_item)
        committed.append(save_db_item)
    return SyncResponse(
        batch_status="PROCESSED",
        total_received=len(payload.records),
        total_synced=len(committed),
        duplicates_dropped=len(dropped),
        committed_records=committed,
        dropped_records=dropped,
    )

