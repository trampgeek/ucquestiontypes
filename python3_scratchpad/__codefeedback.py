"""
Prompt-building helpers for AI feedback on a student's code, given also the
reference answer (author's solution).

This module no longer talks to any LLM itself - it only builds the prompt
text. The actual network call happens later, from the student's browser via
Moodle's local_aigateway web service (core_ai), triggered only if and when
the student clicks "Show AI feedback" and has given consent. Keeping the
prompt text and its {{CHOSEN_AFFIRMATION}}/{{EXTRA_GUIDANCE}} substitution
here (rather than in Moodle/PHP) keeps the actual tutoring wording easy to
iterate on and version-controlled alongside the rest of this question type.
"""

import hashlib

# Affirmation phrases offered to the AI feedback system prompt via
# {{CHOSEN_AFFIRMATION}}.
DEFAULT_AFFIRMATIONS = [
    "Nice work!", "Ka pai!", "Well done!", "Great job!", "Good stuff",
    "Nicely done!", "Solid work!", "You've got it!", "Looking good!", "Nice!",
]


def _default_affirmation(student_code):
    """Deterministically pick a phrase from DEFAULT_AFFIRMATIONS based on
       a hash of the student's code. Used as a fallback when build_combined_prompt
       is called without an explicit affirmation (e.g. standalone/test usage) — the
       normal CodeRunner template.py path always supplies one explicitly.
    """
    digest = hashlib.sha256(student_code.encode('utf-8')).hexdigest()
    index = int(digest, 16) % len(DEFAULT_AFFIRMATIONS)
    return DEFAULT_AFFIRMATIONS[index]


SYSTEM_PROMPT = open("__ai_feedback_system_prompt.txt").read()


# ======================================
#  Prompt building
# ======================================

def build_system_prompt(affirmation, extra_prompt=''):
    """Substitute {{CHOSEN_AFFIRMATION}} and {{EXTRA_GUIDANCE}} into SYSTEM_PROMPT
       and return the result.
    """
    prompt = SYSTEM_PROMPT.replace("{{CHOSEN_AFFIRMATION}}", affirmation)
    return prompt.replace("{{EXTRA_GUIDANCE}}", extra_prompt)


def build_combined_prompt(student_code, authors_code, affirmation=None, extra_prompt=''):
    """Build the single combined prompt text (system instructions plus the
       student's and author's code) to hand to an LLM chat-completion call.
       Used by template.py, which hands this string as-is to Moodle's
       local_aigateway web service - core_ai's generate_text action takes one
       prompttext, not separate system/user messages.
    """
    if affirmation is None:
        affirmation = _default_affirmation(student_code)
    system_prompt = build_system_prompt(affirmation, extra_prompt)
    return f"{system_prompt}\n\nStudent's Code: {student_code}\n\nAuthor's Answer: {authors_code}"
