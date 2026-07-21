"""Conversation-aware ethos agent runtime."""

import asyncio
from collections.abc import AsyncIterator
from copy import copy
from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from ethos.config import EthosSettings, get_settings
from ethos.provider import AIProvider
from ethos.sessions import SessionManager


@dataclass(frozen=True)
class PromptStreamEvent:
    """Provider-neutral prompt text and usage update."""

    text: str = ""
    usage: RunUsage | None = None
    done: bool = False


class AgentRuntime:
    """Reuse one agent with persistent workspace-scoped sessions."""

    def __init__(
        self,
        sessions: SessionManager,
        settings: EthosSettings | None = None,
    ) -> None:
        settings = settings or get_settings()
        provider = AIProvider.from_settings(settings)
        model = provider.model(settings.provider.model_name)

        self._agent = Agent(model, output_type=str)
        self._sessions = sessions
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def run(
        self,
        prompt: str,
        workspace_name: str,
        session_id: str,
    ) -> AsyncIterator[PromptStreamEvent]:
        """Stream and persist one serialised turn in a session."""
        key = (workspace_name, session_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            session = self._sessions.get(workspace_name, session_id)
            if session.archived:
                raise ValueError(f"session is archived: {session_id}")

            # TODO: Add Event here

            async with self._agent.run_stream(
                prompt,
                message_history=session.messages or None,
                conversation_id=str(session.id),
            ) as result:
                emitted = ""
                async for text in result.stream_text():
                    chunk = text[len(emitted) :]
                    emitted = text
                    yield PromptStreamEvent(
                        text=chunk,
                        usage=copy(result.usage),
                    )

                self._sessions.replace_messages(
                    workspace_name,
                    session_id,
                    result.all_messages(),
                )

                # TODO: Add Event here
                yield PromptStreamEvent(
                    usage=copy(result.usage),
                    done=True,
                )


async def run_prompt_singleton(
    prompt: str, settings: EthosSettings | None = None
) -> AsyncIterator[PromptStreamEvent]:
    """Stream one prompt from the configured provider and model."""
    settings = settings or get_settings()
    provider = AIProvider.from_settings(settings)
    model = provider.model(settings.provider.model_name)
    agent = Agent(model, output_type=str)

    async with agent.run_stream(prompt, conversation_id="ask") as result:
        emitted = ""
        async for text in result.stream_text():
            chunk = text[len(emitted) :]
            emitted = text
            yield PromptStreamEvent(text=chunk, usage=copy(result.usage))
        yield PromptStreamEvent(
            usage=copy(result.usage),
            done=True,
        )
