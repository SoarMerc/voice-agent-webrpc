"""Call policy: what the agent does with each scope label (SPEC.md "Handoff behaviour", D9).

Pure Python, no audio, so it can be read and tested on its own. Every handoff and reprompt is a
fixed line; only ANSWER and PARTIAL speak generated text. Principle: a false escalation is better
than a false answer, so anything unexpected falls towards a handoff, never towards an answer.
"""

from dataclasses import dataclass

GREETING = (
    "Hi, you're through to Wise. I can help with where your money is: arrival times, delays, "
    "and what your transfer's status means. What's your question?"
)
ANSWER_CHECK = "Anything else about your transfer?"
PARTIAL_HANDOFF = (
    "For anything about your own transfer, a colleague can help. "
    "Anything else about where your money is before I connect you?"
)
SOFT_HANDOFF = (
    "That's not something I can help with here, but a colleague can. "
    "Anything else about where your money is before I connect you?"
)
URGENT_HANDOFF = "I'll connect you to a colleague right away. Please stay on the line."
CONNECT = "Connecting you to a colleague now. Thanks for calling Wise."
GOODBYE = "Thanks for calling Wise. Goodbye."
REPEAT = "Sorry, could you say that again?"
MENU = (
    "I can help with things like when your money will arrive, why a transfer is taking longer, "
    "or what a proof of payment is. What would you like to know?"
)

LABELS = {"ANSWER", "PARTIAL", "OUT", "URGENT", "UNCLEAR", "DONE"}


@dataclass
class Action:
    speak_answer: bool          # stream the model's own reply
    say: str = ""               # fixed line, spoken after the answer (if any)
    end_call: bool = False


class CallPolicy:
    def __init__(self):
        self.unclear_strikes = 0
        self.handoff_pending = False   # we've offered a colleague; one more in-scope question allowed
        self.asked_anything_else = False

    def decide(self, label: str) -> Action:
        if label not in LABELS:
            label = "UNCLEAR"          # unparseable model output never gets spoken
        if label == "DONE" and not self.asked_anything_else:
            # A goodbye only counts as an answer to "anything else?". Before that it's usually a
            # mis-hearing (Whisper writes "Thank you." on near-silence), so ask them to repeat.
            label = "UNCLEAR"
        action = self._decide(label)
        if action.say in (ANSWER_CHECK, PARTIAL_HANDOFF, SOFT_HANDOFF, MENU):
            self.asked_anything_else = True
        return action

    def _decide(self, label: str) -> Action:
        if label == "URGENT":
            return Action(False, URGENT_HANDOFF, end_call=True)

        if label == "DONE":
            if self.handoff_pending:
                return Action(False, CONNECT, end_call=True)
            return Action(False, GOODBYE, end_call=True)

        if label == "ANSWER":
            self.unclear_strikes = 0
            # After a handoff offer the caller may still ask one more in-scope question.
            return Action(True, ANSWER_CHECK)

        if label == "PARTIAL":
            self.unclear_strikes = 0
            self.handoff_pending = True
            return Action(True, PARTIAL_HANDOFF)

        if label == "OUT":
            if self.handoff_pending:
                return Action(False, CONNECT, end_call=True)
            self.handoff_pending = True
            return Action(False, SOFT_HANDOFF)

        # UNCLEAR
        if self.handoff_pending:
            # e.g. "no" or "nope" after "anything else before I connect you?"
            return Action(False, CONNECT, end_call=True)
        self.unclear_strikes += 1
        if self.unclear_strikes == 1:
            return Action(False, REPEAT)
        if self.unclear_strikes == 2:
            return Action(False, MENU)
        return Action(False, CONNECT, end_call=True)
