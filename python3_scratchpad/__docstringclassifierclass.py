"""
DocstringClassifier: validates function or module docstrings using an LLM.
This version uses Linux SIGALRM to enforce a strict wall-clock timeout for
blocking I/O — ideal for JOBE servers (one job = one Python process).
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

OPEN_ROUTER_KEY = "*************************************"

TIMEOUT = 6     # Hard wall-clock timeout in seconds

MODELS = {
    'dsr1:14b-cosc': "deepseek-r1:14b",
    'dsr1:32b-cosc': "deepseek-r1:32b",
    'dsr1:70b-cosc': "deepseek-r1:70b",
    'ds3.1': "deepseek/deepseek-chat-v3.1:free",

    'gemini2.5f': 'google/gemini-2.5-flash',

    'gemma2:9b': "google/gemma-2-9b-it",
    'gemma3:4b': "google/gemma-3n-e4b-it:free",  # Very limited use
    'gemma3:4b-local': "gemma3:4b",
    'gemma3:12b-cosc': "gemma3:12b",
    'gemma3:27b': "google/gemma-3-27b-it",
    'gemma3:27b-cosc': "gemma3:27b",

    'gpt4om': 'openai/gpt-4o-mini',

    'llama3.3:8bi': "meta-llama/llama-3.3-8b-instruct",
    'llama3.3:8b-local': "llama3:8b",
    'llama3.3:70bi': "meta-llama/llama-3.3-70b-instruct",
    
    'mixtral8:7bi': "mistralai/mixtral-8x7b-instruct",

    'qwen2.5:7bci': "qwen/qwen2.5-coder-7b-instruct", # Slow. Reasoning?
    'qwen3:1.7b-local': "qwen3:1.7b",
    'qwen3:4b-local': "qwen3:4b",
    'qwen3:4b-cosc': "qwen3:4b",
    'qwen3:4b': "qwen/qwen3-4b:free",  # Very limited use
    'qwen3:8b': "qwen/qwen3-8b",  # Reasoning model - slow
    'qwen3:8b-cosc': "qwen3:8b",
    'qwen3:8bds': "deepseek/deepseek-r1-0528-qwen3-8b:free",
    'qwen3:14b-cosc': "qwen3:14b",
    'qwen3:30bi': "qwen/qwen3-30b-a3b-instruct-2507",
    'qwen3:235b': "qwen/qwen3-235b-a22b-2507",

    'sonnet4': "anthropic/claude-sonnet-4",
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
    """Classify docstrings using the given LLM model, which must be 
       a key in the above models list.
    """
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.function_system_prompt = FUNCTION_SYSTEM_PROMPT + "\nFunction whose docstring is to be classified:\n"
        self.program_system_prompt   = PROGRAM_SYSTEM_PROMPT   + "\nProgram whose module docstring is to be classified:\n"

        # Choose endpoint
        if model.endswith('-local'):
            self.base_url = "http://localhost:11434/v1"
        elif model.endswith('-cosc'):
            self.base_url = "http://cs25005IY:11434/v1"
        else:
            self.base_url = "https://openrouter.ai/api/v1"

        self.api_key = OPEN_ROUTER_KEY


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
            return "VALID - but only because we're not using the LLM"
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://csse.canterbury.ac.nz",
                "X-Title": "Docstring Validator",
            }

            data = {
                "model": MODELS[self.model],
                "temperature": 0.0,
                "seed": 1,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{system_prompt}\n{code}",
                    }
                ],
                "provider": {"zdr": True},
            }

            request = urllib.request.Request(
                url=f"{self.base_url}/chat/completions",
                data=json.dumps(data).encode(),
                headers=headers,
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
            return "VALID - but only because the request timed out"

        except urllib.error.URLError as e:
            # Catch timeout-like cases robustly
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                return "VALID - but only because the request timed out"
            return f"VALID - but only because the request raised an exception '{e}'"

        except Exception as e:
            if "timed out" in str(e).lower():
                return "VALID - but only because the request timed out"
            return f"VALID - but only because the request raised an exception '{e}'"

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
