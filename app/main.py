import os
import json
import hashlib
from contextlib import asynccontextmanager
from typing import Dict, Any, Generator
from fastapi import FastAPI, Request, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.rag import MultiHopRAGEngine
from app.services.agents import MultiAgentOrchestrator

# Global services
rag_engine = None
agent_orchestrator = None
generation_cache: Dict[str, Dict[str, Any]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start up services and initialize objects."""
    global rag_engine, agent_orchestrator
    rag_engine = MultiHopRAGEngine()
    agent_orchestrator = MultiAgentOrchestrator()
    print("Multi-Agent Code Generator Engines initialized.")
    yield
    generation_cache.clear()
    print("Shutdown: cache flushed.")

app = FastAPI(
    title="Multi-Agent LLM Code Generator",
    description="Prototype of a multi-agent Python code synthesizer with simulated agents (no LLM calls), keyword-based multi-hop retrieval, SSE streaming, and in-memory caching.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static and templates folders
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Renders the developer dashboard UI."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/v1/generate/stream")
async def stream_generation(
    prompt: str = Query(..., description="Prompt detailing request requirements"),
    max_critiques: int = Query(2, ge=1, le=4),
    hops: int = Query(2, ge=1, le=2),
    temperature: float = Query(0.5, ge=0.0, le=1.0)
):
    """
    Streams multi-agent retrieval and synthesis progress in real-time.
    Serves repeated identical requests from an in-memory cache instead of re-running the steps.
    """
    global rag_engine, agent_orchestrator, generation_cache
    
    # Compute query cache key hash
    cache_key_raw = f"{prompt.strip().lower()}:{max_critiques}:{hops}:{temperature:.1f}"
    cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()

    async def sse_event_generator():
        # Step 1: Check Cache
        if cache_key in generation_cache:
            cached_data = generation_cache[cache_key]
            cached_code = cached_data["code"]
            
            yield f"data: {json.dumps({'status': 'RETRIEVING', 'log': 'System Cache: Cache hit detected! Fetching pre-compiled artifacts...' })}\n\n"
            import asyncio
            await asyncio.sleep(0.3)
            
            yield f"data: {json.dumps({'status': 'RETRIEVING', 'log': 'System Cache: Restoring contexts and streaming cached tokens...' })}\n\n"
            await asyncio.sleep(0.3)
            
            yield f"data: {json.dumps({'status': 'SYNTHESIZING_STREAM', 'code': cached_code})}\n\n"
            await asyncio.sleep(0.3)
            
            yield f"data: {json.dumps({'status': 'COMPLETED', 'log': 'System Cache: Cache retrieval complete.', 'final_code': cached_code})}\n\n"
            return

        # Step 2: Cache Miss -> Run RAG
        yield f"data: {json.dumps({'status': 'RETRIEVING', 'log': 'System Engine: Cache miss. Initializing Multi-Hop RAG engine...' })}\n\n"
        import asyncio
        await asyncio.sleep(0.4)
        
        rag_output = rag_engine.retrieve(prompt, hops=hops)
        for log in rag_output["logs"]:
            yield f"data: {json.dumps({'status': 'RETRIEVING', 'log': log})}\n\n"
            await asyncio.sleep(0.3)
            
        # Step 3: Run Multi-Agent Loop and capture generated code
        final_code = ""
        async for event in agent_orchestrator.generate(prompt, rag_output["context"], max_critiques, temperature):
            yield event
            
            # Parse the event to extract code for caching on completion
            if event.startswith("data: "):
                try:
                    payload = json.loads(event[6:].strip())
                    if payload.get("status") == "SYNTHESIZING_STREAM" and "code" in payload:
                        # If a "clear" flag is set, reset code buffer
                        if payload.get("clear", False):
                            final_code = payload["code"]
                        else:
                            final_code += payload["code"]
                    elif payload.get("status") == "COMPLETED" and "final_code" in payload:
                        final_code = payload["final_code"]
                except Exception:
                    pass
                    
        # Step 4: Write to Cache on successful completion
        if final_code:
            generation_cache[cache_key] = {
                "code": final_code,
                "prompt": prompt
            }

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.post("/api/v1/cache/clear")
async def clear_cache():
    """Wipes the cache clean."""
    generation_cache.clear()
    return JSONResponse(
        content={"status": "success", "message": "In-memory caching layer cleared."},
        status_code=status.HTTP_200_OK
    )

@app.get("/api/v1/cache/status")
async def get_cache_status():
    """Returns the size and keys in the cache."""
    return JSONResponse(
        content={
            "cache_size": len(generation_cache),
            "cached_prompts": [v["prompt"] for v in generation_cache.values()]
        },
        status_code=status.HTTP_200_OK
    )
