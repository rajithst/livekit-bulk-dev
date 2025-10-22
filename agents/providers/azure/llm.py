"""
Azure OpenAI LLM provider implementation.
"""

import logging
from typing import AsyncIterable, Dict, List, Optional, Union, AsyncIterator
from livekit import rtc
from livekit.plugins import openai as lk_openai
from ..base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

class AzureLLMProvider(BaseLLMProvider):
    """
    Azure OpenAI LLM provider using LiveKit's plugin system.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.llm = None

    async def initialize(self) -> None:
        """Initialize the LLM provider."""
        try:
            # Use LiveKit's built-in Azure OpenAI plugin
            self.llm = lk_openai.Chat.with_azure(
                api_version=self.config.metadata.get("api_version", "2023-05-15"),
                azure_endpoint=self.config.metadata["azure_endpoint"],
                azure_deployment=self.config.metadata["azure_deployment"],
                api_key=self.config.metadata["api_key"]
            )
            logger.info("Azure LLM provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure LLM: {str(e)}", exc_info=True)
            raise

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        try:
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
            response = await self.llm.create(
                messages=formatted_messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=False
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                finish_reason=response.choices[0].finish_reason,
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else None
            )
                
        except Exception as e:
            logger.error(f"LLM response generation failed: {str(e)}", exc_info=True)
            raise

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM."""
        try:
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
            response = await self.llm.create(
                messages=formatted_messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                
        except Exception as e:
            logger.error(f"LLM response generation failed: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up any resources."""
        if self.llm:
            await self.llm.aclose()