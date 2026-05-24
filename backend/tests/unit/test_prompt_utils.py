from utils.prompt_utils import derive_case_name, normalize_prompt, prompt_stats


def test_normalize_prompt_preserves_multiline():
    raw = "Línia 1\r\nLínia 2\rLínia 3"
    assert normalize_prompt(raw) == "Línia 1\nLínia 2\nLínia 3"


def test_derive_case_name_uses_first_line():
    prompt = "Títol del cas\n\nContext detallat\nMés context"
    assert derive_case_name(prompt) == "Títol del cas"


def test_prompt_stats_counts_non_empty_lines():
    prompt = "Un\n\nDos\n  \nTres"
    assert prompt_stats(prompt) == {"chars": len("Un\n\nDos\n  \nTres"), "lines": 3}
