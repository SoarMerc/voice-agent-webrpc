"""Scope check shared by the call and the eval: prompt loading, label parsing, the classifier guard."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL_RE = re.compile(r"\s*[`*]*([A-Za-z_]+)[`*]*[ \t]*(?::|\n)")


def system_prompt() -> str:
    template = (ROOT / "agent" / "system_prompt.md").read_text(encoding="utf-8")
    faq = (ROOT / "kb" / "wise-where-is-my-money.md").read_text(encoding="utf-8")
    return template.replace("{faq}", faq)


def split_label(text: str, final: bool = False):
    """Return (LABEL, rest) once the label line is complete, else (None, None).

    Mid-stream the label counts only after its newline or colon ("ANS" is not "ANSWER" yet).
    With final=True the whole reply has arrived, so a bare "OUT" counts too.
    """
    match = LABEL_RE.match(text + "\n" if final else text)
    if not match:
        return None, None
    return match.group(1).upper(), text[match.end():]


class ClassifierGuard:
    """Embedding classifier trained on eval/train.jsonl (D4, D12).

    It may only escalate: it can turn a turn into URGENT or UNCLEAR, never into an answer.
    """

    ESCALATIONS = {"urgent": "URGENT", "unclear": "UNCLEAR"}

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        from sklearn.linear_model import LogisticRegression

        rows = [json.loads(l) for l in (ROOT / "eval" / "train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        self.encoder = SentenceTransformer(model_name, device=device)
        x = self.encoder.encode([r["text"] for r in rows], normalize_embeddings=True)
        self.clf = LogisticRegression(max_iter=2000, C=4.0).fit(x, [r["class"] for r in rows])

    def escalation(self, user_text: str, previous_agent_text: str = ""):
        text = f"{previous_agent_text} || {user_text}" if previous_agent_text else user_text
        label = self.clf.predict(self.encoder.encode([text], normalize_embeddings=True))[0]
        return self.ESCALATIONS.get(label)
