import re
from typing import List, Dict, Any

# Mock Knowledge Base containing standard documentation and code snippets
KNOWLEDGE_BASE = [
    {
        "id": "fastapi_basic",
        "title": "FastAPI App & Server Initialization",
        "keywords": ["fastapi", "app", "startup", "uvicorn", "lifespan"],
        "content": "To initialize a FastAPI application with lifespan events, use: \n"
                   "from fastapi import FastAPI\n"
                   "from contextlib import asynccontextmanager\n"
                   "@asynccontextmanager\n"
                   "async def lifespan(app: FastAPI):\n"
                   "    # Run on startup (e.g., connect to database)\n"
                   "    yield\n"
                   "    # Run on shutdown\n"
                   "app = FastAPI(lifespan=lifespan)"
    },
    {
        "id": "redis_connection",
        "title": "Asynchronous Redis Connection Pool Manager",
        "keywords": ["redis", "connection", "pool", "async", "cache"],
        "content": "Manage async Redis connections using redis-py:\n"
                   "import redis.asyncio as aioredis\n"
                   "class RedisManager:\n"
                   "    def __init__(self, redis_url: str):\n"
                   "        self.pool = aioredis.ConnectionPool.from_url(redis_url)\n"
                   "    async def get_client(self):\n"
                   "        return aioredis.Redis(connection_pool=self.pool)"
    },
    {
        "id": "redis_rate_limiting",
        "title": "Sliding Window Rate Limiter using Redis ZSET",
        "keywords": ["rate", "limiting", "zset", "sliding", "window", "redis"],
        "content": "Implement sliding window rate limiting in FastAPI via Redis Sorted Sets (ZSET):\n"
                   "import time\n"
                   "async def is_rate_limited(redis_client, key: str, limit: int, window: int) -> bool:\n"
                   "    now = time.time()\n"
                   "    clear_before = now - window\n"
                   "    async with redis_client.pipeline(transaction=True) as pipe:\n"
                   "        await pipe.zremrangebyscore(key, 0, clear_before)\n"
                   "        await pipe.zadd(key, {str(now): now})\n"
                   "        await pipe.zcard(key)\n"
                   "        await pipe.expire(key, window)\n"
                   "        results = await pipe.execute()\n"
                   "    request_count = results[2]\n"
                   "    return request_count > limit"
    },
    {
        "id": "pydantic_schemas",
        "title": "Pydantic v2 Data Validation Schemas",
        "keywords": ["pydantic", "validation", "schema", "field", "model"],
        "content": "Write Pydantic models for request/response serialization:\n"
                   "from pydantic import BaseModel, Field\n"
                   "class UserRequest(BaseModel):\n"
                   "    username: str = Field(..., min_length=3, max_length=20)\n"
                   "    email: str\n"
                   "    age: int = Field(..., ge=0, le=120)"
    },
    {
        "id": "sse_streaming",
        "title": "Server-Sent Events (SSE) Streaming in FastAPI",
        "keywords": ["sse", "streaming", "event", "source", "generator"],
        "content": "To stream real-time events using SSE, use FastAPI's StreamingResponse:\n"
                   "from fastapi.responses import StreamingResponse\n"
                   "import asyncio\n"
                   "async def event_generator():\n"
                   "    for i in range(5):\n"
                   "        yield f'data: {{\"step\": {i}, \"status\": \"running\"}}\\n\\n'\n"
                   "        await asyncio.sleep(0.5)\n"
                   "return StreamingResponse(event_generator(), media_type='text/event-stream')"
    }
]

class MultiHopRAGEngine:
    """
    Implements a multi-hop RAG retrieval agent:
    1. Hop 1: Performs keyword matching on the raw query to find initial relevant documentation.
    2. Hop 2: Parses keywords from the retrieved initial context to trigger secondary documentation searches.
    3. Combines contexts to supply comprehensive reference context.
    """
    def __init__(self, documents: List[Dict[str, Any]] = KNOWLEDGE_BASE):
        self.documents = documents

    def _keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """Finds documents that match keywords in the query."""
        tokens = set(re.findall(r'\b\w+\b', query.lower()))
        matches = []
        for doc in self.documents:
            score = 0
            for keyword in doc["keywords"]:
                if keyword in tokens:
                    score += 1
            if score > 0:
                matches.append((doc, score))
        # Sort by match score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in matches]

    def retrieve(self, query: str, hops: int = 2) -> Dict[str, Any]:
        """
        Runs multi-hop RAG retrieval.
        Returns a log of operations and the final combined context string.
        """
        logs = []
        retrieved_ids = set()
        retrieved_docs = []

        # Hop 1: Query Search
        logs.append(f"Hop 1: Querying knowledge base for '{query}'...")
        hop1_results = self._keyword_search(query)
        if hop1_results:
            for doc in hop1_results[:2]: # Limit to top 2
                if doc["id"] not in retrieved_ids:
                    retrieved_ids.add(doc["id"])
                    retrieved_docs.append(doc)
                    logs.append(f"Hop 1: Retrieved '{doc['title']}' (ID: {doc['id']})")
        else:
            logs.append("Hop 1: No documents found.")

        # Hop 2: Secondary Context Search (if hops >= 2 and we have retrieved docs)
        if hops >= 2 and retrieved_docs:
            # Extract secondary keywords from primary retrieved content
            combined_content = " ".join([doc["content"] for doc in retrieved_docs])
            extracted_keywords = []
            
            # Find keywords from other documents that appear in the retrieved context
            for doc in self.documents:
                if doc["id"] not in retrieved_ids:
                    for keyword in doc["keywords"]:
                        if re.search(r'\b' + re.escape(keyword) + r'\b', combined_content.lower()):
                            extracted_keywords.append(keyword)
                            
            if extracted_keywords:
                search_query = " ".join(extracted_keywords)
                logs.append(f"Hop 2: Query expanded with extracted dependencies: '{search_query}'")
                hop2_results = self._keyword_search(search_query)
                for doc in hop2_results:
                    if doc["id"] not in retrieved_ids:
                        retrieved_ids.add(doc["id"])
                        retrieved_docs.append(doc)
                        logs.append(f"Hop 2: Retrieved dependency documentation '{doc['title']}' (ID: {doc['id']})")
                        break # Limit to 1 secondary dependency
            else:
                logs.append("Hop 2: No secondary dependencies detected.")

        # Combine content
        if retrieved_docs:
            context_string = "\n\n=== REFERENCE SNIPPET ===\n".join([
                f"Title: {doc['title']}\nContent:\n{doc['content']}" for doc in retrieved_docs
            ])
        else:
            context_string = "No relevant reference documentation was retrieved."

        return {
            "logs": logs,
            "context": context_string
        }
