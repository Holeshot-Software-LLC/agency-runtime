"""Which output-length parameter a model's API expects.

The OpenAI-compatible chat API renamed the bound on generated length: newer
models take ``max_completion_tokens`` and reject ``temperature``, older ones
take ``max_tokens``. Two call sites decided that independently, each with its
own copy of ``model.startswith("gpt-5")``, and both copies disagreed with the
model name this package ships: ``config_defaults.yaml`` writes ``gpt5.6-luna``
with no hyphen after ``gpt``, so the test answered False for exactly the family
it exists to detect, while an operator config naming the same family
``gpt-5.6-terra`` answered True. One family, two spellings, two different
request bodies -- and the test covering the branch used a third spelling,
``gpt-5.6``, that nothing ships, so nothing was red.

Deciding it here once, from the provider entry rather than from a substring of
a name, gives a renamed or newly released model somewhere to be declared:
``token_parameter`` on the provider settles it outright, and the fallback folds
separators away so the families already known answer the same however they are
punctuated. A model this package has never heard of is the case the declaration
exists for -- guessing forward from a name is what produced the defect above.
"""

from __future__ import annotations

TOKEN_PARAMETER_AUTO = ""
TOKEN_PARAMETER_MAX_TOKENS = "max_tokens"
TOKEN_PARAMETER_MAX_COMPLETION_TOKENS = "max_completion_tokens"

#: Every value ``ProviderEntry.token_parameter`` accepts.
TOKEN_PARAMETERS = (
    TOKEN_PARAMETER_AUTO,
    TOKEN_PARAMETER_MAX_TOKENS,
    TOKEN_PARAMETER_MAX_COMPLETION_TOKENS,
)

# Compared after folding, so "gpt-5.6-terra", "gpt5.6-luna" and "GPT_5" all
# reduce to the same prefix. Extend only for a family whose API is known to
# require the newer parameter; anything unverified belongs in an operator's
# explicit `token_parameter` instead of a guess made here.
_COMPLETION_TOKEN_FAMILIES = ("gpt5",)


def folded_model_name(model: str) -> str:
    """Drop case and separators so one family compares equal to itself."""

    return "".join(character for character in model.casefold() if character.isalnum())


def requires_completion_token_parameter(model: str, *, declared: str = "") -> bool:
    """Whether this model wants ``max_completion_tokens`` over ``max_tokens``.

    ``declared`` is the operator's explicit answer and always wins, which is
    what makes a model change a configuration edit rather than a code change.
    """

    declaration = declared.strip().casefold()
    if declaration == TOKEN_PARAMETER_MAX_COMPLETION_TOKENS:
        return True
    if declaration == TOKEN_PARAMETER_MAX_TOKENS:
        return False
    return folded_model_name(model).startswith(_COMPLETION_TOKEN_FAMILIES)


__all__ = [
    "TOKEN_PARAMETERS",
    "TOKEN_PARAMETER_AUTO",
    "TOKEN_PARAMETER_MAX_COMPLETION_TOKENS",
    "TOKEN_PARAMETER_MAX_TOKENS",
    "folded_model_name",
    "requires_completion_token_parameter",
]
