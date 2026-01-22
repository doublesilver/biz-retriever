from typing import Dict, Any
import os
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

class RAGService:
    def __init__(self):
        # Initialize OpenAI Chat Model
        # Ensure API Key is present, otherwise validation error might occur on instantiation
        self.api_key = settings.OPENAI_API_KEY
        self.llm = None
        if self.api_key and self.api_key.startswith("sk-"):
             self.llm = ChatOpenAI(
                model_name="gpt-4o",
                openai_api_key=self.api_key,
                temperature=0
            )

    async def analyze_bid(self, content: str) -> Dict[str, Any]:
        """
        Analyze bid content to extract summary and keywords.
        """
        if not self.llm:
            return {
                "summary": "Analysis failed: Invalid or missing OpenAI API Key.",
                "keywords": []
            }

        messages = [
            SystemMessage(content="You are an AI assistant for analyzing public bid announcements."),
            HumanMessage(content=f"Analyze the following bid announcement and provide a 1-sentence summary and 3 keywords.\n\nContent:\n{content}")
        ]

        try:
            # LangChain async call
            response = await self.llm.apredict_messages(messages)
            result_text = response.content
            
            # Simple parsing (In production, use Structured Output Parser)
            return {
                "summary": result_text,
                "keywords": ["extracted", "from", "llm"] # Placeholder for simple parsing
            }
        except Exception as e:
            print(f"Error during AI analysis: {e}")
            return {
                "summary": "Analysis failed due to an error.",
                "keywords": []
            }

rag_service = RAGService()
