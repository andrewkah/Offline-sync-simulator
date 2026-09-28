import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import db
from main import app


@pytest.fixture
def isolated_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[db.get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    engine.dispose()


@pytest.mark.asyncio
async def test_challenge_payload_duplication(isolated_database):

    challenge_payload = [
        {
            "submission_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
            "urban_council": "Mukono Municipality",
            "pdp_status": "Active",
            "expiry_year": 2032,
            "field_officer_timestamp": "2026-06-03T09:15:00Z",
        },
        {
            "submission_uuid": "6ec0bd7f-11c0-43da-975e-2a8ad9ebae0b",
            "urban_council": "Entebbe Municipal Council",
            "pdp_status": "Expiring",
            "expiry_year": 2026,
            "field_officer_timestamp": "2026-06-03T10:22:11Z",
        },
        {
            "submission_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
            "urban_council": "Mukono Municipality",
            "pdp_status": "Active",
            "expiry_year": 2032,
            "field_officer_timestamp": "2026-06-03T09:15:00Z",
        },
        {
            "submission_uuid": "bc29e1a8-89c0-4fb1-b12e-1b32d20912ab",
            "urban_council": "Gulu City Council",
            "pdp_status": "Missing",
            "expiry_year": None,
            "field_officer_timestamp": "2026-06-03T11:05:45Z",
        },
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/sync/pdp-batch", json={"records": challenge_payload}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_received"] == 4
        assert data["duplicates_dropped"] == 1
        assert data["committed_count"] == 3
        assert (
            data["dropped_records"][0]["submission_uuid"]
            == "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        )
        assert data["dropped_records"][0]["urban_council"] == "Mukono Municipality"
