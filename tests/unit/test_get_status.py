import pytest
from unittest.mock import Mock
from scripts import get_status
import globus_sdk

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture(scope='session')
def db_engine(request):
    """yields a SQLAlchemy engine which is suppressed after the test session"""
    # db_url = request.config.getoption("--dburl")
    db_url = "sqlite:///run_status_test_cache.sqlite"
    engine_ = create_engine(db_url, echo=True)
    
    yield engine_

    engine_.dispose()


@pytest.fixture(scope='session')
def db_session_factory(db_engine):
    """returns a SQLAlchemy scoped session factory"""
    get_status.Base.metadata.create_all(db_engine)
    return scoped_session(sessionmaker(bind=db_engine))


@pytest.fixture(scope='function')
def db_session(db_session_factory):
    """yields a SQLAlchemy connection which is rollbacked after the test"""
    session_ = db_session_factory()

    yield session_

    session_.rollback()
    session_.close()


def _get_mock_run(unique_id: int):
    return {
        "run_id": f"run_id_{unique_id}",
        "label": f"Run {unique_id}",
        "status": "ACTIVE",
    }

@pytest.fixture
def mock_list_runs(monkeypatch):
    class ListRuns():
        data = [{"runs": [_get_mock_run(n) for n in range(10)]}]

        def __call__(self, client, params):
            yield from self.data
    monkeypatch.setattr(get_status, 'client_list_runs', ListRuns())
    return get_status.client_list_runs


def test_get_status_one_run(mock_list_runs, db_session):
    mock_list_runs.data[0]["runs"][1]["status"] = "FAILED"
    run = get_status.get_run(db_session, "run_id_1")
    assert run.run_id == "run_id_1"
    assert run.label == "Run 1"
    assert run.status == "FAILED"
