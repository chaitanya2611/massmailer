import re

VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_ \-]+?)\s*\}\}")


def extract_variables(*texts):
    """Return the ordered, de-duplicated list of {{variable}} names used across the given strings."""
    seen = []
    for text in texts:
        for match in VARIABLE_PATTERN.findall(text or ""):
            if match not in seen:
                seen.append(match)
    return seen


def render_merge(text, row):
    """Substitute {{variable}} tokens in `text` using values from dict `row`. Missing keys are left as "" ."""

    def _replace(match):
        key = match.group(1)
        return str(row.get(key, ""))

    return VARIABLE_PATTERN.sub(_replace, text or "")


def missing_variables(text, row):
    """Which {{variables}} referenced in `text` are absent or blank in `row`."""
    missing = []
    for var in extract_variables(text):
        value = row.get(var)
        if value is None or str(value).strip() == "":
            missing.append(var)
    return missing
