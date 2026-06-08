import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.services.budget_calculator import seed_travel_type_coefficients


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_travel_type_coefficients(db)
    finally:
        db.close()
    with TestClient(app) as test_client:
        yield test_client
