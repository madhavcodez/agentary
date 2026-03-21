import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.ingest.greenhouse import GreenhouseConnector


@pytest.mark.asyncio
async def test_greenhouse_fetch():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 123,
                "title": "Software Engineer",
                "location": {"name": "San Francisco, CA"},
                "content": "<p>Build amazing things</p>",
                "absolute_url": "https://boards.greenhouse.io/test/jobs/123",
            }
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        connector = GreenhouseConnector(board_tokens=["test"])
        results = await connector.fetch()

        assert len(results) == 1
        assert results[0].title == "Software Engineer"
        assert results[0].company == "Test"
        assert results[0].source == "greenhouse"


def test_hard_filter():
    from app.services.match_engine import _passes_hard_filter

    assert _passes_hard_filter("Software Engineer", "Build ML models") is True
    assert _passes_hard_filter("ML Engineer", None) is True
    assert _passes_hard_filter("VP of Engineering", None) is False
    assert _passes_hard_filter("Staff Software Engineer", None) is False
    assert _passes_hard_filter("Marketing Manager", None) is False
