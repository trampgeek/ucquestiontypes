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

if __name__ == "__main__":
    process_template("assembledrobot.py.template")
    process_template("template.py.template")
    process_template("prototypeextra.html.template")
    process_template("editor.html.template")