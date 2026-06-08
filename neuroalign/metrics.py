"""
Readability Metrics
===================
Quantitative before/after measurement of text transformation.
Used to generate empirical results for the thesis methodology chapter.

Library: textstat (pip install textstat)
Theoretical basis:
  - Flesch Reading Ease (Flesch, 1948): higher = easier (0-100 scale)
  - Flesch-Kincaid Grade Level: US school grade equivalent
  - Gunning Fog Index (Gunning, 1952): years of education needed to understand
  - SMOG Index: validated for health and academic materials

These metrics operationalize Sweller's (1988) extraneous cognitive load
as a measurable, quantitative construct — bridging AI engineering and
cognitive psychology in the thesis methodology chapter.
"""

from dataclasses import dataclass
import textstat


@dataclass
class ReadabilityReport:
    flesch_reading_ease:    float  # 0–100, higher = easier
    flesch_kincaid_grade:   float  # US grade level
    gunning_fog:            float  # years of education required
    smog_index:             float  # validated for academic texts
    avg_sentence_length:    float  # words per sentence
    avg_word_length:        float  # characters per word
    word_count:             int
    sentence_count:         int


def measure(text: str) -> ReadabilityReport:
    """Compute all readability metrics for a text string."""
    return ReadabilityReport(
        flesch_reading_ease  = round(textstat.flesch_reading_ease(text),    2),
        flesch_kincaid_grade = round(textstat.flesch_kincaid_grade(text),   2),
        gunning_fog          = round(textstat.gunning_fog(text),            2),
        smog_index           = round(textstat.smog_index(text),             2),
        avg_sentence_length  = round(textstat.avg_sentence_length(text),    2),
        avg_word_length      = round(textstat.avg_syllables_per_word(text), 2),
        word_count           = textstat.lexicon_count(text),
        sentence_count       = textstat.sentence_count(text),
    )


def compare(before: ReadabilityReport, after: ReadabilityReport) -> dict:
    """
    Compute delta between pre- and post-transformation.
    Returns a dict ready for st.metric() display and CSV export.
    """
    def delta_pct(a, b):
        if a == 0:
            return 0.0
        return round(((b - a) / abs(a)) * 100, 1)

    return {
        "flesch_ease_before":   before.flesch_reading_ease,
        "flesch_ease_after":    after.flesch_reading_ease,
        "flesch_ease_delta":    round(after.flesch_reading_ease - before.flesch_reading_ease, 2),
        "flesch_ease_delta_pct": delta_pct(before.flesch_reading_ease, after.flesch_reading_ease),

        "grade_level_before":   before.flesch_kincaid_grade,
        "grade_level_after":    after.flesch_kincaid_grade,
        "grade_level_delta":    round(after.flesch_kincaid_grade - before.flesch_kincaid_grade, 2),

        "fog_before":           before.gunning_fog,
        "fog_after":            after.gunning_fog,
        "fog_delta":            round(after.gunning_fog - before.gunning_fog, 2),

        "sentence_len_before":  before.avg_sentence_length,
        "sentence_len_after":   after.avg_sentence_length,
        "sentence_len_delta":   round(after.avg_sentence_length - before.avg_sentence_length, 2),

        "word_count_before":    before.word_count,
        "word_count_after":     after.word_count,
        "word_count_delta":     after.word_count - before.word_count,

        "profile":              "",   # filled in by caller
        "intensity":            "",   # filled in by caller
    }


def flesch_label(score: float) -> str:
    """Human-readable label for Flesch Reading Ease score."""
    if score >= 90: return "Very easy (5th grade)"
    if score >= 80: return "Easy (6th grade)"
    if score >= 70: return "Fairly easy (7th grade)"
    if score >= 60: return "Standard (8th–9th grade)"
    if score >= 50: return "Fairly difficult (10th–12th grade)"
    if score >= 30: return "Difficult (university level)"
    return "Very difficult (professional / academic)"
