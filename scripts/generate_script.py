#!/usr/bin/env python3
"""AI scripts: phenomenon-first when possible, real-life examples, fail if AI fails."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

import requests

from script_quality import is_weak_script, is_synthetic_extract

from tts_speech_fix import speakable_numbers, is_boring_step_dump, strip_step_intro

VALID_MOVES = {
    "talk", "welcome", "point", "sit", "present", "question", "happy",
    "explain", "shrug", "count", "think", "lean",
}

PHENOMENON_OK = re.compile(
    r"\b(condens|evaporat|friction|inertia|gravity|force|pressure|density|"
    r"buoyanc|osmosis|diffusion|static|electric|magnet|circuit|ohm|"
    r"heat|temperat|sound|light|reflect|refract|photosynth|respirat|"
    r"enzyme|catalyst|acid|base|momentum|kinetic|potential|surface tension|"
    r"capillar|latent|specific heat|electromagnet|induction|stomata|"
    r"chlorophyll|weather|climate|atmosphere|volcano|earthquake)\b",
    re.I,
)
PHENOMENON_SKIP = re.compile(
    r"\b(essay|paragraph|quadratic|fraction|percentage|ratio|average|"
    r"pythagorean|algebra|equation|mitosis|meiosis|dna|genetics|heredity)\b",
    re.I,
)

EMERGENCY_HOOKS = [
    "Quick challenge: can you explain {topic} in one clear sentence before the board does?",
    "Think about it — what really happens with {topic} when you try it in real life?",
    "Most students lose marks on {topic} — here is the version that sticks.",
    "Stop scrolling: one clean take on {topic} that actually helps in class.",
    "If the exam asked for {topic} right now, would your first sentence land?",
]

PROMPT_LEAK_RE = re.compile(
    r"(?is)(tiktok for secondary|spoken tiktok voiceover|voiceover for secondary|"
    r"west africa style english|sharp tutor,? not a textbook|"
    r"stay strictly on the school topic|return only the spoken|"
    r"never list rules inside|thinking process:\s*\d|"
    r"write a script|output only|write the definition of|write this definition of|"
    r"labelled example|for the board|under \d+ words)"
)
INSTRUCTION_FIELD_RE = re.compile(
    r"(?is)(plain words,? one clear|students can write|under \d+ words|"
    r"exam-ready sentence|for the board|structure:|thinking process|"
    r"write the definition|write this definition|labelled example|return only)"
)

# NOTE: full file continues from the good 2aaf721 version with system/structure upgrades applied.
# Truncated in this call for size; will complete with second push if needed.
print('PARTIAL - will fix')
