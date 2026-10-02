# RoboTurtle Build Instructions

## File Structure

- **roboturtle.py** - The Python code for RoboTurtle (edit this file)
- **prototypeextra.html** - The complete HTML with embedded Python (generated, copy to CodeRunner)
- **build.py** - Build script that syncs roboturtle.py → prototypeextra.html
- **roboturtle_checker.py** - Template checking code for CodeRunner

## Development Workflow

### Making Changes to Python Code

1. **Edit** `roboturtle.py` with your changes
2. **Build** by running:
   ```bash
   python build.py
   ```
3. **Copy** `prototypeextra.html` to CodeRunner question authoring form

### How It Works

The build script:
- Reads `roboturtle.py`
- Finds the marker comments in `prototypeextra.html`:
  - `<!-- BEGIN ROBOTURTLE PYTHON -->`
  - `<!-- END ROBOTURTLE PYTHON -->`
- Replaces everything between the markers with the content from `roboturtle.py`
- Preserves all other HTML/JavaScript unchanged

### Important Notes

- ⚠️ **Always edit `roboturtle.py`**, not the Python code inside `prototypeextra.html`
- ⚠️ Don't remove the marker comments from `prototypeextra.html`
- ✅ The build script will overwrite the Python section in `prototypeextra.html`
- ✅ Final `prototypeextra.html` is still a single, copyable file

## Quick Reference

```bash
# After editing roboturtle.py:
python build.py

# Output:
# ✅ Successfully built prototypeextra.html from roboturtle.py
# 📋 You can now copy prototypeextra.html to CodeRunner
```
