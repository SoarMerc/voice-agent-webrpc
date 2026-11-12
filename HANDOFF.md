# Handoff (12 Nov 2026)

## Where things stand

- Take-home for Sei AI: a voice support agent for Wise's "Where is my money?" FAQ that hands
  anything else to a human. Spec `docs/SPEC.md`, decisions D1-D15 `docs/DECISIONS.md`.
- Browser call built: `python -m agent.bot`, then http://localhost:7860/client. Pipeline in
  `agent/bot.py`, scope step in `agent/llm.py`, call policy in `agent/policy.py` (tests in
  `tests/test_policy.py`; pytest isn't installed, run the functions directly).
- Text eval final (held-out, 62 lines): 90% accuracy, 0 false answers, 3 false handoffs.
- Faithfulness: 8 of 31 answers unsupported (previous prompt). Known limitation; answer bank is
  the documented next step, deliberately not built (Shivansh: close the project).
- Branch `feat/eval-set`, not pushed.

## Left to do (Shivansh)

1. Make a few real calls: check barge-in, the handoff lines, and that the call ends after one.
   Latency lands in `eval/results/call-latency.jsonl`; put median and p90 in the README.
2. Record the 2-3 minute demo video; link it in the README.
3. Push and send the link.

## Context

- Ram Venkataraman (co-founder and CTO) judges "clarity of thinking" and assumes AI was used.
  Next rounds: a 90-120 min technical round, then a non-technical round. Prep in
  `F:\CV\interviews\`.

## Machine

- RTX 5060 Laptop GPU, 8 GB. Ollama 0.32 (`ollama serve` if the API is down) with `qwen3.5:4b`.
- Conda env `langchain`: call `C:\Users\Shivansh\miniconda3\envs\langchain\python.exe` directly
  (`conda run` crashes). Never pip-install without asking.
- Kokoro files: `F:\Voice\tts\kokoro\`.

## Rules

- Never push. Shivansh pushes and sends the link himself.
- Conventional Commits with a scope (`docs`, `eval`, `agent`, `kb`).
- File edits via Edit/Write, not sed or inline Python.
