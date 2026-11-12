"""Call policy (agent/policy.py): one test per rule in SPEC.md "Handoff behaviour"."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.policy import (  # noqa: E402
    CONNECT, GOODBYE, MENU, PARTIAL_HANDOFF, REPEAT, SOFT_HANDOFF, URGENT_HANDOFF, CallPolicy,
)
from agent.scope import split_label  # noqa: E402


def test_answer_speaks_and_continues():
    a = CallPolicy().decide("ANSWER")
    assert a.speak_answer and not a.end_call


def test_out_gets_one_more_chance_then_connects():
    p = CallPolicy()
    first = p.decide("OUT")
    assert (first.say, first.end_call, first.speak_answer) == (SOFT_HANDOFF, False, False)
    assert p.decide("OUT").end_call


def test_in_scope_question_after_handoff_offer_is_answered():
    p = CallPolicy()
    p.decide("OUT")
    a = p.decide("ANSWER")
    assert a.speak_answer and not a.end_call


def test_no_after_handoff_offer_connects():
    for label in ("UNCLEAR", "DONE"):
        q = CallPolicy()
        q.decide("PARTIAL")
        a = q.decide(label)
        assert (a.say, a.end_call) == (CONNECT, True)


def test_partial_answers_then_offers_colleague():
    a = CallPolicy().decide("PARTIAL")
    assert a.speak_answer and a.say == PARTIAL_HANDOFF and not a.end_call


def test_urgent_ends_immediately():
    a = CallPolicy().decide("URGENT")
    assert (a.say, a.end_call, a.speak_answer) == (URGENT_HANDOFF, True, False)


def test_unclear_three_strikes():
    p = CallPolicy()
    assert p.decide("UNCLEAR").say == REPEAT
    assert p.decide("UNCLEAR").say == MENU
    assert p.decide("UNCLEAR").end_call


def test_answer_resets_unclear_strikes():
    p = CallPolicy()
    p.decide("UNCLEAR")
    p.decide("ANSWER")
    assert p.decide("UNCLEAR").say == REPEAT


def test_done_says_goodbye():
    a = CallPolicy().decide("DONE")
    assert (a.say, a.end_call) == (GOODBYE, True)


def test_unknown_label_is_never_spoken():
    a = CallPolicy().decide("BANANA")
    assert not a.speak_answer and a.say == REPEAT


def test_split_label():
    assert split_label("ANSWER\nYou can") == ("ANSWER", "You can")
    assert split_label("partial: First") == ("PARTIAL", " First")
    assert split_label("ANS") == (None, None)            # mid-stream: label not finished yet
    assert split_label("OUT", final=True) == ("OUT", "")  # whole reply was just the label
