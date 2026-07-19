"""Cycle-free shared limits for specialist selection and replay."""

# Selector routing is capped independently, while an isolated unit plan can
# add the protected fallback coordinator to the selected specialist set. Keep
# the replay boundary large enough for three routed specialists plus that one
# coordinator, and no larger.
MAX_SELECTED_SPECIALISTS = 4
MAX_SPECIALIST_PROMPT_CHARS = 7_000

__all__ = ["MAX_SELECTED_SPECIALISTS", "MAX_SPECIALIST_PROMPT_CHARS"]
