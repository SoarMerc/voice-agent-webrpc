# Spec: Wise "Where is my money?" voice support agent

Take-home for Sei AI (received 3 Nov 2026 from Ram Venkataraman, co-founder and CTO). No deadline.
He said he is judging **clarity of thinking** and assumes AI was used.

## The brief (verbatim)

> Build a simple voice agent that can handle incoming calls (use any open source or any provider):
>
> 1. The agent is a customer support representative that can handle inquiries about any of these
>    FAQs: https://wise.com/help/topics/5bVKT0uQdBrDp6T62keyfz/sending-money (only "Where is my
>    money" section)
> 2. When the bot sees any question other than the above, it should deflect to a human agent (for
>    this exercise, it can respond and cut the call)

## What "done" looks like

1. A caller starts a voice call, asks questions in natural speech, and hears short spoken answers
   grounded only in the six FAQ articles (`kb/wise-where-is-my-money.md`).
2. Any question outside that scope gets one deflection line ("Let me connect you to a colleague who
   can help with that"), then the call ends.
3. The caller can interrupt the agent mid-sentence (barge-in).
4. A test set with measured results: answer-vs-deflect accuracy, and answer faithfulness.
5. A README a reviewer can read in five minutes: what it does, how to run it, the decisions, the
   numbers, and what I'd do next. A 2-3 minute demo video.

## Scope policy (the core of the exercise)

The agent's knowledge is exactly the six articles:

1. How do I check my transfer's status?
2. When will my money arrive?
3. Why does it say my transfer's complete when the money hasn't arrived yet?
4. Why is my transfer taking longer than the estimate?
5. What is a proof of payment?
6. What's a banking partner reference number?

Each caller turn falls into one of four classes:

| Class | Example | Behaviour |
|---|---|---|
| **In scope** | "My recipient says the money hasn't arrived but the app says complete." | Answer from the FAQ, two or three spoken sentences, then "Anything else about your transfer?" |
| **In scope, needs the account** | "Where's my transfer 4471? It was due Monday." | The agent can't see accounts. Give the general answer (tracker, working days, receipt), then deflect for the specific transfer. |
| **Out of scope** | Fees, exchange rates, cancelling, card problems, opening an account, anything not about where money is. | Deflect and end the call. |
| **Small talk / unclear** | "Hello?", "Sorry, what?", silence. | Greet or ask them to repeat; never deflect on the first unclear turn. Deflect after two unclear turns in a row. |

Edge cases to decide explicitly (and test):
- Topics the articles only link out to (cancelling a completed transfer, wrong bank details, Interest
  or Stocks thresholds): **deflect**; the agent says only what the six articles say.
- Mixed question ("When will it arrive, and what are your fees?"): answer the in-scope part, then
  deflect for the rest.
- Requests to act (cancel, refund, change details): deflect; the agent never takes actions.
- Prompt injection / "ignore your instructions": treat as out of scope.
- Distress or fraud claims ("I think I've been scammed"): deflect immediately.

## Architecture

```
caller (browser call, WebRTC)
  -> voice activity detection (Silero) + barge-in
  -> speech-to-text: faster-whisper on local GPU
  -> turn handler:
       1. scope check (in / needs-account / out / unclear)
       2. answer from the full FAQ text in the prompt, or a fixed deflection line
  -> LLM: local model via Ollama
  -> text-to-speech: Kokoro (local, CPU)
  -> caller
```

Framework: Pipecat (open source, Python). Everything runs on one machine; no call audio or
transcript leaves it. See `DECISIONS.md` for why each choice was made.

## Evaluation

- `eval/questions.jsonl`: 40-60 caller utterances labelled with the expected class (and, for in-scope,
  the article that answers it). Mix of plain, paraphrased, spoken-style ("uh, so my money's like
  not there yet"), edge cases from the list above, and injection attempts.
- Text-level run (no audio): scope accuracy, confusion matrix, false-answer rate (answered when it
  should have deflected: the costly error) and false-deflect rate.
- Faithfulness spot check: every in-scope answer's claims must appear in the FAQ text.
- Latency on real calls: time from end of caller speech to first audio, median and p90.

## Deliverables

- `README.md` (what, run, decisions, results, next steps), `docs/` (this spec, decisions),
  `eval/` (questions, runner, results), demo video link.
- Pushed to a GitHub repo by Shivansh; link sent to Ram.

## Non-goals

- Real account lookups or actions on transfers.
- Multi-language support.
- A production phone deployment (see D2 in `DECISIONS.md`: phone is a transport adapter, documented).
