import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.app.services.graph_service import GraphService
from src.app.models.company import CompanyOut
from src.app.models.investor import InvestorOut


@pytest.fixture
def mock_driver():
    with patch("src.app.services.graph_service.get_driver") as mock:
        yield mock


@pytest.fixture
def mock_sentence_transformer():
    with patch("src.app.services.graph_service.SentenceTransformer") as mock:
        yield mock


def test_generate_and_store_embeddings(mock_driver, mock_sentence_transformer):
    # Setup mocks
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

    # Mock company data
    mock_company = CompanyOut(
        company_id="1",
        organization_id="1",
        name="Company A",
        description="Desc A",
        mission="Mission A",
        sectors=["Tech"],
        aliases=[],
        country_code="SE",
        year_founded=None,
        num_employees=None,
        num_shares=None,
        portfolio=[],
        shareholders=[],
        customers=[],
        key_people=[],
        website=None,
    )

    mock_investor = InvestorOut(
        investor_id="2",
        organization_id="2",
        name="Investor B",
        description="Desc B",
        mission="Mission B",
        sectors=["Finance"],
        aliases=[],
        country_code="SE",
        year_founded=None,
        num_employees=None,
        num_shares=None,
        portfolio=[],
        shareholders=[],
        customers=[],
        key_people=[],
        website=None,
    )
    # Mock data fetch
    # We need to simulate the dict structure returned by Neo4j driver, including 'labels'
    company_dict = mock_company.model_dump()
    company_dict["labels"] = ["Company"]

    investor_dict = mock_investor.model_dump()
    investor_dict["labels"] = ["Fund"]
    # Service expects 'company_id' in the dict to map it to 'investor_id'
    investor_dict["company_id"] = mock_investor.investor_id

    mock_result = [company_dict, investor_dict]
    # session.run returns an iterable of records (which behave like dicts)
    mock_session.run.return_value = mock_result

    # Mock encoding
    mock_model = mock_sentence_transformer.return_value
    mock_model.encode.return_value = [np.array([0.1, 0.2]), np.array([0.3, 0.4])]

    # Init service
    service = GraphService()
    service.generate_and_store_embeddings(batch_size=2)

    # Verify fetch called
    args, _ = mock_session.run.call_args_list[0]
    assert "MATCH (n)" in args[0]

    # Verify update called
    args, kwargs = mock_session.run.call_args_list[1]
    assert "SET n._embedding" in args[0]
    assert len(kwargs["updates"]) == 2
    assert kwargs["updates"][0]["company_id"] == "1"
    assert kwargs["updates"][1]["company_id"] == "2"


def test_run_leiden_clustering(mock_driver, mock_sentence_transformer):
    # Setup mocks
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

    # Init service
    service = GraphService()
    service.run_leiden_clustering()

    # Verify calls to GDS procedures
    calls = [args[0] for args, _ in mock_session.run.call_args_list]
    assert any("gds.graph.drop" in c for c in calls)
    assert any("gds.graph.project" in c for c in calls)
    assert any("gds.knn.mutate" in c for c in calls)
    assert any("gds.leiden.write" in c for c in calls)
