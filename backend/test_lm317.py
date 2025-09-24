import asyncio
import json
from agents_simple import SimpleAgentOrchestrator
from z2data_client import Z2DataClient

async def test_lm317():
    # Initialize the agents
    agent = SimpleAgentOrchestrator()

    print("Testing LM317-W Texas Instruments Incorporated")
    print("=" * 60)

    # Test the query
    query = "LM317-W Texas Instruments Incorporated"
    result = await agent.process_message(query, "test-conv")

    print(f"Route result type: {result.get('route')}")
    print(f"Agent type: {result.get('agent_type')}")
    print(f"Success: {result.get('success')}")
    print(f"Result keys: {result.keys()}")

    # Check for data field directly
    if result.get('data'):
        print(f"Data type: {type(result['data'])}")
        if isinstance(result['data'], dict):
            print(f"Data keys: {result['data'].keys()}")
            if result['data'].get('type') == 'part_details':
                inner_data = result['data'].get('data', {})
                if 'MPNSummary' in inner_data:
                    mpn = inner_data['MPNSummary']
                    print(f"\n✅ SUCCESS! Found part:")
                    print(f"  Part Number: {mpn.get('MPN')}")
                    print(f"  Manufacturer: {mpn.get('Manufacturer')}")
                    print(f"  Description: {mpn.get('Description')[:100]}..." if mpn.get('Description') else "  Description: N/A")

    if result.get('response'):
        response = result['response']
        if isinstance(response, dict):
            print(f"Response type: {response.get('type')}")
            if response.get('type') == 'part_details':
                data = response.get('data', {})
                if 'MPNSummary' in data:
                    mpn_data = data['MPNSummary']
                    print(f"Found part: {mpn_data.get('MPN')} by {mpn_data.get('Manufacturer')}")
                    print(f"Description: {mpn_data.get('Description')}")
            elif response.get('raw_data'):
                raw_data = response.get('raw_data', {})
                if 'MPNSummary' in raw_data:
                    mpn_data = raw_data['MPNSummary']
                    print(f"Found part: {mpn_data.get('MPN')} by {mpn_data.get('Manufacturer')}")
                    print(f"Description: {mpn_data.get('Description')}")
            elif response.get('sections'):
                print(f"Got sections response with {len(response.get('sections', []))} sections")
                for section in response.get('sections', []):
                    print(f"  Section: {section.get('title')}")
        else:
            print(f"Response preview: {str(response)[:200]}")
    else:
        print("No response received")

    return result

if __name__ == "__main__":
    asyncio.run(test_lm317())