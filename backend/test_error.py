import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents_simple import DataAgent
from z2data_client import Z2DataClient
import asyncio

async def test():
    z2_client = Z2DataClient()
    agent = DataAgent()
    agent.z2_client = z2_client  # Set the client manually

    # Test litigation API call
    result = await z2_client.get_company_litigations("Toshiba")
    print(f"API Result: success={result.get('success')}, has litigations={bool(result.get('litigations'))}")
    print(f"Result keys: {result.keys()}")
    print(f"Litigations type: {type(result.get('litigations'))}")

    # If it's a dict, check what keys it has
    if isinstance(result.get('litigations'), dict):
        print(f"Litigations keys: {result.get('litigations').keys()}")
        # Check if there's a list inside
        for key, val in result.get('litigations').items():
            print(f"  {key}: type={type(val)}, length={len(val) if hasattr(val, '__len__') else 'N/A'}")

    # Test formatting
    try:
        formatted = agent._format_litigation_response(result)
        print(f"Formatting succeeded!")
        print(f"Response preview: {formatted[:200]}...")
    except Exception as e:
        import traceback
        print(f"Formatting error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())