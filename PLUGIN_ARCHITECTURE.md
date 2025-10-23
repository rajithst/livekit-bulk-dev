# Plugin Architecture in LiveKit Agent

## Overview
The LiveKit Agent framework employs a plugin architecture to enable flexible integration of AI service providers (STT, LLM, TTS) without tightly coupling them to the main agent logic. This design allows developers to quickly swap between different vendors, add new capabilities, and improve testability.

## Decoupling from Main Agent
- **Provider Interfaces:** Each provider type (STT, LLM, TTS) implements a base interface defined in `agents/providers/base.py`. The main agent interacts only with these interfaces, not with concrete implementations.
- **Provider Factory:** The agent uses a factory (`ProviderFactory`) to instantiate providers based on configuration. This means the agent does not need to know the details of any specific vendor.
- **Configuration Driven:** Providers are selected and configured via settings, allowing runtime changes without code modification.

## Swapping Vendors
- **Pluggable Providers:** New vendors can be added by implementing the base interface and registering with the factory. For example, Azure and OpenAI providers are implemented in separate modules and can be swapped by changing configuration.
- **No Code Changes Required:** To switch vendors, update the configuration (e.g., change provider type from `openai` to `azure`). The agent will automatically use the new provider.
- **Extensible:** Additional providers (e.g., Google, AWS) can be added with minimal effort, supporting future growth and experimentation.

## Improved Testability
- **Mock Providers:** Since the agent only depends on interfaces, mock providers can be injected for unit testing, enabling isolated tests of agent logic.
- **Independent Testing:** Providers can be tested independently from the agent, ensuring reliability and simplifying debugging.
- **Clear Separation:** Decoupling allows for focused tests on provider implementations, agent orchestration, and integration points.

## Benefits
- **Flexibility:** Rapidly experiment with different vendors and models.
- **Maintainability:** Clean separation of concerns reduces complexity and technical debt.
- **Scalability:** Easily add new providers or features without refactoring core agent logic.
- **Testability:** Enables robust unit and integration testing for both agent and providers.

## Example
```
# Configuration
stt_provider: "azure"
llm_provider: "openai"
tts_provider: "azure"

# Agent Initialization
agent = VoiceAssistantAgent(
    stt_config=STTConfig(provider="azure"),
    llm_config=LLMConfig(provider="openai"),
    tts_config=TTSConfig(provider="azure")
)
```

By following this architecture, the LiveKit Agent remains vendor-agnostic, highly modular, and easy to maintain and test.
