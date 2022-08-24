import html
import locale
import json
import os
import re
import sys
import py_compile

from pytester import PyTester

locale.setlocale(locale.LC_ALL, 'C.UTF-8')

# NOTE: the following are most of the parameters from the python3_stage1
# question type, included here so that the standard python3_stage1 support
# files can be used without changed. However, only the ones prefixed by
# '*' can be used in this question type (without the asterisk).

KNOWN_PARAMS = {
    'abortonerror': True,
    'allowglobals': True,
    'allownestedfunctions': False,
    'checktemplateparams': True,
    'echostandardinput': True,
    '*extra': 'None',
    '*floattolerance': None,
    'globalextra': 'None',
    '*imagewidth': None,
    'imports': [],
    'isfunction': False,
    'maxfunctionlength': 30,
    '*maxfieldlength': None,
    'maxnumconstants': 4,
    'maxoutputbytes': 10000,
    '*maxstringlength': 2000,
    'norun': False,
    'nostylechecks': True,
    'notest': False,
    '*parsegaps': True,
    'precheckers': ['pylint'],
    '*prelude': '',
    '*proscribedbuiltins': ['exec', 'eval'],
    'proscribedfunctions': [],
    'proscribedconstructs': [],
    '*proscribedsubstrings': [";", "print", "import"],
    'pylintoptions': [],
    'requiredconstructs': [],
    'requiredfunctiondefinitions': [],
    'requiredfunctioncalls': [],
    '*requiredsubstrings': [],
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
    '*strictwhitespace': True,
    'stripmain': False,
    'stripmainifpresent': False,
    'testisbash': False,
    '*timeout': 5,
    '*totaltimeout': 50,
    'suppresspassiveoutput': False,
    '*useanswerfortests': False,
    '*usesmatplotlib': False,
    '*usesnumpy': False,
    'usesubprocess': False,
    'warnifpassiveoutput': False,
}

GLOBAL_ERRORS = []


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
    global PARAMS, GLOBAL_ERRORS
    PARAMS = json.loads("""{{ QUESTION.parameters | json_encode | e('py') }}""")
    checktemplateparams = PARAMS.get('checktemplateparams', True)

    # Check for parameters that aren't allowed
    if checktemplateparams:
        author_params = set(PARAMS.keys())
        allowed_params = set(key[1:] for key in KNOWN_PARAMS.keys() if key.startswith('*'))
        unknown_params = author_params - allowed_params
        filtered_params = [param for param in unknown_params if not param.startswith('_')]
        if filtered_params:
            GLOBAL_ERRORS.append(f"Unexpected template parameter(s): {list(sorted(filtered_params))}")

    # Now merge all the KNOWN_PARAMS into PARAMS
    for param_name, default in KNOWN_PARAMS.items():
        if param_name.startswith('*'):
            param_name = param_name[1:]
        if param_name in PARAMS:
            param = PARAMS[param_name]
            if type(param) != type(default) and default is not None:
                GLOBAL_ERRORS.append(f"Template parameter {param_name} has wrong type (expected {type(default)})")
        else:
            PARAMS[param_name] = default;

    if PARAMS['extra'] == 'stdin':
        PARAMS['stdinfromextra'] = True
    if PARAMS['runextra']:
        PARAMS['extra'] = 'pretest'  # Legacy support
    if PARAMS['timeout'] < 2:
        PARAMS['timeout'] = 2  # Allow 1 extra second freeboard


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
        outcome[
            'prologuehtml'] = "Unexpected error ({}) extracting testcase expecteds from sample answer output".format(e)
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
        outcome['prologuehtml'] = "<h2>ERROR IN QUESTION'S SAMPLE ANSWER. PLEASE REPORT</h2>\n" + outcome[
            'prologuehtml']
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
    global GLOBAL_ERRORS
    bits = re.split(splitter, code)
    if len(bits) != len(fields) + 1:
        GLOBAL_ERRORS.append("Richard has goofed. Please report")
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
    """Gets what should be considered the 'student answer'. If global extra
       is being used as the UI source, the student answer is the global
       extra with all the various gaps filled in. The tests then follow that
       code. However, if test0 is the UI source, the student answer is empty
       (apart from a possibly spurious module docstring) as the tests will
       all have had the test0 gap contents plugged into them too.
    """
    if ui_source == 'test0':
        return "'''docstring'''"
    else:
        return insert_fields("""{{ QUESTION.globalextra | e('py')}}""", field_values)


def snip(field, maxlen=10):
    """Return the given field, snipped to a max of maxlen chars"""
    return field if len(field) <= maxlen else field[0:maxlen] + '...'


def fields_precheck(field_values):
    """Checks field lengths (legacy) and no proscribed strings present in fields.
       Also do a syntax check if the 'parsegaps' parameter is true.
    """
    errors = []
    all_constructs = set()
    for field in field_values:
        if PARAMS['maxfieldlength'] is not None and len(field) > PARAMS['maxfieldlength']:
            errors.append(f"Field '{snip(field)}' is too long. Maximum length is {PARAMS['maxfieldlength']}")
        for bad in PARAMS['proscribedsubstrings']:
            if bad in field:
                errors.append(f"Field '{snip(field)}' contains the banned string '{bad}'")
        if PARAMS['parsegaps']:
            with open('__gap.py', 'w') as outfile:
                outfile.write(field)
            try:
                py_compile.compile('__gap.py', doraise=True)
            except Exception as e:
                errors.append(f"Syntax error in field '{snip(field, 30)}'")
            for filename in ['__gap.py', '__gap.pyc']:
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass
    for reqd in PARAMS['requiredsubstrings']:
        if not any(reqd in field for field in field_values):
            errors.append(f"Required substring '{reqd}' not found")
    return errors


def htmlize(message):
    """An html version of the given error message"""
    return '<pre>' + html.escape(message) + '</pre>' if message else ''


def process_global_params(ui_source, field_values):
    """Plug the globals STUDENT_ANSWER, IS_PRECHECK and QUESTION_PRECHECK into the global PARAMS """
    PARAMS['STUDENT_ANSWER'] = get_student_answer(ui_source, field_values) + '\n'
    PARAMS['SEPARATOR'] = "#<ab@17943918#@>#"
    PARAMS['IS_PRECHECK'] = "{{ IS_PRECHECK }}" == "1"
    PARAMS['QUESTION_PRECHECK'] = {{QUESTION.precheck}}  # Type of precheck: 0 = None, 1 = Empty etc
    PARAMS[
        'ALL_OR_NOTHING'] = "{{ QUESTION.allornothing }}" == "1"  # Whether or not all-or-nothing grading is being used
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

if GLOBAL_ERRORS:
    errors = GLOBAL_ERRORS[:]
else:
    errors = fields_precheck(field_values)

if errors:
    prologue = '<p>' + htmlize('\n'.join(errors)) + '</p><p></p>'
    prologue += '<p>Sorry, precheck failed 😞</p>'
    outcome = {'fraction': 0, "prologuehtml": prologue}
else:
    # For gap filler we don't want to apply proscribedsubstrings to all code, only the gaps as above.
    # We also turn off all standard style checks.
    PARAMS['proscribedsubstrings'] = []
    PARAMS['nostylechecks'] = True
    PARAMS['stylechecks'] = False  # For the future!
    if PARAMS['useanswerfortests']:
        outcome, test_cases = get_expecteds_from_answer(PARAMS, test_cases, ui_source, answer_field_values)

    if test_cases:
        tester = PyTester(PARAMS, test_cases)
        outcome = tester.test_code()
print(json.dumps(outcome))
