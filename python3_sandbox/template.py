import json
import base64
import subprocess
import re
import os
import os.path
import sys

# Define lines of code to insert before student's code
PREFIX = [
          'import os',
          'import tempfile',
          "os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()",
          "import matplotlib",
          "matplotlib.use('Agg')",
          "import matplotlib.pyplot as __plt__",
          "__saved_input__ = input",
          "def input(prompt=''):",
          "    response = __saved_input__(prompt).rstrip()",
          "    print(response)",
          "    return response"
]

def make_data_uri(filename):
    """Given a png or jpeg image filename (which must end in .png or .jpg/.jpeg 
       resp.) return a data URI as a UTF-8 string.
    """
    with open(filename, 'br') as fin:
        contents = fin.read()
    contents_b64 = base64.b64encode(contents).decode('utf8')
    if filename.endswith('.png'):
        return "data:image/png;base64,{}".format(contents_b64)
    elif filename.endswith('.jpeg') or filename.endswith('.jpg'):
        return "data:image/jpeg;base64,{}".format(contents_b64)
    else:
        raise Exception("Unknown file type passed to make_data_uri")
        
    
def tweak_line_numbers(error):
    """Adjust the line numbers in the error message to account for extra lines"""
    new_error = ''
    for line in error.splitlines():
        match = re.match("(.*, line )([0-9]+)", line)
        if match:
            line = match.group(1) + str(int(match.group(2)) - len(PREFIX))
        new_error += line + '\n'
    return new_error

student_code = '\n'.join(PREFIX) + '\n'
student_code += """{{ STUDENT_ANSWER | e('py') }}"""
student_code += """\nif __plt__.get_fignums():
    __plt__.savefig('matplotliboutput')
"""
inputfile = None
if 'stdin.txt' in os.listdir():
    inputfile = open('stdin.txt')
    
output = ''
failed = False
try:
    outcome = subprocess.run(
        ['python3', '-c', student_code],
        stdin=inputfile,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout = 25, # 25 second timeout MUST BE LESS THAN DEFAULT FOR QUESTION TYPE
        universal_newlines=True,
        check=True
    )
except subprocess.CalledProcessError as e:
    outcome = e
    output = "Task failed with return code = {}\n".format(outcome.returncode)
    failed = True
except subprocess.TimeoutExpired as e:
    outcome = e
    output = "Task timed out\n"
output += outcome.stdout
if outcome.stderr:
    output += "*** Error output ***\n"
    output += tweak_line_numbers(outcome.stderr)

html = ''
if output:
    html += f"<h4>Text output:</h4>\n<pre style=background-color:white>{output}</pre>\n<hr style='border:0px'>\n"
else:
    html += f"<h5>No text output</h5>\n"

files = sorted(os.listdir())
for filename in files:
    if filename.endswith('.png'):
        data_uri = make_data_uri(filename)
        html += f"""<h4>{filename}</h4><img class="data-uri-example" title="{filename}" src="{data_uri}" alt="{filename}">
<hr style='border:0px'>
"""

# Lastly print the JSON-encoded result required of a combinator grader
print(json.dumps({'epiloguehtml': html,
                  'showoutputonly': True
}))

