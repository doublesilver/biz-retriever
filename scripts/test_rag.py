
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock Env
os.environ["PROJECT_NAME"] = "Test Project"
os.environ["SECRET_KEY"] = "test"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "pass"
os.environ["POSTGRES_DB"] = "db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["OPENAI_API_KEY"] = "sk-test-mock"

# Mock ChatOpenAI before importing RAGService
with patch("langchain_community.chat_models.ChatOpenAI") as MockChat:
    # Setup Mock Response
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Summary: This is a test summary."
    
    # Configure async predict method
    async def async_predict(*args, **kwargs):
        return mock_response
    
    mock_llm.apredict_messages.side_effect = async_predict
    MockChat.return_value = mock_llm

    from app.services.rag_service import rag_service

    async def test_rag():
        print("Testing RAG Service...")
        
        # Test analyze_bid
        content = "This is a detailed bid announcement content for testing purposes."
        result = await rag_service.analyze_bid(content)
        
        print(f"Analysis Result: {result}")
        assert "summary" in result
        assert result["summary"] == "Summary: This is a test summary."
        
        print("RAG Service verified successfully.")

if __name__ == "__main__":
    asyncio.run(test_rag())
