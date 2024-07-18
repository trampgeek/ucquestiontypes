import locale
import json
import os
import re
import html
import random

from pytester import PyTester

STANDARD_PYLINT_OPTIONS = ['--disable=trailing-whitespace,superfluous-parens,' + 
                      'too-few-public-methods,consider-using-f-string,' + 
                      'unbalanced-tuple-unpacking,too-many-statements,' + 
                      'consider-using-enumerate,simplifiable-if-statement,' + 
                      'consider-iterating-dictionary,trailing-newlines,no-else-return,' + 
                      'consider-using-dict-comprehension,consider-using-generator,' + 
                      'len-as-condition,inconsistent-return-statements,consider-using-join,' + 
                      'singleton-comparison,unused-variable,chained-comparison,no-else-break,' + 
	                  'consider-using-in,useless-object-inheritance,unnecessary-pass,' + 
	                  'reimported,wrong-import-order,wrong-import-position,ungrouped-imports,' + 
                      'consider-using-set-comprehension,no-else-raise,' + 
                      'unspecified-encoding,use-dict-literal,,consider-using-with,' + 
                      'duplicate-string-formatting-argument,consider-using-dict-items,' + 
                      'consider-using-max-builtin,use-a-generator ', 
                      '--good-names=i,j,k,n,s,c,_' 
                      ] 


locale.setlocale(locale.LC_ALL, 'C.UTF-8')

KNOWN_PARAMS = {
    'abortonerror': True,
    'allowglobals': False,
    'banglobalcode': True,
    'allownestedfunctions': False,
    'checktemplateparams': True,
    'dpi': 65,
    'echostandardinput': True,
    'extra': 'None',
    'floattolerance': None,
    'forcepylint': False,
    'globalextra': 'None',
    'imagewidth': None,
    'imports': [],
    'isfunction': True,
    'localprechecks': True,
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
    'testre': '',
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


def get_tests_from_example_table():
    """Return a list of Test objects build from the Example table for this question type"""
    num_rows = len(PARAMS['EXAMPLE_TESTS'])
    tests = []
    for i in range(num_rows):
        testcode = PARAMS['EXAMPLE_TESTS'][i]
        result = PARAMS['EXAMPLE_EXPECTEDS'][i]
        test = TestCase({
            'testcode': testcode,
            'stdin': '',
            'expected': result,
            'extra': '',
            'display': 'show',
            'hiderestiffail': False,
            'useasexample': True,
            'mark': 1.0
        })
        tests.append(test)
    return tests


def build_new_outcome(outcome):
    """Replace the testresults table with customised prologuehtml that
       contains a table more appropriate to this question type.
    """
    GREYS = ['#f0f0f0', '#e0e0e0']
    IS_CORRECT_COL = 4
    
    def style(colour, padding=5, border='border:1px solid darkgray', extrastyle=''):
        """The style to use for a cell"""
        return f'style="background-color:{colour};padding:{padding}px;{border};{extrastyle};"'
        
    locked = get_readonly_cells()
    html = '<table class="table table-bordered" style="width:auto">\n'
    html += f'<tr><th {style(GREYS[0])}>Test</th><th {style(GREYS[0])}>Result</th><th {style(GREYS[0])}>Valid test?</th>'
    for i, row in enumerate(outcome['testresults'][1:]):
        is_correct = row[IS_CORRECT_COL]
        html += '<tr>'
        
        # Extract the testcode and expected from the result table.
        # Colour the cells according to whether they were user-editable and
        # if so according to whether the test was labelled correct or not.
        for result_table_col, test_table_col in [(1, 0), (2, 1)]:
            row_colour = colour = GREYS[(i + 1) % 2]
            if (i, test_table_col) not in locked and not is_correct: 
                # If this is a cell allowing user entry and test is wrong
                colour = '#fcc'  # Red
            html += f'<td {style(colour)}"><pre {style(colour, 0, "")}>{row[result_table_col]}</pre></td>'
        if is_correct:
            html += f'<td {style(row_colour, extrastyle="text-align:center")}><span style="color: green;">✔</span></td>\n'
        else:
            html += f'<td {style(row_colour, extrastyle="text-align:center")}><span style="font-size: 16pt; color: red;">✘</span></td>\n'
        
    html += '</table>\n'
    outcome['epiloguehtml'] = html
    del outcome['testresults']
    return outcome


def get_answer():
    """Return the sample answer"""
    answer_json = """{{QUESTION.answer | e('py')}}""".strip()
    try:
        answer = json.loads(answer_json)['main_answer_code'][0]
    except:
        answer = answer_json  # Assume this is the original solution
    return answer
    
    
def get_readonly_cells():
    """Return a list of the readonly cells"""
    preload = json.loads("""{{QUESTION.answerpreload | e('py')}}""".strip())
    cells = []
    for cell_label in json.loads(preload['cr_readonly_cells'][0]).keys():
        mat = re.match(r'cell-(\d+)-(\d+)', cell_label)
        cells.append((int(mat[1]), int(mat[2])))  # (row, column)
    return cells
    
    
def process_global_params():
    """Plug into the PARAMS variable all the "global" parameters from
       the question and its answer (as distinct from the template parameters).
    """
    response = json.loads("""{{ STUDENT_ANSWER | e('py') }}""")
    PARAMS['STUDENT_ANSWER'] = response['main_answer_code'][0].rstrip() + '\n'
    PARAMS['EXAMPLE_TESTS'] = response['test_table_col0']
    PARAMS['EXAMPLE_EXPECTEDS'] = response['test_table_col1']
    PARAMS['SEPARATOR'] = "#<ab@17943918#@>#"
    PARAMS['IS_PRECHECK'] = "{{ IS_PRECHECK }}" == "1"
    PARAMS['QUESTION_PRECHECK'] = {{ QUESTION.precheck }} # Type of precheck: 0 = None, 1 = Empty etc
    PARAMS['ALL_OR_NOTHING'] = "{{ QUESTION.allornothing }}" == "1" # Whether or not all-or-nothing grading is being used
    PARAMS['GLOBAL_EXTRA'] = """{{ QUESTION.globalextra | e('py') }}\n"""
    PARAMS['STEP_INFO'] = json.loads("""{{ QUESTION.stepinfo | json_encode }}""")
    answer = get_answer()
    if answer:
        if PARAMS['STUDENT_ANSWER'].strip() == answer.strip():
            PARAMS['AUTHOR_ANSWER'] = "<p>Your answer is an <i>exact</i> match with the author's solution.</p>"
        else:
            with open("__author_solution.html") as file:
                PARAMS['AUTHOR_ANSWER'] = (file.read().strip() % html.escape(answer))
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


def run_tests(params, test_cases):
    """Run all tests using the sample answer rather than the student answer"""
    new_params = {key: value for key, value in params.items()}
    new_params['IS_PRECHECK'] = False
    new_params['nostylechecks'] = True
    new_params['STUDENT_ANSWER'] = get_answer()
    new_params['running_sample_answer'] = True
    tester = PyTester(new_params, test_cases)
    outcome = tester.test_code()
    return outcome
    
    
def get_expecteds_from_answer(params, test_cases):
    """Run all tests using the sample answer rather than the student answer.
       Fill in the expected field of each test case using the sample answer and return
       the updated test case list.
       Return None if the sample answer gave any sort of runtime error
    """
    outcome = run_tests(params, test_cases)
    if 'prologuehtml' in outcome:
        outcome['prologuehtml'] = "<h2>ERROR IN QUESTION'S SAMPLE ANSWER. PLEASE REPORT</h2>\n" + outcome['prologuehtml']
        return outcome, None
    else:
        return outcome, update_test_cases(test_cases, outcome)


ok = True
process_template_params()
test_cases = get_test_cases()
process_global_params()
example_tests = get_tests_from_example_table()

outcome = {'fraction': 1.0}

if PARAMS['testre']:
    # Check all tests to see if they contain the desired regular expression
    bad_tests = []
    for test in example_tests:
        code = test.testcode
        if not re.search(PARAMS['testre'], code, re.DOTALL):
            bad_tests.append(code)
    if bad_tests:
        test_is = 'test is' if len(bad_tests) == 1 else 'tests are'
        outcome['fraction'] = 0.0
        outcome['prologuehtml'] = f"""<p>Sorry but the following {test_is} not in the required form.
Please re-read the question to see what was expected. Ask a tutor if you're still unsure.
<ul>"""
        for code in bad_tests:
            outcome['prologuehtml'] += f'<li><pre>{code}</pre></li>\n'
        outcome['prologuehtml'] += '</ol>'
        ok = False
    
if not PARAMS['IS_PRECHECK'] and ok:
    # Check the Example table cases with the so-called sample answer
    #print("Running example tests")
    
    outcome = run_tests(PARAMS, example_tests)
    outcome = build_new_outcome(outcome)
    if 'prologuehtml' in outcome:
        outcome['prologuehtml'] = "<h2>ERROR IN QUESTION'S HIDDEN TESTING CODE. PLEASE REPORT</h2>\n" + outcome['prologuehtml']
        ok = False
    elif outcome['fraction'] == 1.0:
        outcome['prologuehtml'] = '<h4>All good!</h4>'
    else:
        outcome['prologuehtml'] = """<b>One or more of your tests is invalid.</b>
<br>The erroneous cells are shaded red in the result table."""
        ok = False
    
print(json.dumps(outcome))
