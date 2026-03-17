import openai
import os
from typing import List, Dict, Any, Generator
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("No OpenAI API key provided - using mock responses")

    def _build_prompt(self, context: str, question: str, conversation_history: List[Dict] = None) -> str:
        """Build the RAG prompt with context and conversation history."""

        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context.
        Always be accurate, concise, and cite specific information from the context when relevant.
        If the context doesn't contain enough information to answer the question, say so clearly.
        Format your response naturally and conversationally."""

        # Add conversation history if available
        if conversation_history and len(conversation_history) > 1:
            # Get last few exchanges
            recent_history = conversation_history[-6:]  # Last 3 exchanges
            history_text = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_history
            ])
            system_prompt += f"\n\nConversation History:\n{history_text}"

        user_prompt = f"""
Context: {context}

Question: {question}

Please provide a comprehensive but concise answer based on the context above."""

        return system_prompt, user_prompt

    def generate(self, context: str, question: str, conversation_history: List[Dict] = None) -> str:
        """Generate answer using RAG with OpenAI."""
        if not self.api_key:
            # Mock response
            return f"Based on the provided context, here's what I found: {context[:300]}... (This is a mock response - configure OPENAI_API_KEY for real responses)"

        try:
            system_prompt, user_prompt = self._build_prompt(context, question, conversation_history)

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for more factual responses
                top_p=0.9
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer for question: {question[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"I apologize, but I encountered an error while processing your question. Please try again. Error: {str(e)}"

    def generate_stream(self, context: str, question: str, conversation_history: List[Dict] = None) -> Generator[str, None, None]:
        """Generate streaming answer using RAG with OpenAI."""
        if not self.api_key:
            # Mock streaming response
            response = f"Based on the provided context, here's what I found: {context[:300]}..."
            for word in response.split():
                yield word + " "
                import time
                time.sleep(0.05)  # Simulate streaming delay
            return

        try:
            system_prompt, user_prompt = self._build_prompt(context, question, conversation_history)

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3,
                top_p=0.9,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.get('content'):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"

# Legacy functions for backward compatibility
def generate_answer(context: str, question: str) -> str:
    """Legacy function - use RAGPipeline class instead."""
    pipeline = RAGPipeline()
    return pipeline.generate(context, question)

def mock_generate_answer(context: str, question: str) -> str:
    """Mock answer for testing."""
    return f"Mock response: Based on context '{context[:100]}...', answering: {question}"