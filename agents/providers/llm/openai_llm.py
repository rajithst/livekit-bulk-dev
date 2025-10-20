"""
OpenAI GPT LLM provider implementation.
"""

from typing import AsyncIterator, List
from openai import AsyncOpenAI

from ..base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    ProviderType
)


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI GPT LLM implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client: AsyncOpenAI = None

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        api_key = self.config.metadata.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self._initialized = True

    def _convert_messages(self, messages: List[LLMMessage]) -> List[dict]:
        """Convert LLMMessage objects to OpenAI format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI."""
        # Add system prompt if configured
        formatted_messages = self._convert_messages(messages)
        if self.config.system_prompt:
            formatted_messages.insert(0, {
                "role": "system",
                "content": self.config.system_prompt
            })
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=formatted_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            **kwargs
        )
        
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content,
            finish_reason=choice.finish_reason,
            tokens_used=response.usage.total_tokens if response.usage else None,
            metadata={
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
            }
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using OpenAI."""
        formatted_messages = self._convert_messages(messages)
        if self.config.system_prompt:
            formatted_messages.insert(0, {
                "role": "system",
                "content": self.config.system_prompt
            })
        
        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=formatted_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.close()
        self._initialized = False

    def get_model_info(self):
        """Get model information."""
        return {
            "provider": ProviderType.OPENAI.value,
            "model": self.config.model,
            "supports_streaming": True,
            "max_tokens": self.config.max_tokens
        }
