"""Browser voice call: Silero VAD + Smart Turn -> Whisper -> scope LLM -> Kokoro (D2, D5, D6).

Run from the repo root:
    python -m agent.bot
then open http://localhost:7860/client and press Connect.

Every turn's end-of-speech -> first-audio latency is appended to eval/results/call-latency.jsonl.
"""

import json
import time

import ollama
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.observers.user_bot_latency_observer import UserBotLatencyObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.whisper.stt import Model, WhisperSTTService
from pipecat.transports.base_transport import TransportParams
from pipecat.turns.user_mute.mute_until_first_bot_complete_user_mute_strategy import (
    MuteUntilFirstBotCompleteUserMuteStrategy,
)

from agent.llm import WiseScopeLLM
from agent.policy import GREETING
from agent.scope import ROOT, ClassifierGuard, system_prompt

LLM_MODEL = "qwen3.5:4b"
KOKORO_DIR = "F:/Voice/tts/kokoro"   # model files from the existing local voice stack
LATENCY_LOG = ROOT / "eval" / "results" / "call-latency.jsonl"

GUARD = ClassifierGuard()            # trained once at startup, shared across calls

# Load the LLM onto the GPU and cache the system prompt now, not on the first caller's question.
ollama.Client().chat(
    model=LLM_MODEL,
    messages=[{"role": "system", "content": system_prompt()}, {"role": "user", "content": "hello"}],
    think=False,
    options={"num_predict": 1},
    keep_alive="30m",
)


async def bot(runner_args: RunnerArguments):
    transport = await create_transport(
        runner_args,
        {"webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True)},
    )

    stt = WhisperSTTService(
        settings=WhisperSTTService.Settings(model=Model.LARGE_V3_TURBO.value),
        device="cuda",
        compute_type="float16",
    )
    llm = WiseScopeLLM(model=LLM_MODEL, guard=GUARD)
    tts = KokoroTTSService(
        model_path=f"{KOKORO_DIR}/kokoro-v1.0.onnx",
        voices_path=f"{KOKORO_DIR}/voices-v1.0.bin",
        settings=KokoroTTSService.Settings(voice="af_heart"),
    )

    context = LLMContext(messages=[{"role": "system", "content": system_prompt()}])
    aggregators = LLMContextAggregatorPair(
        context,
        # Silero for speech/silence; Pipecat's default turn strategy (Smart Turn v3) decides
        # when the caller has finished (D10).
        # The caller is muted until the greeting finishes, so the agent can't hear its own
        # greeting through the caller's speakers and answer it.
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_mute_strategies=[MuteUntilFirstBotCompleteUserMuteStrategy()],
        ),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregators.user(),
        llm,
        tts,
        transport.output(),
        aggregators.assistant(),
    ])

    latency = UserBotLatencyObserver()
    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True),
        observers=[latency],
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @latency.event_handler("on_latency_breakdown")
    async def on_breakdown(_observer, breakdown):
        lines = breakdown.turn_contribution_lines()
        for line in lines:
            logger.info(line)
        total = next((l for l in lines if "TOTAL" in l), "")
        # "TOTAL (from client connected)" turns are timed from the connection, not from the end
        # of the caller's speech (no VAD stop was seen); they are not response latency.
        if not total or "from client connected" in total:
            return
        seconds = float(total.split("s", 1)[0])
        parts = {
            l.split("s", 1)[1].split("[")[0].strip(): float(l.split("s", 1)[0])
            for l in lines if "TOTAL" not in l and l.strip()
        }
        LATENCY_LOG.parent.mkdir(exist_ok=True)
        with LATENCY_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "latency_s": seconds, "parts": parts}) + "\n")

    @transport.event_handler("on_client_connected")
    async def on_connected(_transport, _client):
        await task.queue_frames([TTSSpeakFrame(GREETING)])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(_transport, _client):
        await task.cancel()

    await PipelineRunner(handle_sigint=runner_args.handle_sigint).run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
