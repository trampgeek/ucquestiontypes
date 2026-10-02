# build.py
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).parent / "classes"))
from item_types import ITEM_TYPES  # noqa: E402 - needs the sys.path tweak above


def item_emoji_js():
    """Render ITEM_TYPES as a JS object literal, e.g. { star:'⭐', key:'🔑' }."""
    entries = ", ".join(f"{name}:'{symbol}'" for name, symbol in ITEM_TYPES.items())
    return "{ " + entries + " }"


def item_type_options_html():
    """Render ITEM_TYPES as a list of <option> elements, e.g. for a <select>."""
    return "\n".join(
        f'        <option value="{name}">{symbol} {name}</option>'
        for name, symbol in ITEM_TYPES.items()
    )


def process_template(template_path):
    """
    Process a template file to generate the derived output.

    Template syntax:
        {INCLUDE:path/to/file.py} - includes the content of the specified file
        {ITEM_EMOJI_JS} - a JS object literal of ITEM_TYPES, from classes/item_types.py
        {ITEM_TYPE_OPTIONS_HTML} - a list of <option> elements, one per ITEM_TYPES entry
        Remove any lines with the string '#omitfrombuild'
        Everything else is literal content
    """

    def get_file_from_match(match):
        """Return the contents of the file matched by the given RE Match object."""
        include_path = match.group(1)
        file_path = Path(include_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Component file for {output_path} not found: {include_path}")
        return file_path.read_text()

    template_path = Path(template_path)

    # Derive output path: target.py.template -> target.py
    if template_path.suffix == ".template":
        output_path = template_path.with_suffix("")
    else:
        raise RuntimeError("Template file name must end in .template")

    template_content = template_path.read_text()

    # Replace all include markers with file contents
    output_content = re.sub(
        r'\{INCLUDE: ?([^}]+)\}',
        get_file_from_match,
        template_content
    )

    # Replace item-type markers with content derived from classes/item_types.py
    output_content = output_content.replace("{ITEM_EMOJI_JS}", item_emoji_js())
    output_content = output_content.replace("{ITEM_TYPE_OPTIONS_HTML}", item_type_options_html())

    # Filter out lines with #omitfrombuild
    filtered = '\n'.join(line for line in output_content.splitlines() if not '#omitfrombuild' in line) + '\n'

    output_path.write_text(filtered)
    print(f"Built {output_path} from {template_path}")

# ---------------------------------------------------------------------------
# Drift check between the two RoboTurtle question types.
#
# python3_roboturtle (the original single-turtle type) and python3_roboturtle_oo (the object-oriented
# type) are deliberately independent folders - one folder per question type. But the files below are
# meant to be IDENTICAL in both, so a fix made in one has to be made in the other. This build.py is one
# of them, so the same copy of this code runs in both folders. A normal build ends by warning about any
# that have drifted apart; "python build.py --check-sync" does only the check and exits with status 1 on
# drift (add -v to see the differences). Everything else - world.py, the goal worlds, the student-facing
# classes, help.html, the editor ... - differs by design and is not checked.
# ---------------------------------------------------------------------------
SIBLING_FOLDERS = ("python3_roboturtle", "python3_roboturtle_oo")
SHARED_FILES = [
    "build.py",
    "turtle.py",                       # The Jobe-server stub for Turtle and Screen
    "classes/item_types.py",           # Item type names and emoji
    "classes/item.py",
    "roboturtle.js",                   # The browser-side runtime, including its setup checks
    "prototypeextra.html.template",    # The HTML skeleton that wraps roboturtle.js
]


def check_sibling_sync(show_diffs=False):
    """Compare SHARED_FILES here with the sibling question type's copies. Print a summary of any
       differences and return how many files differ (0 if all match or there is no sibling to compare).
    """
    import difflib
    here = Path(__file__).resolve().parent
    if here.name not in SIBLING_FOLDERS:
        return 0
    sibling = here.parent / [name for name in SIBLING_FOLDERS if name != here.name][0]
    if not sibling.is_dir():
        return 0
    drifted = []
    for name in SHARED_FILES:
        ours, theirs = here / name, sibling / name
        if not ours.exists() or not theirs.exists():
            drifted.append((name, "missing from " + (here.name if not ours.exists() else sibling.name), []))
            continue
        a, b = theirs.read_text().splitlines(), ours.read_text().splitlines()
        if a != b:
            diff = list(difflib.unified_diff(a, b, f"{sibling.name}/{name}", f"{here.name}/{name}", lineterm="", n=1))
            changed = sum(1 for line in diff if line[0] in "+-" and not line.startswith(("+++", "---")))
            drifted.append((name, f"{changed} changed lines", diff))
    if drifted:
        print()
        print("*" * 78)
        print(f"WARNING: {len(drifted)} file(s) that should be identical in {here.name} and {sibling.name} differ:")
        for name, how, diff in drifted:
            print(f"    {name}  ({how})")
            if show_diffs:
                for line in diff:
                    print("        " + line)
        print("Decide which version is right and copy it into the other folder (python build.py --check-sync -v")
        print("shows the differences).")
        print("*" * 78)
    return len(drifted)


if __name__ == "__main__":
    if "--check-sync" in sys.argv:
        drift = check_sibling_sync(show_diffs="-v" in sys.argv)
        print("Shared files match." if not drift else "")
        sys.exit(1 if drift else 0)
    process_template("assembledrobot.py.template")
    process_template("template.py.template")
    process_template("prototypeextra.html.template")
    process_template("editor.html.template")
    check_sibling_sync()
