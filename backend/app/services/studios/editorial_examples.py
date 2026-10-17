"""Versioned partial examples illustrate decisions, never complete production fixtures."""

EXAMPLES = {
    "footage": {
        "task": "Explain a visible detail in supplied footage",
        "family": "evidence",
        "targets": ["observed footage", "short annotation"],
        "avoid": "Using a filename as evidence that the detail is visible",
    },
    "motion": {
        "task": "Explain successive stages of a process",
        "family": "sequence",
        "targets": ["initial state", "changed state", "consequence"],
        "avoid": "Adding repeated shapes unrelated to the stated process",
    },
    "mixed": {
        "task": "Compare two observed outcomes",
        "family": "comparison",
        "targets": ["first outcome", "second outcome"],
        "avoid": "Substituting missing footage with decorative circles",
    },
    "revision": {
        "task": "Make selected scenes calmer and reduce complementary text",
        "family": "focus",
        "targets": ["essential evidence"],
        "avoid": "Changing narration, qualifications or unselected scenes",
    },
}


def select_examples(revision_instruction, request):
    selected = (
        ["revision", "mixed"]
        if revision_instruction
        else ["motion", "footage"]
        if request and request.mode == "motion"
        else ["mixed", "footage"]
    )
    return {"version": "res.editorial-examples.v1", "partialExamples": [EXAMPLES[key] for key in selected]}
