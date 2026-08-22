"""The one thing How Do says to a person before it is asked anything.

It explains a conversation that is about to happen and offers both ways out of
it. That is why it may be spoken unprompted where the discipline itself may
not: it is a notice *about* the skill, not the skill running.

The text lives here rather than in ``install.py`` because ``install.py`` is a
repository concern that never ships. The `SessionStart` hook runs from inside
the payload and needs the same words, and two copies of a text this careful
would drift on the first edit.

ASCII only. This reaches a terminal of unknown encoding, and a legacy codepage
would turn a first run into a UnicodeEncodeError.
"""

from __future__ import annotations


# States in which the note has something to say. Any other state means the
# question has already been answered -- settled, declined, or postponed -- and
# repeating it would be the nagging the discipline explicitly refuses.
UNSETTLED = frozenset({"missing", "onboarding_required"})


CONFIGURATION_NOTE = """
What happens next, and why:

  This skill works better once it knows how you, in particular, come to
  understand something. That cannot be read off your machine or your task,
  so the first conversation works it out with you. Four things:

    1. a subject you already know well, so you can judge for yourself
       whether an explanation of it was any good
    2. whether a concrete case lands better before the general rule, or
       after it
    3. what convinces you that you have actually got something: predicting
       the next result, reproducing the steps, watching it break, or
       saying it back in your own words
    4. how you want to be corrected when you are wrong

  It is meant to feel like a conversation rather than a form, it happens
  once, and you can correct any of it later.

  You can also say no. Say you are not interested and that is recorded;
  you will not be asked again. Say not now and the offer stays open while
  the work gets going. Everything else works either way; what you lose is
  the tailoring.
"""
