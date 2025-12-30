#!/usr/bin/env python3
"""
Fetch OpenRouter generation details to identify the source of unexpected model calls.

Usage:
    python scripts/check_openrouter_generation.py <generation_id>
    
    # Or check multiple from CSV:
    grep "claude-4.5-haiku" openrouter_activity_*.csv | cut -d',' -f1 | head -3 | xargs -I{} python scripts/check_openrouter_generation.py {}
"""

import asyncio
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx


async def fetch_generation(generation_id: str):
    """Fetch generation details from OpenRouter API."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)
    
    url = f"https://openrouter.ai/api/v1/generation?id={generation_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code != 200:
            print(f"ERROR: API returned {response.status_code}")
            print(response.text)
            return None
        
        return response.json()


def analyze_generation(data: dict):
    """Analyze generation data to identify the caller."""
    print("\n" + "=" * 60)
    print("GENERATION ANALYSIS")
    print("=" * 60)
    
    # Basic info
    print(f"\nGeneration ID: {data.get('id', 'N/A')}")
    print(f"Model: {data.get('model', 'N/A')}")
    print(f"Created: {data.get('created_at', 'N/A')}")
    
    # Cost info
    print(f"\nTotal Cost: ${data.get('total_cost', 0):.6f}")
    print(f"Tokens (prompt): {data.get('tokens_prompt', 0)}")
    print(f"Tokens (completion): {data.get('tokens_completion', 0)}")
    
    # Request details - this is key for identifying the caller
    request = data.get('request', {})
    if request:
        print("\n--- REQUEST DETAILS ---")
        
        # Headers can reveal the caller
        headers = request.get('headers', {})
        print(f"HTTP-Referer: {headers.get('http-referer', 'NOT SET')}")
        print(f"X-Title: {headers.get('x-title', 'NOT SET')}")
        
        # The model requested
        print(f"Model requested: {request.get('model', 'N/A')}")
        
        # Messages can help identify context
        messages = request.get('messages', [])
        if messages:
            print(f"\nFirst message preview:")
            first_msg = messages[0] if messages else {}
            content = first_msg.get('content', '')
            if isinstance(content, str):
                print(f"  Role: {first_msg.get('role', 'N/A')}")
                print(f"  Content: {content[:200]}...")
    
    # Provider info
    print(f"\nProvider: {data.get('provider_name', 'N/A')}")
    print(f"App ID: {data.get('app_id', 'N/A')}")
    print(f"API Key Name: {data.get('api_key_name', 'N/A')}")
    
    print("\n" + "=" * 60)
    
    # Verdict
    referer = request.get('headers', {}).get('http-referer', '')
    model = request.get('model', '')
    
    print("\nVERDICT:")
    if 'haiku' in model.lower() or 'sonnet' in model.lower():
        print(f"  ⚠️  PAID MODEL DETECTED: {model}")
        if referer:
            print(f"  📍 Source hint: {referer}")
        else:
            print("  📍 No HTTP-Referer set - hard to trace source")
            print("     Consider setting HTTP-Referer header in all clients")
    else:
        print(f"  ✅ Free/expected model: {model}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_openrouter_generation.py <generation_id>")
        print("\nExample:")
        print("  python scripts/check_openrouter_generation.py gen-1767116740-7lrapuv3INfw6BtjwpRq")
        sys.exit(1)
    
    generation_id = sys.argv[1]
    print(f"Fetching generation: {generation_id}")
    
    data = await fetch_generation(generation_id)
    if data:
        analyze_generation(data)
        
        # Also dump raw JSON for further inspection
        print("\n--- RAW JSON ---")
        print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
