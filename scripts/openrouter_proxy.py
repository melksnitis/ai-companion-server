#!/usr/bin/env python3
"""
OpenRouter Model Proxy - Intercepts and rewrites model field to force free model.

Run this proxy, then point ANTHROPIC_BASE_URL to it.
All requests will have their model field rewritten to the free model.
"""

import os
import json
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OpenRouter Model Proxy")

# Configuration
OPENROUTER_BASE = "https://openrouter.ai/api"
FORCE_MODEL = os.getenv("OPENROUTER_MODEL_ID", "xiaomi/mimo-v2-flash:free")
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

print(f"[PROXY] Force model: {FORCE_MODEL}")
print(f"[PROXY] API key set: {bool(API_KEY)}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    """Proxy all requests to OpenRouter, rewriting model field."""
    
    target_url = f"{OPENROUTER_BASE}/{path}"
    
    # Get headers, forward auth
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Use our API key if Authorization header contains the proxy token
    if "authorization" in headers:
        # Replace with real OpenRouter key
        headers["authorization"] = f"Bearer {API_KEY}"
    
    # Get body and rewrite model if present
    body = await request.body()
    original_model = None
    
    if body and request.method == "POST":
        try:
            data = json.loads(body)
            if "model" in data:
                original_model = data["model"]
                data["model"] = FORCE_MODEL
                print(f"[PROXY] Rewrote model: {original_model} -> {FORCE_MODEL}")
                body = json.dumps(data).encode()
        except json.JSONDecodeError:
            pass
    
    # Check if streaming is requested
    is_streaming = False
    if body:
        try:
            data = json.loads(body)
            is_streaming = data.get("stream", False)
        except:
            pass
    
    if is_streaming:
        # Handle streaming response - client must stay open during streaming
        async def stream_response():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params,
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
        )
    else:
        # Handle regular response
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )


if __name__ == "__main__":
    print(f"[PROXY] Starting OpenRouter Model Proxy on http://localhost:9999")
    print(f"[PROXY] Set ANTHROPIC_BASE_URL=http://localhost:9999 to use")
    uvicorn.run(app, host="0.0.0.0", port=9999)
