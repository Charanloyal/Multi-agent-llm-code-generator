import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_serve_dashboard(client):
    response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "AgentCodex" in response.text

@pytest.mark.asyncio
async def test_cache_status_endpoint(client):
    response = await client.get("/api/v1/cache/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "cache_size" in data
    assert "cached_prompts" in data

@pytest.mark.asyncio
async def test_clear_cache_endpoint(client):
    response = await client.post("/api/v1/cache/clear")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_stream_endpoint_success(client):
    """Verifies that the SSE streaming response yields valid event-stream items."""
    async with client.stream(
        "GET", 
        "/api/v1/generate/stream?prompt=redis&max_critiques=1&hops=2&temperature=0.5"
    ) as response:
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]
        
        event_count = 0
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event_count += 1
                assert "status" in line
                
        assert event_count > 0

@pytest.mark.asyncio
async def test_cache_hit_and_clear_integration(client):
    """Runs a full integration scenario: cache miss -> cache hit -> cache status verify -> cache clear."""
    # 1. First run: Cache Miss (max_critiques=1 to run fast)
    async with client.stream(
        "GET", 
        "/api/v1/generate/stream?prompt=caching_test&max_critiques=1&hops=1&temperature=0.3"
    ) as r1:
        assert r1.status_code == status.HTTP_200_OK
        # Consume stream completely to trigger caching
        async for _ in r1.aiter_lines():
            pass
            
    # 2. Second run: Cache Hit (exact same query parameters)
    async with client.stream(
        "GET", 
        "/api/v1/generate/stream?prompt=caching_test&max_critiques=1&hops=1&temperature=0.3"
    ) as r2:
        assert r2.status_code == status.HTTP_200_OK
        lines = []
        async for line in r2.aiter_lines():
            if line.startswith("data: "):
                lines.append(line)
        # Verify cache logs are emitted
        assert any("Cache hit" in l for l in lines)
        assert any("Cache retrieval" in l for l in lines)
        
    # 3. Check Cache Status
    status_response = await client.get("/api/v1/cache/status")
    assert status_response.status_code == status.HTTP_200_OK
    status_data = status_response.json()
    assert status_data["cache_size"] >= 1
    assert "caching_test" in status_data["cached_prompts"]
    
    # 4. Clear Cache
    clear_response = await client.post("/api/v1/cache/clear")
    assert clear_response.status_code == status.HTTP_200_OK
    
    # 5. Check Cache Status again (should be 0)
    status_response_after = await client.get("/api/v1/cache/status")
    assert status_response_after.status_code == status.HTTP_200_OK
    assert status_response_after.json()["cache_size"] == 0

