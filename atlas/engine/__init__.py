"""Atlas deterministic engine — the single source of truth for the law.

Every public function here is PURE and depends only on its arguments + the loaded
ruleset. No LLM, no network, no clock, no randomness in the judgment path.
"""
