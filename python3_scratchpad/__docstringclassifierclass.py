"""
DocstringClassifier: validates function or module docstrings using an LLM.
This version uses Linux SIGALRM to enforce a strict wall-clock timeout for
blocking I/O — ideal for JOBE servers (one job = one Python process).

Restricted to locally-hosted Ollama models only (no cloud/API-key-based
models) - the earlier version could also route to OpenRouter using
OPEN_ROUTER_KEY from __secrets.py, but that key sat in the same Jobe sandbox
as student code, exfiltratable via the unrestricted Scratchpad panel (see
conversation notes). Rather than build a secure channel to keep using a
cloud model that wasn't actually in use, this cuts the capability entirely:
no API key is imported or needed, since local Ollama servers require none.
"""

import ast
import re
import json
import urllib.request
import urllib.error
import signal


# ======================================
#  Configuration
# ======================================

TIMEOUT = 6     # Hard wall-clock timeout in seconds

# Local-network Ollama models only. Anything else is refused - see __init__.
MODELS = {
    'dsr1:14b-cosc': "deepseek-r1:14b",
    'dsr1:32b-cosc': "deepseek-r1:32b",
    'dsr1:70b-cosc': "deepseek-r1:70b",

    'gemma3:12b-cosc': "gemma3:12b",
    'gemma3:27b-cosc': "gemma3:27b",

    'qwen3:4b-cosc': "qwen3:4b",
    'qwen3:8b-cosc': "qwen3:8b",
    'qwen3:14b-cosc': "qwen3:14b",
}

FUNCTION_SYSTEM_PROMPT = open("function_system_prompt.txt").read()
PROGRAM_SYSTEM_PROMPT   = open("program_system_prompt.txt").read()

DEFAULT_MODEL = 'gemma3:27b-cosc'


# ======================================
#  Custom timeout exception
# ======================================

class RequestTimeout(Exception):
    """Raised when SIGALRM fires"""
    pass



# ======================================
#  Classifier
# ======================================

class DocstringClassifier:
    """Classify docstrings using the given local Ollama model, which must be
       a key in the above models list (name ending in '-local' or '-cosc').
    """
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.function_system_prompt = FUNCTION_SYSTEM_PROMPT + "\nFunction whose docstring is to be classified:\n"
        self.program_system_prompt   = PROGRAM_SYSTEM_PROMPT   + "\nProgram whose module docstring is to be classified:\n"

        if model.endswith('-cosc'):
            self.base_url = "http://132.181.10.39:11434/v1"
        else:
            raise ValueError(
                f"Model '{model}' is not a local Ollama model (must end in '-cosc'). "
                "Cloud/API-key-based models are no longer supported."
            )


    # --------------------------------------
    # Extract a function's docstring
    # --------------------------------------
    @staticmethod
    def extract_docstring(function_string):
        try:
            tree = ast.parse(function_string)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return ast.get_docstring(node)
            return None
        except SyntaxError:
            return None


    # --------------------------------------
    # Public API
    # --------------------------------------
    def classify_module_docstring(self, program):
        program = program.rstrip() + "\n"
        return self.ask_llm(program, self.program_system_prompt)


    def classify_function_docstring(self, function_string, use_llm=True):
        function_string = function_string.rstrip() + "\n"
        docstring = self.extract_docstring(function_string)
        if not docstring:
            return "INVALID - no docstring found."
        if len(docstring.split()) < 3:
            return "INVALID - docstring must have at least 3 words."
        if not use_llm:
            return "VALID - but not checked by the LLM"
        return self.ask_llm(function_string, self.function_system_prompt)


    # --------------------------------------
    #  Core request + timeout logic
    # --------------------------------------
    def ask_llm(self, code, system_prompt):

        # Handler that SIGALRM invokes
        def timeout_handler(signum, frame):
            raise RequestTimeout("Timed out")

        # Set handler & alarm
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT)

        try:
            data = {
                "model": MODELS[self.model],
                "temperature": 0.0,
                "seed": 1,
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{system_prompt}\n{code}",
                    }
                ],
            }

            request = urllib.request.Request(
                url=f"{self.base_url}/chat/completions",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method='POST'
            )

            # This blocking call **will** be interrupted by SIGALRM on Linux
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                result = json.loads(response.read().decode())
                msg = result["choices"][0]["message"]["content"]

                # Strip <think>…</think> if present
                msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.DOTALL)

                return msg.strip()

        except RequestTimeout:
            return "VALID - but not LLM checked (timed out)"

        except urllib.error.URLError as e:
            # Catch timeout-like cases robustly
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                return "VALID - but not LLM checked (timed out)"
            return f"VALID - but not LLM checked (the request raised an exception '{e}')"

        except Exception as e:
            if "timed out" in str(e).lower():
                return "VALID - but only because the request timed out"
            return f"VALID - but not LLM checked (the request raised an exception '{e}')"

        finally:
            # Always clean up
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


# ======================================
#  Test
# ======================================
if __name__ == "__main__":
    func = '''def num_adult_tickets(grandparent1_age, grandparent2_age):
    """Return a count of how many of you and your two grandparents
       are not seniors.
    """
    count = 1
    if grandparent1_age < 65:
        count += 1
    if grandparent2_age < 65:
        count += 1
    return count
'''
    clf = DocstringClassifier()
    print(clf.classify_function_docstring(func))
    prog = '''"""A program for processing volume data read from a file.
Written for COSC131.
Author: Angus McGurkinshaw
Date: 30 February 2021
"""

from os.path import isfile
LITRES_PER_GALLON =3.7854

# Get filename
def get_filename():
    """ """
    prompt = "Input csv file name? "
    error_message = "File does not exist."
    filename = input(prompt)
    while not isfile(filename):
        print(error_message)
        filename = input(prompt)
    return filename

# Read data from file into a list
def file_to_list(filename):
    """ """
    infile = open(filename)
    lines = infile.read().splitlines()
    infile.close()
    data_in_gallons = [float(line) for line in lines]
    return data_in_gallons

# Convert data into litres
def data_to_litres(data_in_gallons):
    """ """
    data_in_litres = []
    for value_in_gallons in data_in_gallons:
        value_in_litres = value_in_gallons * LITRES_PER_GALLON
        data_in_litres.append(value_in_litres)
    return data_in_litres

# Calculate average
def average_calc(data_in_litres):
    """ """
    average = sum(data_in_litres) / len(data_in_litres)
    return average

# Print some statistics about the data
def print_statistics(data_in_litres, average):
    """ """
    print(f"Average volume: {average:.2f}")
    print(f"Minimum volume: {min(data_in_litres):.2f}")
    print(f"Maximum volume: {max(data_in_litres):.2f}")

def main():
    """ """
    filenames = get_filename()
    gallons_list = file_to_list(filenames)
    litres_list = data_to_litres(gallons_list)
    averages = average_calc(litres_list)
    print_statistics(litres_list, averages)

main()'''
    print(clf.classify_module_docstring(prog))
