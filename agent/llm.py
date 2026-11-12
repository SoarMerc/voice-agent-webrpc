"""The agent's LLM step for Pipecat: scope label first, then the policy decides what is spoken.

Subclasses Pipecat's Ollama service only for its frame plumbing (context in, text frames out,
interruptions). The request itself goes to Ollama's native API with think=False: Pipecat's
service uses the OpenAI-compatible endpoint, which took ~2.4 s to the first token against
~0.45 s natively for the same prompt (D6).
"""

import time

import ollama
from loguru import logger
from pipecat.frames.frames import EndWorkerFrame, LLMContextFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.ollama.llm import OLLamaLLMService

from agent.policy import CallPolicy
from agent.scope import ClassifierGuard, split_label


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


class WiseScopeLLM(OLLamaLLMService):
    def __init__(self, *, model: str, guard: ClassifierGuard, host: str = "http://localhost:11434", **kwargs):
        super().__init__(settings=OLLamaLLMService.Settings(model=model), **kwargs)
        self._model = model
        self._client = ollama.AsyncClient(host=host)
        self._guard = guard
        self._policy = CallPolicy()
        self._end_call = False

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMContextFrame) and self._end_call:
            # Queued behind the last spoken line, so the caller hears it before the call ends.
            await self.push_frame(EndWorkerFrame(reason="handoff"))

    async def _process_context(self, context):
        messages = [
            {"role": m["role"], "content": _text(m.get("content"))}
            for m in context.get_messages()
            if isinstance(m, dict) and m.get("role") in ("system", "user", "assistant")
        ]
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        previous_agent = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
        started = time.perf_counter()
        if not user_text.strip():
            logger.info("turn skipped: empty transcript (not counted as unclear)")
            return

        label = self._guard.escalation(user_text, previous_agent)
        source = "classifier"
        spoken = ""
        if label is None:
            source = "llm"
            label, spoken = await self._stream_llm(messages)

        if label is not None:
            action = self._policy.decide(label)
            if action.say and not (action.speak_answer and spoken.rstrip().endswith("?")):
                await self._push_llm_text((" " if spoken else "") + action.say)
            self._end_call = action.end_call
        logger.info(
            f"turn label={label} source={source} label_s={time.perf_counter() - started:.2f} "
            f"end_call={self._end_call} user={user_text!r}"
        )

    async def _stream_llm(self, messages):
        """Stream the reply; speak it only if the label allows. Returns (label, spoken_text)."""
        await self.start_ttfb_metrics()
        stream = await self._client.chat(
            model=self._model,
            messages=messages,
            stream=True,
            think=False,
            options={"temperature": 0, "num_predict": 200},
        )
        buffer, label, spoken, speak = "", None, "", False
        try:
            async for chunk in stream:
                delta = chunk.message.content or ""
                if not delta:
                    continue
                if label is None:
                    await self.stop_ttfb_metrics()
                    buffer += delta
                    label, rest = split_label(buffer)
                    if label is None and len(buffer) < 40:
                        continue
                    if label is None:
                        label, rest = "UNCLEAR", ""        # no label: never speak it
                    speak = label in ("ANSWER", "PARTIAL")
                    if not speak:
                        break                              # fixed line instead; stop generating
                    delta = rest
                if speak and delta:
                    spoken += delta
                    await self._push_llm_text(delta)
        finally:
            if hasattr(stream, "aclose"):
                await stream.aclose()
        if label is None:                                  # reply ended inside the label line
            label, _ = split_label(buffer, final=True)
        return label or "UNCLEAR", spoken
