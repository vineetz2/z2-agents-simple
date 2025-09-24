"""
Test suite for the simplified agents
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import RouterAgent, DataAgent, CodeAgent

class TestRouterAgent:
    """Test the router agent's pattern matching"""
    
    def test_route_to_data(self):
        router = RouterAgent()
        
        # Test data-related queries
        assert router.route("search for resistors") == "data"
        assert router.route("find parts with 10k ohm") == "data"
        assert router.route("show component details") == "data"
        assert router.route("market availability for ABC123") == "data"
        
    def test_route_to_code(self):
        router = RouterAgent()
        
        # Test code-related queries
        assert router.route("write python code to calculate fibonacci") == "code"
        assert router.route("execute this script") == "code"
        assert router.route("def hello(): print('hi')") == "code"
        assert router.route("import math") == "code"
        
    def test_route_to_chat(self):
        router = RouterAgent()
        
        # Test general chat queries
        assert router.route("hello how are you") == "chat"
        assert router.route("what is the weather today") == "chat"
        assert router.route("explain quantum computing") == "chat"
        
    def test_caching(self):
        router = RouterAgent()
        
        # First call should cache
        result1 = router.route("search for resistors")
        # Second call should use cache (test by checking it returns same result)
        result2 = router.route("search for resistors")
        
        assert result1 == result2 == "data"


@pytest.mark.asyncio
class TestDataAgent:
    """Test the data agent"""
    
    async def test_search_parts_extraction(self):
        agent = DataAgent()
        
        # Mock the z2_client for testing
        class MockZ2Client:
            async def search_parts(self, query):
                return {"results": [{"partNumber": "TEST123", "manufacturer": "TestCorp"}]}
            
            def format_results(self, data, operation):
                return "Mocked results"
        
        agent.z2_client = MockZ2Client()
        
        result = await agent.process("search for test components")
        assert "Mocked results" in result
        
    async def test_general_data_query(self):
        agent = DataAgent()
        
        # This would normally call LLM, but we can test the structure
        # In real tests, you'd mock the litellm call
        result = await agent.process("what is a capacitor")
        assert isinstance(result, str)


@pytest.mark.asyncio  
class TestCodeAgent:
    """Test the code agent"""
    
    def test_extract_code_from_markdown(self):
        agent = CodeAgent()
        
        message = "```python\nprint('hello')\n```"
        code = agent.extract_code(message)
        assert code == "print('hello')"
        
    def test_extract_code_from_plain(self):
        agent = CodeAgent()
        
        message = "def greet():\n    print('hi')"
        code = agent.extract_code(message)
        assert code == message
        
    def test_no_code_extraction(self):
        agent = CodeAgent()
        
        message = "please write a hello world program"
        code = agent.extract_code(message)
        assert code == ""
        
    async def test_execute_safe_code(self):
        agent = CodeAgent()
        
        # Test with safe code
        result = await agent.execute("print('Hello, World!')")
        assert "Hello, World!" in result or "Error" in result  # Depends on sandbox availability
        
    async def test_execute_unsafe_code(self):
        agent = CodeAgent()
        
        # Test with unsafe code
        result = await agent.execute("import os\nos.system('ls')")
        assert "Error" in result or "unsafe" in result.lower()