"""
Test suite for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app

client = TestClient(app)

def test_root_endpoint():
    """Test the health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Agents Simple API"
    assert data["version"] == "0.1.0"

def test_chat_endpoint():
    """Test the REST chat endpoint"""
    response = client.post("/chat", json={
        "content": "Hello",
        "conversation_id": "test-123",
        "role": "user"
    })
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "agent_type" in data
    assert data["agent_type"] in ["chat", "data", "code"]

def test_get_conversation():
    """Test getting conversation history"""
    # First create a conversation
    conv_id = "test-conv-123"
    client.post("/chat", json={
        "content": "Test message",
        "conversation_id": conv_id,
        "role": "user"
    })
    
    # Then retrieve it
    response = client.get(f"/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_id
    assert "messages" in data
    assert len(data["messages"]) >= 2  # User and assistant messages

def test_clear_conversation():
    """Test clearing conversation history"""
    conv_id = "test-clear-123"
    
    # Create a conversation
    client.post("/chat", json={
        "content": "Test",
        "conversation_id": conv_id
    })
    
    # Clear it
    response = client.delete(f"/conversations/{conv_id}")
    assert response.status_code == 200
    
    # Verify it's cleared
    response = client.get(f"/conversations/{conv_id}")
    data = response.json()
    assert len(data["messages"]) == 0

def test_conversation_not_found():
    """Test getting non-existent conversation"""
    response = client.get("/conversations/non-existent-id")
    assert response.status_code == 404
    
def test_file_upload():
    """Test file upload endpoint"""
    # Create a test file
    test_content = b"test,data\n1,2\n3,4"
    
    response = client.post(
        "/upload",
        files={"file": ("test.csv", test_content, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "test.csv"

def test_routing_logic():
    """Test that different queries route to correct agents"""
    
    # Test data routing
    response = client.post("/chat", json={
        "content": "search for resistors",
        "conversation_id": "routing-test-1"
    })
    assert response.json()["agent_type"] == "data"
    
    # Test code routing
    response = client.post("/chat", json={
        "content": "write python code to sort a list",
        "conversation_id": "routing-test-2"
    })
    assert response.json()["agent_type"] == "code"
    
    # Test chat routing
    response = client.post("/chat", json={
        "content": "what is the meaning of life",
        "conversation_id": "routing-test-3"
    })
    assert response.json()["agent_type"] == "chat"