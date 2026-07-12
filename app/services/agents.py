import asyncio
import json
from typing import AsyncGenerator, Dict, Any

# Template code fragments matching prompt keywords
TEMPLATES = {
    "redis": {
        "v1": '# Draft v1: FastAPI + Redis Rate Limiter\n'
              'from fastapi import FastAPI, Request\n'
              'import redis.asyncio as aioredis\n'
              '\n'
              'app = FastAPI()\n'
              '# Note: redis variable is initialized but not typed\n'
              'redis_client = None\n'
              '\n'
              '@app.on_event("startup")\n'
              'async def startup():\n'
              '    global redis_client\n'
              '    redis_client = aioredis.from_url("redis://localhost:6379")\n'
              '\n'
              '@app.get("/data")\n'
              'async def get_data(request: Request):\n'
              '    # Missing rate limit checks\n'
              '    return {"status": "ok", "message": "data fetched"}',
        
        "v2": '# Draft v2: Refined FastAPI + Redis Rate Limiter (Typing Added)\n'
              'from fastapi import FastAPI, Request\n'
              'import redis.asyncio as aioredis\n'
              'from typing import Optional, Dict\n'
              '\n'
              'app: FastAPI = FastAPI()\n'
              'redis_client: Optional[aioredis.Redis] = None\n'
              '\n'
              '@app.on_event("startup")\n'
              'async def startup() -> None:\n'
              '    global redis_client\n'
              '    redis_client = aioredis.from_url("redis://localhost:6379")\n'
              '\n'
              '@app.get("/data")\n'
              'async def get_data(request: Request) -> Dict[str, str]:\n'
              '    # Added sliding window check\n'
              '    # Redis client is not wrapped in exception safety\n'
              '    await redis_client.ping()\n'
              '    return {"status": "ok", "message": "data fetched"}',
        
        "final": '# Final Production Code: Robust FastAPI + Redis Sliding Window Rate Limiter\n'
                 'from fastapi import FastAPI, Request, HTTPException, status\n'
                 'import redis.asyncio as aioredis\n'
                 'from typing import Optional, Dict, Any\n'
                 'import time\n'
                 '\n'
                 'app: FastAPI = FastAPI(title="Rate Limited Service")\n'
                 'redis_client: Optional[aioredis.Redis] = None\n'
                 'redis_pool: Optional[aioredis.ConnectionPool] = None\n'
                 '\n'
                 '@app.on_event("startup")\n'
                 'async def startup() -> None:\n'
                 '    global redis_client, redis_pool\n'
                 '    try:\n'
                 '        redis_pool = aioredis.ConnectionPool.from_url("redis://localhost:6379", max_connections=20)\n'
                 '        redis_client = aioredis.Redis(connection_pool=redis_pool)\n'
                 '        await redis_client.ping()\n'
                 '    except Exception as e:\n'
                 '        print(f"Failed to connect to Redis: {e}")\n'
                 '\n'
                 '@app.on_event("shutdown")\n'
                 'async def shutdown() -> None:\n'
                 '    if redis_pool:\n'
                 '        await redis_pool.disconnect()\n'
                 '\n'
                 'async def is_rate_limited(client: aioredis.Redis, key: str, limit: int, window: int) -> bool:\n'
                 '    now: float = time.time()\n'
                 '    clear_before: float = now - window\n'
                 '    try:\n'
                 '        async with client.pipeline(transaction=True) as pipe:\n'
                 '            await pipe.zremrangebyscore(key, 0, clear_before)\n'
                 '            await pipe.zadd(key, {str(now): now})\n'
                 '            await pipe.zcard(key)\n'
                 '            await pipe.expire(key, window)\n'
                 '            results = await pipe.execute()\n'
                 '        return results[2] > limit\n'
                 '    except Exception:\n'
                 '        return False # Fail-open strategy\n'
                 '\n'
                 '@app.get("/data")\n'
                 'async def get_data(request: Request) -> Dict[str, Any]:\n'
                 '    if not redis_client:\n'
                 '        raise HTTPException(status_code=500, detail="Redis connection unavailable")\n'
                 '    \n'
                 '    client_ip: str = request.client.host if request.client else "unknown"\n'
                 '    rate_limit_key: str = f"limiter:{client_ip}"\n'
                 '    \n'
                 '    if await is_rate_limited(redis_client, rate_limit_key, limit=5, window=60):\n'
                 '        raise HTTPException(\n'
                 '            status_code=status.HTTP_429_TOO_MANY_REQUESTS,\n'
                 '            detail="Rate limit exceeded. Please try again later."\n'
                 '        )\n'
                 '    return {"status": "success", "data": "High-throughput secure metrics"}\n'
    },
    "default": {
        "v1": '# Draft v1: General Python Script\n'
              'def main():\n'
              '    print("processing request")\n'
              '    # missing return type and logging\n'
              '    x = 10\n'
              '    print("done")',
        
        "v2": '# Draft v2: Script with basic functions and return typing\n'
              'def main() -> int:\n'
              '    # Still missing robust logging structure\n'
              '    print("processing request")\n'
              '    return 0',
        
        "final": '# Final Production Code: Robust Python application with logging\n'
                 'import logging\n'
                 'from typing import Dict, Any\n'
                 '\n'
                 'logging.basicConfig(level=logging.INFO)\n'
                 'logger = logging.getLogger("CodeGeneratorApp")\n'
                 '\n'
                 'def run_process(config: Dict[str, Any]) -> int:\n'
                 '    logger.info("Initializing task execution...")\n'
                 '    try:\n'
                 '        # Run processing logic\n'
                 '        logger.info(f"Task successfully processed with parameters: {config}")\n'
                 '        return 0\n'
                 '    except Exception as e:\n'
                 '        logger.error(f"Process execution failed: {e}")\n'
                 '        return 1\n'
                 '\n'
                 'if __name__ == "__main__":\n'
                 '    config = {"env": "production", "workers": 4}\n'
                 '    run_process(config)'
    }
}

class MultiAgentOrchestrator:
    """
    Simulates a critique-synthesis agent loop.
    Generates logs, runs verification critiques, and updates code versions.
    Yields events suitable for SSE streaming.
    """
    def __init__(self, templates: Dict[str, Any] = TEMPLATES):
        self.templates = templates

    async def generate(
        self, 
        prompt: str, 
        context: str, 
        max_critiques: int = 2, 
        temperature: float = 0.5
    ) -> AsyncGenerator[str, None]:
        """
        Runs the async multi-agent synthesis-critique loop.
        Yields chunk messages formatted as Server-Sent Events (SSE).
        """
        # Determine code template based on query keywords
        code_key = "redis" if "redis" in prompt.lower() or "limiter" in prompt.lower() else "default"
        codes = self.templates[code_key]

        # ----------------------------------------------------
        # STAGE 1: Initial Synthesis
        # ----------------------------------------------------
        yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Analyzing RAG context and requirements...'})}\n\n"
        await asyncio.sleep(0.6)
        
        yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Drafting initial code version v1...'})}\n\n"
        await asyncio.sleep(0.6)

        # Stream code v1 tokens (simulate chunk streaming)
        v1_code = codes["v1"]
        yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Streaming initial draft...' })}\n\n"
        
        # Stream the code in chunks
        chunk_size = len(v1_code) // 5
        for i in range(0, len(v1_code), chunk_size):
            chunk = v1_code[i:i+chunk_size]
            yield f"data: {json.dumps({'status': 'SYNTHESIZING_STREAM', 'code': chunk})}\n\n"
            await asyncio.sleep(0.15)
            
        yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Draft v1 completed.'})}\n\n"
        await asyncio.sleep(0.5)

        # ----------------------------------------------------
        # STAGE 2: Critique & Refinement Loop
        # ----------------------------------------------------
        current_code = v1_code
        iteration = 1
        
        while iteration <= max_critiques:
            yield f"data: {json.dumps({'status': 'CRITIQUING', 'log': f'Critique Agent (Loop {iteration}): Commencing code verification review...'})}\n\n"
            await asyncio.sleep(0.6)

            if iteration == 1:
                # First critique returns issues
                yield f"data: {json.dumps({'status': 'CRITIQUING', 'log': 'CRITIQUE WARNING: Missing explicit variable type annotations.'})}\n\n"
                await asyncio.sleep(0.4)
                yield f"data: {json.dumps({'status': 'CRITIQUING', 'log': 'CRITIQUE WARNING: Missing API exception boundaries around dependencies.'})}\n\n"
                await asyncio.sleep(0.4)
                
                # Hand back to Synthesis Agent
                yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Refactoring v1 to resolve critique issues...' })}\n\n"
                await asyncio.sleep(0.6)
                
                # Stream code v2 (refined)
                current_code = codes["v2"]
                chunk_size = len(current_code) // 5
                for i in range(0, len(current_code), chunk_size):
                    chunk = current_code[i:i+chunk_size]
                    yield f"data: {json.dumps({'status': 'SYNTHESIZING_STREAM', 'code': chunk, 'clear': True if i==0 else False})}\n\n"
                    await asyncio.sleep(0.15)
                    
                yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Refactored draft v2 completed.'})}\n\n"
                await asyncio.sleep(0.5)
                
            elif iteration == 2 or max_critiques >= 2:
                # Final critique validates against production-grade metrics
                yield f"data: {json.dumps({'status': 'CRITIQUING', 'log': 'CRITIQUE NOTICE: Security check passed. Type validations ok.'})}\n\n"
                await asyncio.sleep(0.4)
                yield f"data: {json.dumps({'status': 'CRITIQUING', 'log': 'CRITIQUE NOTICE: Recommending addition of connection pool cleanup handlers.'})}\n\n"
                await asyncio.sleep(0.4)
                
                # Final Synthesis Refinement
                yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Finalizing production-grade script optimization...' })}\n\n"
                await asyncio.sleep(0.6)
                
                current_code = codes["final"]
                chunk_size = len(current_code) // 5
                for i in range(0, len(current_code), chunk_size):
                    chunk = current_code[i:i+chunk_size]
                    yield f"data: {json.dumps({'status': 'SYNTHESIZING_STREAM', 'code': chunk, 'clear': True if i==0 else False})}\n\n"
                    await asyncio.sleep(0.15)
                
                yield f"data: {json.dumps({'status': 'SYNTHESIZING', 'log': 'Synthesis Agent: Final production script compiled.'})}\n\n"
                await asyncio.sleep(0.5)
                break
                
            iteration += 1

        # ----------------------------------------------------
        # STAGE 3: Completed Stream
        # ----------------------------------------------------
        yield f"data: {json.dumps({'status': 'COMPLETED', 'log': 'System Engine: Generation lifecycle complete.', 'final_code': current_code})}\n\n"
