"""
Test script to verify MCP routing for various queries
"""
import asyncio
import sys
from mcp_registry import MCPRegistry
from agents_simple import RouterAgent, DataAgent
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_routing():
    """Test MCP routing for various query types"""

    # Initialize components
    mcp_registry = MCPRegistry()
    router = RouterAgent()
    data_agent = DataAgent()

    # Test queries
    test_queries = [
        "toshiba litigations",
        "company details for Intel",
        "supply chain locations for NXP",
        "DigiKey stock for LM317",
        "RoHS compliance for BAV99",
        "search for TPS62840",
        "find all capacitors by Murata"
    ]

    print("=" * 80)
    print("Testing MCP Registry Analysis")
    print("=" * 80)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)

        # Test MCP registry analysis
        analysis = mcp_registry.analyze_query(query)

        if analysis['tool']:
            print(f"[OK] Tool matched: {analysis['tool']['name']}")
            print(f"  Confidence: {analysis['confidence']:.1f}")
            print(f"  API method: {analysis['tool']['api_method']}")
            print(f"  Parameters extracted:")
            for key, value in analysis['parameters'].items():
                if value:
                    print(f"    - {key}: {value}")
        else:
            print("[X] No tool matched")

        # Test router
        route = await router.route(query)
        print(f"  Router decision: {route}")

    print("\n" + "=" * 80)
    print("Testing DataAgent with MCP Integration")
    print("=" * 80)

    # Test a specific query through the DataAgent
    test_query = "toshiba litigations"
    print(f"\nProcessing query: '{test_query}'")
    print("-" * 40)

    try:
        result = await data_agent.process(test_query)
        print(f"Success: {result.get('success', False)}")
        if result.get('response'):
            print(f"Response preview: {result['response'][:200]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_routing())