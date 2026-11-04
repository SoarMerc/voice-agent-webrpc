# Handoff (4 Nov 2026)

## Where things stand

- Take-home for Sei AI: a voice support agent for Wise's "Where is my money?" FAQ that deflects
  anything else. Brief, scope policy, architecture and eval plan: `docs/SPEC.md`.
- Decided: run fully local on open-source models (D1); browser call instead of a phone number,
  divergence stated in the README (D2); this repo location (D7). Proposed, need his yes: no RAG
  (D3), explicit scope check (D4), Pipecat (D5), models (D6). All in `docs/DECISIONS.md`.
- Knowledge base: `kb/wise-where-is-my-money.md`, the six articles fetched 3 Nov 2026 through a
  model-processed renderer. Check wording against the live pages before the final run.
- No code yet. Nothing installed yet.

## Context

- Ram Venkataraman (co-founder and CTO, ex-PayPal, Wise, Amazon) said he judges "clarity of
  thinking" and assumes AI was used. No deadline. He prefers self-driven people who don't need specs.
- His GitHub (ramkumarvenkat) is small single-purpose repos with one-line READMEs. Aim for a
  clean, minimal, runnable demo, not breadth.
- Next rounds after this: a 90-120 min technical round of open-ended problems, then a non-technical
  round with the other co-founder. Prep and debriefs live in `F:\CV\interviews\`; application notes
  in `F:\CV\applications\2026-11-02-sei-ai-engineer\`.

## Machine

- RTX 5060 Laptop GPU, 8 GB. Ollama 0.32 with `qwen3.5:4b`, `gemma3:4b` (and others).
- Conda env for this project: `langchain` (D8). Has faster-whisper (CUDA), ollama, openai and
  Pipecat 1.15.0. Base has kokoro_onnx. **Never create venvs or pip-install without asking.**
- Prior voice work to reuse: `F:\Voice` (README: ASR benchmark, qwen3.5 no-think proxy, Kokoro
  chunked streaming). Credited in this README.
- Kokoro model files: `F:\Voice\tts\kokoro\`.

## Next, in order

1. Shivansh: say yes/no to D3-D6 in `docs/DECISIONS.md`.
2. Write `eval/questions.jsonl` and a text-only runner first (no audio). Pick the LLM and the
   one-call vs two-call scope check by the numbers.
3. Wire the Pipecat pipeline with a browser call; measure latency.
4. README with results; record the demo video.
5. Optional: Twilio adapter.

## Rules

- Never push. Shivansh pushes and sends the link himself.
- Conventional Commits with a scope (`docs`, `eval`, `agent`, `kb`).
- File edits via Edit/Write, not sed or inline Python.
