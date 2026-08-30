"""Cycle-free shared limits for specialist selection and replay."""

# Direct prompt capsules remain intentionally small. Isolated workforce plans
# carry only immutable references in the parent and may bind one specialist per
# verified work unit, up to the same system-wide work-unit budget.
MAX_SELECTED_SPECIALISTS = 4
MAX_DURABLE_SPECIALIST_REFERENCES = 16
MAX_SPECIALIST_PROMPT_CHARS = 7_000

__all__ = [
    "MAX_DURABLE_SPECIALIST_REFERENCES",
    "MAX_SELECTED_SPECIALISTS",
    "MAX_SPECIALIST_PROMPT_CHARS",
]
