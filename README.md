# Wise "Where is my money?" voice agent

A voice support agent that answers callers' questions about Wise's
["Where is my money?"](https://wise.com/help/topics/5bVKT0uQdBrDp6T62keyfz/sending-money) help
articles and hands everything else to a human. Runs fully local on open-source models: no call
audio or transcript leaves the machine.

> Status: spec and decisions written, no code yet. See `docs/SPEC.md` and `docs/DECISIONS.md`.

## Built on my existing local voice stack

I already run an offline voice setup day to day (push-to-talk dictation with LLM cleanup, and
text-to-speech), so this agent reuses parts I've measured on this exact machine (RTX 5060 Laptop,
8 GB) rather than picking models from a leaderboard:

| Piece | What I already have | What carries over here |
|---|---|---|
| Speech-to-text | Benchmarked 11 local ASR models on one fixed recording (WER, technical-term recall, speed). Parakeet V2 and Whisper Turbo both run well above real time on this GPU. | Model choice from my own numbers; the WER harness to test on caller-style audio. |
| LLM | `qwen3.5:4b` via Ollama as a transcript-cleanup model; it took end-to-end WER from 22.4% to 18.4%. | The model, and one finding that matters a lot for a voice agent: as a reasoning model it spent 90-170 s "thinking" per sentence until I set `reasoning_effort: "none"`, which brought it to ~2 s with no quality loss. |
| Text-to-speech | Kokoro-82M (ONNX, voice `af_heart`) on CPU, about 0.3 real-time factor, with sentence chunking so the first audio plays while the rest is still being generated. | The voice and the chunked streaming approach, keeping the GPU free for speech-to-text and the LLM. |
| Evaluation habit | Held-out test sentences only. Testing on the prompt's own examples once inflated a score from 1/7 to 5/7. | The scope eval is written before the prompt is tuned, and kept separate from it. |

What's new for this task: real-time turn-taking and barge-in (Pipecat), the scope policy (answer,
answer-then-hand-off, hand off), and the evaluation of that policy.

## How it works

See `docs/SPEC.md` for the architecture, the scope policy and the evaluation plan.

## Decisions

See `docs/DECISIONS.md`. In short: fully local and open source (Sei's own stance is that customer
data stays out of the model labs); a browser call instead of a phone number, with the phone version
described; no retrieval because the whole FAQ fits in the prompt; an explicit, testable scope check.

## Run

To be written.

## Results

To be written: scope accuracy, false-answer and false-hand-off rates, latency (median and p90).
