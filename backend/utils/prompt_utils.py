"""Helpers for normalizing and naming case prompts."""


def normalize_prompt(text: str) -> str:
    """Normalize line endings while preserving multiline content."""
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def derive_case_name(prompt: str, max_len: int = 100) -> str:
    """Use the first non-empty line as the case title."""
    normalized = normalize_prompt(prompt)
    if not normalized:
        return "Cas generat"

    first_line = next(
        (line.strip() for line in normalized.split("\n") if line.strip()),
        normalized,
    )
    if len(first_line) <= max_len:
        return first_line
    return first_line[: max_len - 1].rstrip() + "…"


def prompt_stats(prompt: str) -> dict[str, int]:
    """Return character and non-empty line counts for a prompt."""
    normalized = normalize_prompt(prompt)
    lines = [line for line in normalized.split("\n") if line.strip()]
    return {
        "chars": len(normalized),
        "lines": len(lines) if lines else (1 if normalized else 0),
    }
