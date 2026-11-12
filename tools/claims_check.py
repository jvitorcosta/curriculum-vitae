"""Claude Code PostToolUse hook: flag unbacked claims written into a resume or cover letter.

Reads the hook JSON on stdin. Exit 2 sends the findings back to Claude so it fixes the file;
exit 0 otherwise. See cv/claims.py for the rules.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cv.claims import find_claims, is_checked, load_banned  # noqa: E402 (needs ROOT on sys.path first)


def new_text(tool_input: dict) -> str:
    """The text this Edit, MultiEdit or Write added."""
    if "content" in tool_input:
        return tool_input["content"]
    if "edits" in tool_input:
        return "\n".join(edit.get("new_string", "") for edit in tool_input["edits"])
    return tool_input.get("new_string", "")


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    path = Path(tool_input.get("file_path", ""))
    try:
        rel = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return 0
    if not is_checked(rel):
        return 0
    found = find_claims(new_text(tool_input), load_banned(ROOT))
    if not found:
        return 0
    print(f"Claims check on {rel}: every claim must trace to main/.", file=sys.stderr)
    for item in found:
        print(f"- {item}", file=sys.stderr)
    print("Remove or reword these lines (a negation such as 'no vector DB' is fine).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
