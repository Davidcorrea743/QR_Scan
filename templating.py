import html
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_ESCAPED_RE = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
_RAW_RE = re.compile(r"\{!\s*([A-Z0-9_]+)\s*!}")


def render(template_name: str, **context) -> str:
    with open(os.path.join(TEMPLATES_DIR, template_name), encoding="utf-8") as f:
        s = f.read()

    def esc(match):
        key = match.group(1)
        return html.escape(str(context.get(key, "")), quote=True)

    def raw(match):
        key = match.group(1)
        return str(context.get(key, ""))

    s = _ESCAPED_RE.sub(esc, s)
    s = _RAW_RE.sub(raw, s)
    return s
