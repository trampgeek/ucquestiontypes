import locale
import json
import os
import re
import html
import random

from pytester import PyTester

STANDARD_PYLINT_OPTIONS = ['--disable=trailing-whitespace,superfluous-parens,' +
                      'bad-continuation,min-public-methods,too-few-public-methods,star-args,' +
                      'unbalanced-tuple-unpacking,too-many-statements,' +
                      'consider-using-enumerate,simplifiable-if-statement,' +
                      'consider-iterating-dictionary,trailing-newlines,no-else-return,' +
                      'consider-using-dict-comprehension,' +
                      'len-as-condition,inconsistent-return-statements,consider-using-join,' +
                      'singleton-comparison,unused-variable,chained-comparison,no-else-break,' +
	                  'consider-using-in,useless-object-inheritance,unnecessary-pass,' +	
                      'consider-using-set-comprehension,no-else-raise,duplicate-string-formatting-argument',
                      '--enable=C0326',
                      '--good-names=i,j,k,n,s,c,_'
                      ]

locale.setlocale(locale.LC_ALL, 'C.UTF-8')

KNOWN_PARAMS = {
    'abortonerror': True,
    'allowglobals': False,
    'banglobalcode': True,
    'allownestedfunctions': False,
    'checktemplateparams': True,
    'echostandardinput': True,
    'extra': 'None',
    'floattolerance': None,
    'globalextra': 'None',
    'imagewidth': None,
    'imports': [],
    'isfunction': True,
    'maxfunctionlength': 30,
    'maxnumconstants': 4,
    'maxoutputbytes': 10000,
    'maxstringlength': 2000,
    'norun': False,
    'nostylechecks': False,
    'notest': False,
    'parsonsproblemthreshold': None, # The number of checks before parsons' problem displayed
    'precheckers': ['pylint'],
    'prelude': '',
    'proscribedbuiltins': ['exec', 'eval'],
    'proscribedfunctions': [],
    'proscribedconstructs': ["goto"],
    'proscribedsubstrings': [],
    'pylintoptions': [],
    'requiredconstructs': [],
    'requiredfunctiondefinitions': [],
    'requiredfunctioncalls': [],
    'requiredsubstrings': [],
    'requiretypehints': False,
    'restrictedfiles': {
        'disallow': ['__.*', 'prog.*', 'pytester.py'],
    },
    'restrictedmodules': {
        'builtins': {
            'onlyallow': []
        },
        'imp': {
            'onlyallow': []  
        },
        'importlib': {
            'onlyallow': []  
        },
        'os': {
            'disallow': ['system', '_exit', '_.*']
        },
        'subprocess': {
            'onlyallow': []
        },
        'sys': {
            'disallow': ['_.*']
        },
    },
    'runextra': False,
    'showfeedbackwhenright': False,
    'stdinfromextra': False,
    'strictwhitespace': True,
    'stripmain': False,
    'stripmainifpresent': False,
    'testisbash': False,
    'timeout': 5,
    'totaltimeout': 50,
    'suppresspassiveoutput': False,
    'useanswerfortests': False,
    'usesmatplotlib': False,
    'usesnumpy': False,
    'usesubprocess': False,
    'warnifpassiveoutput': True,
}

class TestCase:
    def __init__(self, dict_rep):
        """Construct a testcase from a dictionary representation obtained via JSON"""
        self.testcode = dict_rep['testcode']
        self.stdin = dict_rep['stdin']
        self.expected = dict_rep['expected']
        self.extra = dict_rep['extra']
        self.display = dict_rep['display']
        try:
            self.testtype = int(dict_rep['testtype'])
        except:
            self.testtype = 0
        self.hiderestiffail = bool(int(dict_rep['hiderestiffail']))
        self.useasexample = bool(int(dict_rep['useasexample']))
        self.mark = float(dict_rep['mark'])


# ================= CODE TO DO ALL TWIG PARAMETER PROCESSING ===================

def process_template_params():
    """Extract the template params into a global dictionary PARAMS"""
    global PARAMS
    PARAMS = json.loads("""{{ QUESTION.parameters | json_encode | e('py') }}""")
    checktemplateparams = PARAMS.get('checktemplateparams', True)
    if checktemplateparams:
        unknown_params = set(PARAMS.keys()) - set(KNOWN_PARAMS.keys())
        filtered_params = [param for param in unknown_params if not param.startswith('_')]
        if filtered_params:
            print("Unexpected template parameter(s):", list(sorted(filtered_params)))

    for param_name, default in KNOWN_PARAMS.items():
        if param_name in PARAMS:
            param = PARAMS[param_name]
            if type(param) != type(default) and default is not None:
                print("Template parameter {} has wrong type (expected {})".format(param_name, type(default)))
        else:
            PARAMS[param_name] = default;

    if PARAMS['extra'] == 'stdin':
        PARAMS['stdinfromextra'] = True
    if PARAMS['runextra']:
        PARAMS['extra'] = 'pretest'  # Legacy support
    if PARAMS['timeout'] < 2:
        PARAMS['timeout'] = 2  # Allow 1 extra second freeboard 
    PARAMS['pylintoptions'] = STANDARD_PYLINT_OPTIONS + PARAMS['pylintoptions']
    if PARAMS['allowglobals']:
        PARAMS['pylintoptions'].append("--const-rgx='[a-zA-Z_][a-zA-Z0-9_]{2,30}$'")
    if PARAMS['usesmatplotlib']:
        PARAMS['pylintoptions'].append("--disable=reimported,wrong-import-position,wrong-import-order,unused-import")
    if PARAMS['testisbash']:
        print("testisbash is not implemented for Python")


def get_test_cases():
    """Return an array of Test objects from the template parameter TESTCASES"""
    test_cases = [TestCase(test) for test in json.loads("""{{ TESTCASES | json_encode | e('py') }}""")]
    return test_cases


def scrambled(answer):
    """Return a randomly reordered version of the given answer"""
    if answer.strip() == '':
        return ''
    docstrings = re.findall(r'""".*?"""', answer) + re.findall(r"'''.*?'''", answer)
    rest = re.sub(r'""".*?"""', '', answer)
    rest2 = re.sub(r"'''.*?'''", '', rest)
    lines = [line.strip() for line in (rest2.splitlines() + docstrings) if line.strip()]
    original = lines[:]
    while original == lines: # Make sure the order changes!
        random.shuffle(lines)
    return '\n'.join(lines)
    

def process_global_params():
    """Plug into the PARAMS variable all the "global" parameters from
       the question and its answer (as distinct from the template parameters).
    """
    PARAMS['STUDENT_ANSWER'] = """{{ STUDENT_ANSWER | e('py') }}""".strip() + '\n'
    PARAMS['SEPARATOR'] = "#<ab@17943918#@>#"
    PARAMS['IS_PRECHECK'] = "{{ IS_PRECHECK }}" == "1"
    PARAMS['QUESTION_PRECHECK'] = {{ QUESTION.precheck }} # Type of precheck: 0 = None, 1 = Empty etc
    PARAMS['ALL_OR_NOTHING'] = "{{ QUESTION.allornothing }}" == "1" # Whether or not all-or-nothing grading is being used
    PARAMS['GLOBAL_EXTRA'] = """{{ QUESTION.globalextra | e('py') }}\n"""
    PARAMS['STEP_INFO'] = json.loads("""{{ QUESTION.stepinfo | json_encode }}""")
    answer = """{{QUESTION.answer | e('py')}}""".strip()
    if answer:
        if PARAMS['STUDENT_ANSWER'] == answer:
            PARAMS['AUTHOR_ANSWER'] = "<p>Your answer is an <i>exact</i> match with the author's solution.</p>"
        else:
            with open("__author_solution.html") as file:
                PARAMS['AUTHOR_ANSWER'] = (file.read().strip() % html.escape(answer))
        with open("__author_solution_scrambled.html") as file:
            PARAMS['AUTHOR_ANSWER_SCRAMBLED'] = (file.read().strip() % html.escape(scrambled(answer))) + "\n"
    else:
        PARAMS['AUTHOR_ANSWER'] = PARAMS['AUTHOR_ANSWER_SCRAMBLED'] = ''


def update_test_cases(test_cases, outcome):
    """Return the updated testcases after replacing all empty expected fields with those from the
       given outcome's test_results which must have a column header 'Got'. Non-empty existing expected
       fields are left unchanged.
       If any errors occur, the return value will be None and the outcome parameter will have had its prologuehtml
       value updated to include an error message.
    """
    try:
        results = outcome['testresults']
        col_num = results[0].index('Got')
        for i in range(len(test_cases)):
            if test_cases[i].expected.strip() == '':
                test_cases[i].expected = results[i + 1][col_num]
    except ValueError:
        outcome['prologuehtml'] = "No 'Got' column in result table from which to get testcase expecteds"
        test_cases = None
    except Exception as e:
        outcome['prologuehtml'] = "Unexpected error ({}) extracting testcase expecteds from sample answer output".format(e)
        test_cases = None
    return test_cases


def get_expecteds_from_answer(params, test_cases):
    """Run all tests using the sample answer rather than the student answer.
       Fill in the expected field of each test case using the sample answer and return
       the updated test case list.
       Return None if the sample answer gave any sort of runtime error
    """
    new_params = {key: value for key, value in params.items()}
    new_params['IS_PRECHECK'] = False
    new_params['nostylechecks'] = True
    new_params['STUDENT_ANSWER'] = """{{ QUESTION.answer | e('py') }}"""
    new_params['running_sample_answer'] = True
    tester = PyTester(new_params, test_cases)
    outcome = tester.test_code()
    if 'prologuehtml' in outcome:
        outcome['prologuehtml'] = "<h2>ERROR IN QUESTION'S SAMPLE ANSWER. PLEASE REPORT</h2>\n" + outcome['prologuehtml']
        return outcome, None
    else:
        return outcome, update_test_cases(test_cases, outcome)


process_template_params()
test_cases = get_test_cases()
process_global_params()

if PARAMS['useanswerfortests']:
    outcome, test_cases = get_expecteds_from_answer(PARAMS, test_cases)

if test_cases:
    tester = PyTester(PARAMS, test_cases)
    outcome = tester.test_code()
    feedback = ''
    parsons_threshold = float('inf') if PARAMS['parsonsproblemthreshold'] is None else PARAMS['parsonsproblemthreshold']
    if outcome['fraction'] != 1 and not PARAMS['IS_PRECHECK'] and PARAMS['STEP_INFO']['numchecks'] + 1 >= parsons_threshold:
        feedback = PARAMS['AUTHOR_ANSWER_SCRAMBLED']
    elif outcome['fraction'] == 1 and PARAMS['showfeedbackwhenright'] and not (PARAMS['IS_PRECHECK']):
        feedback = PARAMS['AUTHOR_ANSWER']
    if feedback:
        if 'epiloguehtml' in outcome:
            if outcome['epiloguehtml'].strip():
                outcome['epiloguehtml'] += '<br>'
        else:
            outcome['epiloguehtml'] = ''
        outcome['epiloguehtml'] += f'<div style="background-color: #f4f4f4">{feedback}</div>'
print(json.dumps(outcome))

