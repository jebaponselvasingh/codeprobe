"""
Input sanitization and prompt injection mitigation for CodeProbe.

Two concerns:
1. User-supplied fields (student_name, project_id, problem_statement) — strip
   control characters, null bytes, and enforce length limits.
2. Code snippets embedded in LLM prompts — strip lines that look like
   prompt-injection directives and wrap content in structural delimiters so
   the model treats it as data to analyse, not instructions to follow.
"""
import re
import unicodedata

# ---------------------------------------------------------------------------
# Prompt-injection patterns to strip from code content
# These match lines that are clearly directive instructions, not code.
# ---------------------------------------------------------------------------
_INJECTION_LINE_RE = re.compile(
    r"(?im)^\s*(?:"
    r"IGNORE\b.*"
    r"|SYSTEM\s*:.*"
    r"|USER\s*:.*"
    r"|ASSISTANT\s*:.*"
    r"|<\s*/?(?:system|user|assistant|instruction|prompt)\s*>"
    r"|###\s+[A-Z][A-Z\s]{2,}"   # e.g. ### IGNORE PREVIOUS INSTRUCTIONS
    r")\s*$"
)

# Characters that should never appear in user-supplied text fields
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_input_field(value: str, max_len: int = 500) -> str:
    """
    Clean a user-supplied text field (student_name, project_id, problem_statement).

    - Removes null bytes and ASCII control characters (keeps \\t, \\n, \\r).
    - Normalises unicode to NFC to prevent homoglyph attacks.
    - Truncates to max_len characters.
    """
    if not isinstance(value, str):
        return ""
    # Normalise unicode
    value = unicodedata.normalize("NFC", value)
    # Strip control chars (keep tab/newline/CR which are legitimate in problem statements)
    value = _CONTROL_CHAR_RE.sub("", value)
    # Truncate
    return value[:max_len].strip()


def sanitize_code_for_prompt(code: str, max_len: int = 48_000) -> str:
    """
    Prepare a code snippet for safe inclusion in an LLM prompt.

    - Strips lines that match known prompt-injection directive patterns.
    - Wraps the result in <CODE_BLOCK> delimiters so the model treats the
      content as data to analyse, not instructions to execute.
    - Truncates to max_len characters to avoid token blowout.
    """
    if not isinstance(code, str):
        return "<CODE_BLOCK>\n</CODE_BLOCK>"

    # Remove injection lines
    lines = code.splitlines()
    cleaned_lines = [line for line in lines if not _INJECTION_LINE_RE.match(line)]
    cleaned = "\n".join(cleaned_lines)

    # Truncate before wrapping
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "\n... [truncated]"

    return f"<CODE_BLOCK>\n{cleaned}\n</CODE_BLOCK>"


def sanitize_prompt_dict(files: dict, max_files: int = 10, max_len_each: int = 6_000) -> dict:
    """
    Sanitize a dict of {filename: code_content} before embedding in a prompt.
    Returns a new dict with each value run through sanitize_code_for_prompt,
    limited to the first max_files entries.
    """
    result = {}
    for i, (path, content) in enumerate(files.items()):
        if i >= max_files:
            break
        result[path] = sanitize_code_for_prompt(content, max_len=max_len_each)
    return result
