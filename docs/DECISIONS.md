# Decisions

Each entry: what we chose, why, and what would change the decision. Status is **decided** (by
Shivansh) or **proposed** (needs his yes).

## D1. Run everything locally on open-source models (decided, 4 Nov 2026)

Speech-to-text, LLM and text-to-speech all run on the developer machine (RTX 5060 Laptop, 8 GB).

- Why: Sei's own stance is that customer data never goes to the model labs. A support call about
  someone's money is exactly that kind of data. Keeping audio and transcripts on one machine shows
  the same instinct.
- Cost: smaller models than a hosted API, so latency and answer quality need measuring (see Eval).
- Would change if: the eval shows the local LLM can't hold the scope line reliably; then a hosted
  model behind a clear data boundary, stated in the README.

## D2. Browser call instead of a phone number (decided, 4 Nov 2026)

The "incoming call" is a browser voice call (WebRTC), not a phone number.

- Why: a number pointing at a laptop only answers while the laptop, tunnel and GPU are up, so a
  reviewer would most likely watch the demo video anyway. The carrier (e.g. Twilio) would also see
  call audio, which cuts against D1. The work being judged (scope policy, turn handling, latency,
  evaluation) is identical either way.
- The README states this divergence from "incoming calls" up front and describes the phone version:
  in Pipecat, a Twilio Media Streams transport plus a serializer, roughly 30 lines, and the carrier
  as the only third party in the audio path.
- Would change if: Shivansh wants the extra step; the Twilio adapter is optional and built last.

## D3. No retrieval (RAG); the whole FAQ goes in the prompt (decided, 11 Nov 2026)

- Why: six short articles, about 1,500 words. That fits easily in a small model's context.
  Retrieval would add a failure mode (wrong chunk) and latency, with nothing gained at this size.
- Would change if: the knowledge base grew past what fits comfortably (hundreds of articles), or
  answers needed per-article citations; then hybrid retrieval with a reranker.

## D4. Scope check as an explicit step, not only a prompt instruction (decided, 11 Nov 2026; classifier picked by the eval)

Every caller turn is classified (in scope / needs account / out of scope / unclear) before any
answer is generated; out-of-scope turns get a fixed deflection line, never generated text.

- Why: the costly error is answering something it shouldn't (invented fees, a promise about a
  specific transfer). A separate, testable decision makes that error measurable and keeps the
  deflection wording fixed. It mirrors how Sei routes low-confidence items to a human.
- Open: which classifier. Three candidates, measured on the same eval set:
  1. **LLM, one call:** the model writes the class on its first line, then the answer. The class
     line is read and stripped as it streams; an out-of-scope class cancels generation and plays
     the fixed line. (Not JSON `{class, answer}`: the answer can't stream to TTS until it parses.)
  2. **Small classifier:** sentence embeddings (e.g. `bge-small` / `all-MiniLM`) plus logistic
     regression, or SetFit. ~10-30 ms, and can't be talked out of its class by "ignore your
     instructions". Its confidence score gives a threshold to trade false answers against false
     handoffs explicitly. Costs: needs training examples kept separate from the eval set (written
     paraphrases), handles mixed questions and context-dependent follow-ups poorly, and the open
     "everything else" class is hard for a nearest-neighbour model.
  3. **Cascade:** the classifier decides when confident; the uncertain band falls through to
     option 1. In-scope answers still run with the stay-in-the-FAQ prompt, so there are two guards.
  - The latency gain from 2 and 3 is mainly on handoffs (instant, no LLM call). In-scope turns
    still wait for the LLM, and Ollama caches the FAQ prompt prefix, so classifying inside the
    answer call costs only a few tokens. The stronger reasons for a classifier are injection
    resistance and a tunable threshold.
  - `sentence-transformers` and `scikit-learn` are already in the `langchain` env; SetFit is not.
- Result (12 Nov 2026, held-out set; README "Results"): LLM label 82%, classifier 80%,
  confidence cascade 83-85%. **Decided (12 Nov 2026): the LLM label, with the classifier only
  allowed to escalate to urgent or unclear** (83%). The classifier is reliable on those two classes and
  unreliable on "in scope" (it called fees and weather in scope), so it may only make the agent
  more cautious, never make it answer. Simple to explain, and false answers stay bounded by the
  LLM.
- Narrowed 13 Nov 2026 after live calls: **urgent only, at confidence >= 0.45**. On real
  transcripts it ended a call on a garbled in-scope line (urgent at 0.31) and its "unclear"
  blocked "Bye." from reaching DONE. Held-out result unchanged (90%, 0 false answers): its only
  win there was the injection line, caught at 0.55.

## D5. Pipecat as the framework (decided, 11 Nov 2026)

- Why: open source, Python, handles the hard real-time parts (voice activity detection, barge-in,
  streaming between stages), supports browser calls and a Twilio transport, and has local
  faster-whisper and Ollama integrations.
- Alternative: LiveKit Agents (heavier setup: server plus SIP trunk for phones).

## D6. Models: reuse the measured local voice stack (decided, 11 Nov 2026)

Shivansh's own offline voice setup (`F:\Voice`, README there) already benchmarked these on this
machine. Reuse it rather than choose fresh:

- Speech-to-text: candidates from his 11-model ASR benchmark. Parakeet V2 (his daily driver,
  9.6x real time) or Whisper Turbo (60x real time, 26.4% WER on his technical-dictation test).
  Whisper has a ready Pipecat integration (faster-whisper, already in the `langchain` env);
  Parakeet would need a small custom Pipecat STT service. Start with Whisper, swap if the
  caller-style eval says so.
- LLM: `qwen3.5:4b` via Ollama (his cleanup model). **Must** send `reasoning_effort: "none"`
  (or route through his `F:\Voice\proxy\ollama_nothink_proxy.py`): with thinking on it took
  90-170 s per sentence; off, ~2 s. `gemma3:4b` as the comparison on the scope eval. His finding:
  prompt bulk hurt gemma3:4b and helped qwen3.5, so measure, don't assume.
- Text-to-speech: Kokoro-82M ONNX, voice `af_heart`, on CPU, with the sentence-chunked streaming
  from `F:\Voice\tts\speak_clipboard.py`.
- The README credits this prior work in a "Built on my existing local voice stack" section.
- GPU memory: Whisper Turbo plus `qwen3.5:4b` are expected to fit in 8 GB together. Measure
  with both loaded during a call before the latency run.
- Measured 12 Nov 2026 on the dev set: `qwen3.5:4b` 83%, `gemma3:4b` 21%, `qwen3.5:9b` 79% (9
  replies skipped the label; only 5.1 of 6.0 GB fit on the GPU even without Whisper). The 9B was
  deleted. Call Ollama's native API with `think: false`, not the OpenAI-compatible endpoint
  (2.6 s vs 0.6 s to first token).

## D7. Repo location (decided, 4 Nov 2026)

`F:\Products\sei-voice-agent`, its own git repo. Not `F:\TomatoSoup` (that is the published
hint-ladder-eval project) and not the CV repo.

## D8. Python environment: the existing `langchain` conda env (decided, 4 Nov 2026)

Pipecat 1.15.0 installed there with extras `webrtc,silero,whisper,ollama,runner`. torch (CUDA),
numpy and faster-whisper were untouched. Known side effect: OpenTelemetry packages moved to
1.45.2, so the env's existing `opentelemetry-exporter-otlp-proto-grpc` 1.39.0 now has a version
mismatch (only matters if something in the env exports traces over gRPC). `kokoro-onnx` 0.6.1
added on 11 Nov 2026 (with `phonemizer`, `espeakng-loader`, `dlinfo`; numpy and onnxruntime
untouched).

## D9. Soft handoff: strict about topic, forgiving about the turn (decided, 11 Nov 2026)

Out-of-scope and needs-account turns get a fixed line that names the topic and offers one more
in-scope question before the call ends. Unclear turns hand off on the third in a row, not the
second, and silence doesn't count. Actions, fraud or distress, and injection still hand off
immediately. Details in `SPEC.md`, "Handoff behaviour".

- Why: in the demo a handoff hangs up, so a false handoff costs as much as a false answer. One
  misclassification, a natural follow-up ("and the fees?") or two bad transcripts would otherwise
  lose the caller. The brief allows cutting the call; it doesn't require doing it on the first
  wrong guess.
- Cost: one extra turn on real out-of-scope calls, and a little more state (strike counter,
  pending-handoff flag).
- Would change if: the eval shows callers or the classifier abusing the extra turn, e.g.
  out-of-scope questions answered on the second try.

## D10. End of turn: Smart Turn v3 vs a plain silence timeout (open, needs a test)

How the agent decides the caller has finished. Two layers in Pipecat 1.15:

- Silero VAD only says speech or silence, per ~30 ms chunk. Installed defaults: `confidence=0.7`,
  `start_secs=0.2`, `stop_secs=0.2`.
- A turn strategy turns that into "the caller is done":
  - **Smart Turn v3** (Pipecat's default, local, CPU): after each 0.2 s pause it looks at the last
    ~8 s of audio and judges whether the sentence sounds finished. "My transfer to… uh…" is
    judged incomplete, so the agent waits. A fallback silence timer still ends the turn if the
    caller stays quiet.
  - **Speech timeout:** end the turn after a fixed silence (default 0.6 s). Simpler; cuts off
    hesitant callers if short, feels slow if long.
- Test: about ten recorded caller-style utterances with mid-sentence pauses, played through both.
  Count cut-offs and measure end-of-speech to first audio. Start on Smart Turn v3.

## D11. Conversation memory: the whole call, appended (decided, 11 Nov 2026)

Each turn the LLM gets the fixed system prompt (instructions plus the full FAQ), then every
caller and agent turn of this call so far, then the new utterance.

- Why: calls are short, so the whole history fits; follow-ups ("and on a Friday?") need it. The
  system prompt stays first and unchanged, so Ollama reuses its cached prefix and only the new
  turns are processed. Pipecat's context aggregator keeps this history, and on barge-in it stores
  only the part of the agent's reply the caller actually heard.
- Limit: keep the last 10 exchanges if a call runs long.
- Not summarising turns: an exchange here is a few dozen tokens, so a summary saves almost nothing.
  It would also cost a second LLM call on the same 8 GB GPU while the next turn is being served,
  and a summary can drop or distort what was said. Policy state (unclear-turn strikes, a pending
  handoff) lives in code variables, never in the prompt history.
- Would change if: calls ran long enough to pass the 10-exchange cap; then a rolling summary of
  the dropped turns. Cheapest form: the same answer call writes a one-line summary after the
  spoken reply (as the class goes first), stripped before TTS. Costs a few tokens every turn and
  is lost when the caller barges in, so the code falls back to the raw turn.
- The scope check sees the previous exchange plus the new utterance.

## D12. Classifier training data written by Claude, kept apart from the eval (decided, 11 Nov 2026)

Training paraphrases for the small classifier (D4 option 2) go in `eval/train.jsonl`, written
without looking at `eval/questions.jsonl`. No sentence is reused between the two.

## D13. Faithfulness review split between Shivansh and Claude (decided, 11 Nov 2026)

Claude checks every in-scope answer against the FAQ and marks each as supported, unsupported or
unsure. Every "unsure", plus a random sample of the rest, goes to Shivansh, and disagreements
between the two are reported in the README.

## D14. Spoken answer style (decided, 11 Nov 2026)

Rules for what the agent says, in `agent/system_prompt.md`. From voice design guidance (Google
conversation design, the Alexa "one-breath test", Rasa and Vapi voice prompting guides):

- Lead with the answer. One idea per turn.
- At most three sentences, about 40 words: it should be sayable in roughly one breath.
- No lists read aloud. Steps become "First… then… then…". At most three items in a turn; longer
  ones (the seven things a proof of payment must show) give three, then "Want the rest?".
- Numbers and symbols written as words so the TTS reads them right ("one to four working days",
  not "1-4"). No URLs, no markdown.
- Plain, contracted, no filler ("Great question!"). Don't repeat the caller's question back.
- Every in-scope answer ends with a short check, "Anything else about your transfer?"

## D15. A false escalation is better than a false answer (decided, 12 Nov 2026)

The rule that settles the remaining trade-offs. In `agent/policy.py`: unparseable model output
becomes UNCLEAR and is never spoken; after a handoff offer, anything but an in-scope question
connects the caller; the classifier may only escalate. A DONE label (caller says "no, that's
all") ends the call with a goodbye instead of an "unclear" reprompt.

- Faithfulness stays a known limitation for this version: the answer bank (README "What I'd do
  next") is the fix, deferred to close the project.
- Speech-to-text: Whisper large-v3-turbo (`deepdml/faster-whisper-large-v3-turbo-ct2`) on CUDA,
  downloaded 12 Nov 2026.
