# Handoff (11 Nov 2026)

## Where things stand

- Take-home for Sei AI: a voice support agent for Wise's "Where is my money?" FAQ that deflects
  anything else. Brief, scope policy, architecture and eval plan: `docs/SPEC.md`.
- Decisions D1-D14 in `docs/DECISIONS.md`. All decided except D10 (end of turn: Smart Turn v3 vs
  silence timeout, needs a recorded test). D4's classifier (LLM first-line label, small
  embedding classifier, or a cascade) is picked by the eval.
- Knowledge base: `kb/wise-where-is-my-money.md`, verbatim from the live pages (pasted by
  Shivansh, 11 Nov 2026).
- System prompt with spoken-style rules and class labels: `agent/system_prompt.md` (D14).
- Text-level eval done (12 Nov): `eval/run_scope.py`, results in README. Held-out accuracy 83%
  with the LLM label plus classifier escalation. Faithfulness review in `eval/faithfulness.md`:
  6 of 31 answers unsupported (invented timings, guesses about the caller's transfer).
- Waiting on Shivansh: D4's proposed combination; the 3 "unsure" + 4 sample answers in
  `eval/faithfulness.md`; whether q40's `out` label is wrong; how to fix faithfulness.
- No pipeline code yet.

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
- Conda env `langchain` (D8): faster-whisper (CUDA), ollama, openai, Pipecat 1.15.0 (Smart Turn
  v3 included), sentence-transformers, scikit-learn, kokoro-onnx 0.6.1. Call its python directly:
  `C:\Users\Shivansh\miniconda3\envs\langchain\python.exe` (`conda run` crashes here).
  **Never create venvs or pip-install without asking.**
- Prior voice work to reuse: `F:\Voice` (README: ASR benchmark, qwen3.5 no-think proxy, Kokoro
  chunked streaming). Credited in this README. Kokoro model files: `F:\Voice\tts\kokoro\`.

## Next, in order

1. Fix faithfulness (Shivansh picks the approach), re-run the held-out set once.
2. Wire the Pipecat pipeline with a browser call; run the D10 end-of-turn test; measure latency.
3. Faithfulness review (D13): Claude labels, Shivansh reviews the unsure ones and a sample.
4. README with results; record the demo video.
5. Optional, not yet: Twilio adapter.

## Rules

- Never push. Shivansh pushes and sends the link himself.
- Conventional Commits with a scope (`docs`, `eval`, `agent`, `kb`).
- File edits via Edit/Write, not sed or inline Python.
