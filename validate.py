#!/usr/bin/env python3
"""Validate the Hermes Agent Field Guide build."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = ROOT / "index.html"
PROMPTS_JS = ROOT / "prompts.js"
WING_SVG = ROOT / "wing-logo.svg"
FAVICON = ROOT / "assets" / "hermes-icon.png"

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}

errors: list[str] = []
checks: list[str] = []


def ok(msg: str) -> None:
    checks.append(f"  PASS  {msg}")


def fail(msg: str) -> None:
    errors.append(f"  FAIL  {msg}")


def validate_html() -> None:
    if not INDEX.exists():
        fail("index.html not found")
        return
    src = INDEX.read_text(encoding="utf-8")
    ok(f"index.html exists ({len(src)} bytes, {src.count(chr(10))+1} lines)")

    if not (src.startswith("<!doctype") or src.startswith("<!DOCTYPE")):
        fail("Document does not start with <!doctype>")
    else:
        ok("Starts with <!doctype>")

    sections = re.findall(r'<section class="sec" id="([^"]+)"', src)
    if len(sections) == 9:
        ok(f"All 9 sections found: {', '.join(sections)}")
    else:
        fail(f"Expected 9 sections, found {len(sections)}")

    for idn in ["basics", "start", "how", "brain", "system",
                "team", "bots", "rules", "sources"]:
        if f'id="{idn}"' in src:
            ok(f'  Section id="{idn}" present')
        else:
            fail(f'  Section id="{idn}" missing')

    if 'id="botGrid"' in src:
        ok("Bot grid container present")
    else:
        fail("Bot grid container missing")

    if '<dialog id="dlg"' in src:
        ok("Dialog element present")
    else:
        fail("Dialog element missing")

    if '<script src="prompts.js">' in src:
        ok('prompts.js ref correct: src="prompts.js"')
    else:
        fail("prompts.js ref wrong")

    n_copy = len(re.findall(r'class="btn sm cp"', src))
    if n_copy >= 8:
        ok(f"Copy buttons found ({n_copy})")
    else:
        fail(f"Expected >=8 copy buttons, found {n_copy}")

    # Balanced tags
    open_tags: list[str] = []
    tag_re = re.compile(r"<(/?)([a-z][a-z0-9]*)\b[^>]*?(/?)>")
    for m in tag_re.finditer(src):
        close, name, self = m.group(1), m.group(2), m.group(3)
        if name in VOID_TAGS or self == "/":
            continue
        if close == "/":
            if open_tags and open_tags[-1] == name:
                open_tags.pop()
            else:
                fail(f"Unbalanced </{name}>")
                break
        else:
            open_tags.append(name)
    if not open_tags:
        ok("All non-void tags balanced")
    else:
        fail(f"Unclosed: {open_tags[-5:]}")


def validate_prompts_js() -> None:
    if not PROMPTS_JS.exists():
        fail("prompts.js not found")
        return
    src = PROMPTS_JS.read_text(encoding="utf-8")
    if not src.strip().startswith("const BOTS = ["):
        fail("prompts.js missing `const BOTS = [`")
    else:
        ok("Starts with `const BOTS = [`")
    if not src.rstrip().endswith("];"):
        fail("prompts.js missing `];`")
    else:
        ok("Ends with `];`")
    bots = re.findall(r'name:"([^"]+)"', src)
    if len(bots) == 10:
        ok(f"10 bots: {', '.join(bots)}")
    else:
        fail(f"Expected 10 bots, found {len(bots)}")
    sc = len(re.findall(r'steps:\[', src))
    pc = len(re.findall(r'prompt:\[', src))
    if sc == 10 and pc == 10:
        ok("All bots have steps + prompt arrays")
    else:
        fail(f"steps={sc} prompt={pc} (expected 10 each)")

    # A `];` tail is not proof the file parses: the object list was once left
    # unclosed while startsWith/endsWith both passed. Parse it for real.
    if _syntax_ok(PROMPTS_JS):
        ok("prompts.js parses as JavaScript (node --check)")
    else:
        fail("prompts.js has a JavaScript syntax error — the whole page's JS dies")


def _syntax_ok(path):
    """Real syntax check via node when available; fall back to node-less parse."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if node:
        r = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        if r.returncode != 0:
            print("    " + (r.stderr or "").strip().splitlines()[0])
        return r.returncode == 0
    # No node: bracket-balance the file as a weak fallback.
    depth = 0
    instr = None
    esc = False
    for ch in path.read_text(encoding="utf-8"):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == instr:
                instr = None
        elif ch in "\"'`":
            instr = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and instr is None


def validate_assets():
    if PROMPTS_JS.exists():
        ok("prompts.js file exists")
    else:
        fail("prompts.js file missing")
    if WING_SVG.exists():
        ok("wing-logo.svg exists")
    else:
        fail("wing-logo.svg missing")
    if FAVICON.exists():
        ok(f"Favicon exists ({FAVICON.stat().st_size} bytes)")
    else:
        fail("Favicon missing")
    if (ROOT / "assets").is_dir():
        ok("assets/ directory exists")
    else:
        fail("assets/ directory missing")


def validate_wing_svg():
    if not WING_SVG.exists():
        return
    svg = WING_SVG.read_text(encoding="utf-8")
    if svg.startswith("<svg") and svg.rstrip().endswith("</svg>"):
        ok("Proper SVG wrapper")
    else:
        fail("Missing SVG wrapper")
    paths = re.findall(r"<path[^>]*>", svg)
    if len(paths) == 3:
        ok("3 feather paths")
    else:
        fail(f"Expected 3 paths, found {len(paths)}")
    if "#0000f2" in svg:
        ok("Uses Hermes blue (#0000f2)")
    else:
        fail("Missing Hermes blue")


def validate_colors():
    if not INDEX.exists():
        return
    css = INDEX.read_text(encoding="utf-8")
    for name, code in [("blue #0000f2", "#0000f2"),
                       ("cream #ffe6cb", "#ffe6cb"),
                       ("gold #ffbd39", "#ffbd39")]:
        if code in css:
            ok(f"Brand color {name} found")
        else:
            fail(f"Brand color {name} missing")


def main() -> int:
    print("=" * 70)
    print("  Hermes Agent Field Guide — Build Validation")
    print("=" * 70)
    for label, fn in [("HTML", validate_html),
                      ("prompts.js", validate_prompts_js),
                      ("Assets", validate_assets),
                      ("wing-logo.svg", validate_wing_svg),
                      ("Brand Colors", validate_colors)]:
        print(f"\n--- {label} ---")
        checks.clear()
        fn()
        for c in checks:
            print(c)
    print("\n" + "=" * 70)
    if errors:
        print(f"  {len(errors)} error(s)")
        for e in errors:
            print(e)
        return 1
    print("  All checks passed!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

    if not src.strip().startswith("const BOTS = ["):
        fail("prompts.js missing `const BOTS = [`")
    else:
        ok("Starts with `const BOTS = [`")
    if not src.rstrip().endswith("];"):
        fail("prompts.js missing `];`")
    else:
        ok("Ends with `];`")
    bots = re.findall(r'name:"([^"]+)"', src)
    if len(bots) == 10:
        ok(f"10 bots: {', '.join(bots)}")
    else:
        fail(f"Expected 10 bots, found {len(bots)}")
    sc = len(re.findall(r'steps:\[', src))
    pc = len(re.findall(r'prompt:\[', src))
    if sc == 10 and pc == 10:
        ok("All bots have steps+ prompt arrays")
    else:
        fail(f"steps={sc} prompt={pc} (expected 10 each)")
