"""Text-only scope eval (no audio).

Runs caller lines through three scope checks (DECISIONS.md D4):
  llm      - the answer model writes the class label on its first line (agent/system_prompt.md)
  clf      - sentence embeddings + logistic regression, trained on eval/train.jsonl only
  combined - "two guards": the LLM label, overridden by the classifier when the classifier says
             urgent or unclear (the two classes the LLM misses), plus the older confidence cascade

Splits:
  --split test   eval/questions.jsonl, the held-out set. Run once per prompt version, not to tune.
  --split train  eval/train.jsonl, the dev set for tuning the prompt. LLM only (the classifier is
                 trained on it, so its score there means nothing).

Usage:
  python eval/run_scope.py [--split test|train] [--model qwen3.5:4b] [--embed BAAI/bge-base-en-v1.5]

Writes eval/results/<split>-<model>-<timestamp>.json and prints a summary.
"""

import argparse
import json
import re
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import ollama
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["in", "in_handoff", "out", "urgent", "unclear", "done"]
ANSWERS = {"in", "in_handoff"}    # classes where the agent speaks FAQ content
HANDOFFS = {"out", "urgent"}      # classes where it only plays a fixed line
GUARD_CLASSES = {"urgent", "unclear"}


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def system_prompt():
    template = (ROOT / "agent" / "system_prompt.md").read_text(encoding="utf-8")
    faq = (ROOT / "kb" / "wise-where-is-my-money.md").read_text(encoding="utf-8")
    return template.replace("{faq}", faq)


# Prompt labels (distinct words a small model won't blur) -> eval classes.
PROMPT_LABELS = {"answer": "in", "partial": "in_handoff", "out": "out", "urgent": "urgent", "unclear": "unclear", "done": "done"}


def parse_label(reply):
    """The label is the first word of the reply; it may be followed by a newline or by ': text'."""
    match = re.match(r"\s*[`*]*([a-z_]+)", reply.lower())
    word = match.group(1) if match else ""
    return PROMPT_LABELS.get(word, f"invalid:{reply.strip()[:20]}")


def run_llm(client, model, prompt, item):
    messages = [{"role": "system", "content": prompt}]
    for turn in item.get("context", []):
        messages.append({"role": "user" if turn["role"] == "user" else "assistant", "content": turn["text"]})
    messages.append({"role": "user", "content": item["text"]})

    start = time.perf_counter()
    first_token = label_at = None
    reply = ""
    # Native Ollama API with think=False. Through the OpenAI-compatible endpoint with
    # reasoning_effort "none" the first content token took ~2.6 s; natively ~0.6 s.
    stream = client.chat(
        model=model,
        messages=messages,
        stream=True,
        think=False if "qwen" in model else None,
        options={"temperature": 0, "num_predict": 200},
    )
    for chunk in stream:
        delta = chunk.message.content or ""
        if not delta:
            continue
        if first_token is None:
            first_token = time.perf_counter() - start
        reply += delta
        if label_at is None and re.search(r"[\n:]", reply):
            label_at = time.perf_counter() - start
    total = time.perf_counter() - start
    return {
        "label": parse_label(reply),
        "reply": reply,
        "first_token_s": round(first_token or total, 3),
        "label_s": round(label_at or total, 3),
        "total_s": round(total, 3),
    }


def clf_text(item):
    """What the classifier sees: the previous agent line (if any) plus the caller's words."""
    context = item.get("context", [])
    previous = next((t["text"] for t in reversed(context) if t["role"] == "agent"), "")
    return f"{previous} || {item['text']}" if previous else item["text"]


def metrics(gold, pred):
    pairs = list(zip(gold, pred))
    return {
        "accuracy": round(sum(g == p for g, p in pairs) / len(pairs), 3),
        # answered (spoke FAQ content) when it should have handed off: the costly error
        "false_answer": sum(g in HANDOFFS and p in ANSWERS for g, p in pairs),
        # handed off when it could have answered
        "false_handoff": sum(g in ANSWERS and p in HANDOFFS for g, p in pairs),
        # urgent treated as an ordinary out-of-scope (soft handoff instead of immediate)
        "urgent_softened": sum(g == "urgent" and p == "out" for g, p in pairs),
        # needs-account / mixed answered without the handoff
        "handoff_dropped": sum(g == "in_handoff" and p == "in" for g, p in pairs),
        "invalid_label": sum(p.startswith("invalid") for p in pred),
        "n": len(pairs),
    }


def confusion(gold, pred):
    labels = CLASSES + (["invalid"] if any(p.startswith("invalid") for p in pred) else [])
    counts = Counter((g, "invalid" if p.startswith("invalid") else p) for g, p in zip(gold, pred))
    lines = ["gold \\ pred".ljust(12) + "".join(l.rjust(11) for l in labels)]
    for g in CLASSES:
        lines.append(g.ljust(12) + "".join(str(counts[(g, p)]).rjust(11) for p in labels))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "train"], default="test")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--embed", default="BAAI/bge-base-en-v1.5")
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()

    train = load_jsonl(ROOT / "eval" / "train.jsonl")
    items = load_jsonl(ROOT / "eval" / "questions.jsonl") if args.split == "test" else train
    for i, item in enumerate(items):
        item.setdefault("id", f"t{i + 1:02d}")
    gold = [q["class"] for q in items]

    clf_pred = clf_conf = None
    clf_ms = None
    if args.split == "test":
        encoder = SentenceTransformer(args.embed)
        x_train = encoder.encode([t["text"] for t in train], normalize_embeddings=True)
        clf = LogisticRegression(max_iter=2000, C=4.0).fit(x_train, [t["class"] for t in train])
        t0 = time.perf_counter()
        x_eval = encoder.encode([clf_text(q) for q in items], normalize_embeddings=True)
        clf_ms = round((time.perf_counter() - t0) / len(items) * 1000, 1)
        proba = clf.predict_proba(x_eval)
        clf_pred = [clf.classes_[i] for i in proba.argmax(axis=1)]
        clf_conf = proba.max(axis=1)

    client = ollama.Client(host=args.host)
    prompt = system_prompt()
    run_llm(client, args.model, prompt, {"text": "hello"})  # warm up: load model, cache the prompt
    llm_runs = []
    for i, q in enumerate(items):
        r = run_llm(client, args.model, prompt, q)
        llm_runs.append(r)
        mark = "ok " if r["label"] == q["class"] else "XX "
        clf_note = f" clf={clf_pred[i]}" if clf_pred else ""
        print(f"{mark}{q['id']} gold={q['class']:<10} llm={r['label']:<10}{clf_note}  {r['label_s']:.2f}s  | {q['text'][:50]}")
    llm_pred = [r["label"] for r in llm_runs]

    results = {"llm": metrics(gold, llm_pred)}
    if clf_pred:
        results["clf"] = metrics(gold, clf_pred)
        guarded = [c if c in GUARD_CLASSES else l for c, l in zip(clf_pred, llm_pred)]
        results["guard"] = metrics(gold, guarded)
        for threshold in (0.5, 0.7):
            cascade = [c if conf >= threshold else l for c, conf, l in zip(clf_pred, clf_conf, llm_pred)]
            results[f"cascade@{threshold}"] = metrics(gold, cascade)

    label_times = [r["label_s"] for r in llm_runs]
    timing = {
        "llm_label_median_s": round(statistics.median(label_times), 3),
        "llm_label_p90_s": round(float(np.percentile(label_times, 90)), 3),
        "llm_first_token_median_s": round(statistics.median(r["first_token_s"] for r in llm_runs), 3),
        "clf_ms_per_item": clf_ms,
    }

    print("\n== scope metrics ==")
    for name, m in results.items():
        print(f"{name:<14} {m}")
    print("\n== timing ==", timing)
    print("\n== llm confusion ==\n" + confusion(gold, llm_pred))
    if clf_pred:
        print("\n== guard confusion ==\n" + confusion(gold, guarded))

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = out_dir / f"{args.split}-{args.model.replace(':', '_').replace('/', '_')}-{stamp}.json"
    out.write_text(json.dumps({
        "split": args.split, "model": args.model, "embed": args.embed if clf_pred else None,
        "metrics": results, "timing": timing,
        "items": [
            {**q, "llm": r, **({"clf": clf_pred[i], "clf_conf": round(float(clf_conf[i]), 3)} if clf_pred else {})}
            for i, (q, r) in enumerate(zip(items, llm_runs))
        ],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
