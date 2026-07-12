"""
CodeFeedback class - uses an AI to get feedback on a students code, given also the
reference answer (author's solution).
This version routes all requests to openrouter.ai through an Cloudflare worker:
https://openrouterproxy2026.trampgeek.workers.dev/
"""

import ast
import re
import json
import urllib.request
import urllib.error
import signal

from __secrets import CLOUDFLARE_API_KEY


# ======================================
#  Configuration
# ======================================

WORKER_URL = "https://openrouterproxy2026.trampgeek.workers.dev/"

TIMEOUT = 10     # Hard wall-clock timeout in seconds

MODELS = {
    'dsr1:14b-cosc': "deepseek-r1:14b",
    'dsr1:32b-cosc': "deepseek-r1:32b",
    'dsr1:70b-cosc': "deepseek-r1:70b",
    'ds3.1': "deepseek/deepseek-chat-v3.1:free",
    'dsv4flash': "deepseek/deepseek-v4-flash",

    'gemini3.1f': 'google/gemini-3.1-flash-lite',

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
    'qwen2.5:32bci': "qwen/qwen-2.5-coder-32b-instruct",
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

SYSTEM_PROMPT = open("__ai_feedback_system_prompt.txt").read()

#DEFAULT_MODEL = 'gemma3:27b-cosc'
#DEFAULT_MODEL = 'dsv4flash'
DEFAULT_MODEL = 'gemini3.1f'


# ======================================
#  Custom timeout exception
# ======================================

class RequestTimeout(Exception):
    """Raised when SIGALRM fires"""
    pass



# ======================================
#  CodeFeedback class
# ======================================

class CodeFeedback:
    """Get feeback on given student's codeusing the given LLM model, which must be 
       a key in the above models list.
    """
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.system_prompt = SYSTEM_PROMPT


        # Choose endpoint
        self.is_local = True
        if model.endswith('-local'):
            self.url = "http://localhost:11434/v1/chat/completions"
        elif model.endswith('-cosc'):
            self.url = "http://132.181.10.39:11434/v1/chat/completions"
        else:
            self.url = WORKER_URL
            self.is_local = False


   
    # --------------------------------------
    # Public API
    # --------------------------------------
    def get_feedback(self, student_code, authors_code, extra_prompt=''):
        prompt = self.system_prompt.replace("{{EXTRA_GUIDANCE}}", extra_prompt)
        return self.ask_llm(student_code, authors_code, self.system_prompt)


 
    # --------------------------------------
    #  Core request + timeout logic
    # --------------------------------------
    def ask_llm(self, student_code, authors_code, system_prompt):

        # Handler that SIGALRM invokes
        def timeout_handler(signum, frame):
            raise RequestTimeout("Timed out")

        # Set handler & alarm
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT)

        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "application/json",
            }

            if self.is_local:
                headers['X-Title'] = 'Code feedback'
            else:
                headers["Authorization"] = f"Bearer {CLOUDFLARE_API_KEY}"

            data = {
                "model": MODELS[self.model],
                "temperature": 0.0,
                "seed": 1,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "system",
                        "content": f"{system_prompt}",
                    },
                    {
                        "role": "user",
                        "content": f"Student's Code: {student_code}\n\nAuthor's Answer: {authors_code}",
                    }
                ],
                "provider": {"zdr": True},
            }

            request = urllib.request.Request(
                url=self.url,
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
            return "Sorry: Request timed out. The AI is busy or unavailable, so no feedback is available."

        except urllib.error.URLError as e:
            # Catch timeout-like cases robustly
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                return "Sorry: Request timed out. The AI is busy or unavailable, so no feedback is available."
            error_body = e.read().decode(errors='replace')
            print(f"HTTP {e.code}: {error_body}")
            return f"Sorry, no feedback is available (the request raised an exception '{e}')"

        except Exception as e:
            if "timed out" in str(e).lower():
                return "Sorry: Request timed out. The AI is busy or unavailable, so no feedback is available."
            return f"Sorry, no feedback is available (the request raised an exception '{e}')"

        finally:
            # Always clean up
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


# ======================================
#  Test
# ======================================
if __name__ == "__main__":
    student_code = [
'''def print_index_product(numbers):
    "madpih"
    n = len(numbers)
    i = 0
    for i in range(0, n):
        num = numbers[i]
        print(f"{i * num}")
''',

'''def print_index_product(numbers):
    """takes a list of numbers and prints each number in the list times ots 
    index in the list."""
    i = len(numbers)
    for num in range(0, i):
        numend = numbers[num]
        print(numend * num)
''',

'''def print_index_product(nums):
    """Print each number times its index"""
    i = 0
    n = len(nums)
    while i < n:
        number = nums[i]
        product = number * i
        print(product)
        i += 1
''', 

'''def print_index_product(numbers):
    """Prints each number in numbers times its index in the list"""
    n = len(numbers)
    for i in range(0, n):
        num = numbers[i]
        print(i * num)
'''

    ]

    authors_answer = '''def print_index_product(numbers):
"""Prints each number in numbers times its index in the list"""
n = len(numbers)
for i in range(0, n):
    num = numbers[i]
    print(i * num)
'''

    cf = CodeFeedback()
    taught = ["expressions", "assignment", "if statements", "while loops", "for loops"]
    for i, code in enumerate(student_code, 1):
        print(f"Test #{i}")
        print(cf.get_feedback(code, authors_answer))
        print("\n")