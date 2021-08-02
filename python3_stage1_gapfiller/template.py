import html
import locale
import json
import os
import re
import sys

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
    'maxfieldlength': 100,
    'maxnumconstants': 4,
    'maxoutputbytes': 10000,
    'maxstringlength': 2000,
    'norun': False,
    'nostylechecks': False,
    'notest': False,
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
    def __init__(self, dict_rep, test_code_html=None):
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
        self.test_code_html = test_code_html


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



def get_expecteds_from_answer(params, test_cases, ui_source, answer_field_values):
    """Run all tests using the sample answer rather than the student answer.
       Fill in the expected field of each test case using the sample answer and return
       the updated test case list.
       Return None if the sample answer gave any sort of runtime error
    """
    # Insert answer fields into test cases.
    answer_test_cases = get_test_cases(ui_source, answer_field_values)
    new_params = {key: value for key, value in params.items()}
    new_params['IS_PRECHECK'] = False
    new_params['nostylechecks'] = True
    new_params['STUDENT_ANSWER'] = get_student_answer(ui_source, answer_field_values)
    new_params['running_sample_answer'] = True
    tester = PyTester(new_params, answer_test_cases)
    outcome = tester.test_code()
    if 'prologuehtml' in outcome:
        outcome['prologuehtml'] = "<h2>ERROR IN QUESTION'S SAMPLE ANSWER. PLEASE REPORT</h2>\n" + outcome['prologuehtml']
        return outcome, None
    else:
        return outcome, update_test_cases(test_cases, outcome)
        
        
# ================= CODE TO DO GAPFILLER STUFF ===================
def get_test_cases(ui_source, field_values):
    """Return an array of Test objects from the template parameter TESTCASES"""
    test_cases = []
    tests = json.loads("""{{ TESTCASES | json_encode | e('py') }}""")
    
    for test in tests:
        # If gaps come from test cases then we fill student answer into gaps.
        
        if ui_source == 'test0' and test['testcode'].strip() != '':
            test_code_html = insert_fields(htmlize(test['testcode']), field_values, highlight=True)
            test['testcode'] = insert_fields(test['testcode'], field_values)
            test_case = TestCase(test, test_code_html=test_code_html)
        else:
            test_case = TestCase(test)
        test_cases.append(test_case)
    return test_cases
    
# Expand the given code by inserting the given fields into the
# given code, after splitting it with the given regular expression.
# If highlight is true, the inserted text is wrapped in a <span> element
# with a special blue-grey background.
def insert_fields(code, fields, splitter=r"\{\[.*?\]\}", highlight=False):
    bits = re.split(splitter, code)
    if len(bits) != len(fields) + 1:
        print("Richard has goofed. Please report", file=sys.stderr)
        sys.exit()
        
    prog = bits[0]
    i = 1
    for value in fields:
        if len(value.splitlines()) > 1:
            # Indent all lines in a textarea by the indent of the first line
            indent = len(prog.splitlines()[-1])
            value_bits = value.splitlines()
            for j in range(1, len(value_bits)):
                value_bits[j] = indent * ' ' + value_bits[j]
            value = '\n'.join(value_bits) + '\n'
        if highlight:
            value = f"<span style='background-color:#c7cfe6;'>{value}</span>"
        prog += value + bits[i]
        i += 1
    return prog
    
def get_student_answer(ui_source, field_values):
    """Gets what should be consider the 'student answer'. If ui_source is test0
       then this will be empty as the student's answer is plugged directly into
       the test cases.
    """
    if ui_source == 'test0':
        # If prechecking then we should check that the code the in 'test0' is valid.
        if "{{ IS_PRECHECK }}" == "1":
            return insert_fields("""{{ QUESTION.testcases[0].testcode | e('py')}}""", field_values)
        else:
            return "'''docstring'''"
    else:
        return insert_fields("""{{ QUESTION.globalextra | e('py')}}""", field_values)

def snip(field):
    """Return the given field, snipped to a max of 10 chars"""
    return field if len(field) <= 10 else field[0:10] + '...'
        
def fields_precheck(field_values):
    """Checks field lengths (legacy) and no proscribed strings present in fields"""
    errors = []
    all_constructs = set()
    for field in field_values:
        if len(field) > PARAMS['maxfieldlength']:
            errors.append(f"Field '{snip(field)}' is too long. Maximum length is {PARAMS['maxfieldlength']}")
        for bad in PARAMS['proscribedsubstrings']:
            if bad in field:
                errors.append(f"Field '{snip(field)}' contains the banned string '{bad}'")
    return errors
        
def htmlize(message):
    """An html version of the given error message"""
    return '<pre>' + html.escape(message) + '</pre>' if message else ''
    
def process_global_params(ui_source, field_values):
    """Plug the globals STUDENT_ANSWER, IS_PRECHECK and QUESTION_PRECHECK into the global PARAMS """
    PARAMS['STUDENT_ANSWER'] = get_student_answer(ui_source, field_values) + '\n'
    PARAMS['SEPARATOR'] = "#<ab@17943918#@>#"
    PARAMS['IS_PRECHECK'] = "{{ IS_PRECHECK }}" == "1"
    PARAMS['QUESTION_PRECHECK'] = {{ QUESTION.precheck }} # Type of precheck: 0 = None, 1 = Empty etc
    PARAMS['ALL_OR_NOTHING'] = "{{ QUESTION.allornothing }}" == "1" # Whether or not all-or-nothing grading is being used
    PARAMS['GLOBAL_EXTRA'] = """{{ QUESTION.globalextra | e('py') }}\n"""

# Get fields and ui params.
ui_params = json.loads("""{{ QUESTION.uiparameters | json_encode | e('py') }}""")
if ui_params and 'ui_source' in ui_params:
    ui_source = ui_params['ui_source']
else:
    ui_source = 'globalextra'
    
field_values = json.loads(""" {{ STUDENT_ANSWER | e('py') }}""")
answer_field_values = json.loads(""" {{ QUESTION.answer | e('py') }}""")


process_template_params()
test_cases = get_test_cases(ui_source, field_values)
process_global_params(ui_source, field_values)

errors = fields_precheck(field_values)

if errors:
    prologue = '<p>' + htmlize('\n'.join(errors)) + '</p><p></p>'
    prologue += '<p>Sorry, precheck failed 😞</p>'
    outcome = {'fraction': 0, "prologuehtml": prologue}
else:
    # For gap filler we don't want to apply proscribedsubstrings to all code, only the gaps as above.
    PARAMS['proscribedsubstrings'] = []
    if PARAMS['useanswerfortests']:
        outcome, test_cases = get_expecteds_from_answer(PARAMS, test_cases, ui_source, answer_field_values)
    
    if test_cases:
        tester = PyTester(PARAMS, test_cases)
        outcome = tester.test_code()
print(json.dumps(outcome))
