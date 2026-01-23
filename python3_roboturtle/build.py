# build.py
from pathlib import Path
import re


def process_template(template_path):
    """
    Process a template file to generate the derived output.
    
    Template syntax:
        {INCLUDE:path/to/file.py} - includes the content of the specified file
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

    # Filter out lines with #omitfrombuild
    filtered = '\n'.join(line for line in output_content.splitlines() if not '#omitfrombuild' in line) + '\n'
    
    output_path.write_text(filtered)
    print(f"Built {output_path} from {template_path}")

if __name__ == "__main__":
    process_template("assembledrobot.py.template")
    process_template("template.py.template")
    process_template("prototypeextra.html.template")