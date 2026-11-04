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

## D3. No retrieval (RAG); the whole FAQ goes in the prompt (proposed)

- Why: six short articles, about 1,500 words. That fits easily in a small model's context.
  Retrieval would add a failure mode (wrong chunk) and latency, with nothing gained at this size.
- Would change if: the knowledge base grew past what fits comfortably (hundreds of articles), or
  answers needed per-article citations; then hybrid retrieval with a reranker.

## D4. Scope check as an explicit step, not only a prompt instruction (proposed)

Every caller turn is classified (in scope / needs account / out of scope / unclear) before any
answer is generated; out-of-scope turns get a fixed deflection line, never generated text.

- Why: the costly error is answering something it shouldn't (invented fees, a promise about a
  specific transfer). A separate, testable decision makes that error measurable and keeps the
  deflection wording fixed. It mirrors how Sei routes low-confidence items to a human.
- Open: one LLM call that returns `{class, answer}` as structured output, or two calls (classify,
  then answer). Pick by measured accuracy and latency.

## D5. Pipecat as the framework (proposed)

- Why: open source, Python, handles the hard real-time parts (voice activity detection, barge-in,
  streaming between stages), supports browser calls and a Twilio transport, and has local
  faster-whisper and Ollama integrations.
- Alternative: LiveKit Agents (heavier setup: server plus SIP trunk for phones).

## D6. Models (proposed, to be measured)

- Speech-to-text: faster-whisper `small` or `distil-large-v3` (not `large-v3`: phone-quality audio
  and latency matter more than the last bit of accuracy). Already in the `langchain` conda env.
- LLM: `qwen3.5:4b` or `gemma3:4b` via Ollama, both already pulled. Pick the one with fewer false
  answers on the eval set.
- Text-to-speech: Kokoro-82M ONNX, voice `af_heart`, on CPU so it doesn't compete for GPU memory.
  Already used by Shivansh's clipboard reader (`F:\Voice\tts`).

## D7. Repo location (decided, 4 Nov 2026)

`F:\Products\sei-voice-agent`, its own git repo. Not `F:\TomatoSoup` (that is the published
hint-ladder-eval project) and not the CV repo.

## Open

- Python environment: install Pipecat into the existing `langchain` env, or a new conda env for
  this project. Waiting on Shivansh.
