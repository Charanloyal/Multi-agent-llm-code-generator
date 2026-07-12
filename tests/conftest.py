import os
import sys
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Test client fixture for making requests to FastAPI app."""
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac
