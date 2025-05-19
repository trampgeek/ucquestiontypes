import locale
import json
import os
import re
import html
import random

from pytester import PyTester

STANDARD_PYLINT_OPTIONS = ['--disable=trailing-whitespace,superfluous-parens,' + 
                      'too-few-public-methods,consider-using-f-string,useless-return,' + 
                      'unbalanced-tuple-unpacking,too-many-statements,' + 
                      'consider-using-enumerate,simplifiable-if-statement,' + 
                      'consider-iterating-dictionary,trailing-newlines,no-else-return,' + 
                      'consider-using-dict-comprehension,consider-using-generator,' + 
                      'len-as-condition,inconsistent-return-statements,consider-using-join,' + 
                      'singleton-comparison,unused-variable,chained-comparison,no-else-break,' + 
	                  'consider-using-in,useless-object-inheritance,unnecessary-pass,' + 
	                  'reimported,wrong-import-order,wrong-import-position,ungrouped-imports,' + 
                      'consider-using-set-comprehension,no-else-raise,unnecessary-lambda-assignment,' + 
                      'unspecified-encoding,use-dict-literal,consider-using-with,consider-using-min-builtin,' + 
                      'duplicate-string-formatting-argument,consider-using-dict-items,' + 
                      'consider-using-max-builtin,use-a-generator,unidiomatic-typecheck', 
                      '--good-names=i,j,k,n,s,c,_' 
                      ] 


locale.setlocale(locale.LC_ALL, 'C.UTF-8')

KNOWN_PARAMS = {
    'abortonerror': True,
    'allowglobals': False,
    'allownestedfunctions': False,
    'banfunctionredefinitions': True,
    'banglobalcode': True,
    'checktemplateparams': True,
    'dpi': 65,
    'echostandardinput': True,
    'extra': 'None',
    'failhiddenonlyfract': 0,
    'floattolerance': None,
    'forcepylint': False,
    'globalextra': 'None',
    'imagewidth': None,
    'imports': [],
    'isfunction': True,
    'localprechecks': True,
    'maxfunctionlength': 30,
    'maxreturndepth': None,
    'maxprechecks': None,
    'maxnumconstants': 4,
    'maxoutputbytes': 10000,
    'maxstringlength': 2000,
    'norun': False,
    'nostylechecks': False,
    'notest': False,
    'parsonsproblemthreshold': None, # The number of checks before parsons' problem displayed
    'precheckers': ['ruff'],
    'prelude': '',
    'proscribedbuiltins': ['exec', 'eval'],
    'proscribedfunctions': [],
    'proscribedconstructs': ["goto", "while_with_else"],
    'proscribedsubstrings': [],
    'protectedfiles': [],
    'pylintoptions': [],
    'pylintmatplotlib': False,
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
        'fileinput': {
            'onlyallow': []  
        },
        'os': {
            'disallow': ['system', '_exit', '_.*', 'open', 'fdopen', 'listdir']
        },
        'subprocess': {
            'onlyallow': []
        },
        'sys': {
            'disallow': ['_.*']
        },
    },
    'resultcolumns': [], # If not specified, use question's resultcolumns value. See below.
    'ruffoptions': [],
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
    PARAMS = json.loads("""{}""")
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
        if PARAMS['pylintmatplotlib']:
            PARAMS['pylintoptions'].append("--disable=reimported,wrong-import-position,wrong-import-order,unused-import")
        else:
            PARAMS['precheckers'] = []
    if PARAMS['testisbash']:
        print("testisbash is not implemented for Python")
        
    # We use the template parameter for resultcolumns if non-empty.
    # Otherwise use the value from the question, or an equivalent default if that's empty too.
    q_result_columns = """""".strip();
    if PARAMS['resultcolumns'] == []:
        if q_result_columns:
            PARAMS['resultcolumns'] = json.loads(q_result_columns);
        else:
            PARAMS['resultcolumns'] = [['Test', 'testcode'], ['Input', 'stdin'], ['Expected', 'expected'], ['Got', 'got']]


def get_test_cases():
    """Return an array of Test objects from the template parameter TESTCASES"""
    test_cases = [TestCase(test) for test in json.loads("""[{\"testtype\":\"0\",\"testcode\":\"sites_info = {42: (\\\"Christchurch\\\", \\\"Canterbury\\\"), 8472: (\\\"Timaru\\\", \\\"Canterbury\\\")}\\nprint_region_summary(sites_info, regions_from_sites(sites_info))\",\"stdin\":\"\",\"expected\":\"Canterbury\\n      42:  Christchurch                                      \\n    8472:  Timaru\",\"extra\":\"\",\"useasexample\":\"1\",\"display\":\"SHOW\",\"hiderestiffail\":\"0\",\"mark\":\"1.000\"},{\"testtype\":\"0\",\"testcode\":\"sites_info = {71: (\\\"Hokitika\\\", \\\"West Coast\\\"), 30: (\\\"Wellington\\\", \\\"Wellington\\\"), 98: (\\\"Napier\\\", \\\"Hawke's Bay\\\"), 56: (\\\"Graymouth\\\", \\\"West Coast\\\")}\\nprint_region_summary(sites_info, regions_from_sites(sites_info))\",\"stdin\":\"\",\"expected\":\"Hawke's Bay\\n      98:  Napier                                            \\nWellington\\n      30:  Wellington                                        \\nWest Coast\\n      56:  Graymouth                                         \\n      71:  Hokitika\",\"extra\":\"\",\"useasexample\":\"0\",\"display\":\"HIDE_IF_SUCCEED\",\"hiderestiffail\":\"1\",\"mark\":\"1.000\"},{\"testtype\":\"0\",\"testcode\":\"sites_info = {111: (\\\"Taumatawhakatangihangakoauauotamateapokaiwhenuakitanatahu\\\", \\\"New Zealand\\\"), 222: (\\\"Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch\\\", \\\"Wales\\\"), 333: (\\\"Chargoggagoggmanchauggagoggchaubunagungamaugg\\\", \\\"United States\\\"), 444: (\\\"Tweebuffelsmeteenskootmorsdoodgeskietfontein\\\", \\\"South Africa\\\")}\\nprint_region_summary(sites_info, regions_from_sites(sites_info))\",\"stdin\":\"\",\"expected\":\"New Zealand\\n     111:  Taumatawhakatangihangakoauauotamateap...       \\nSouth Africa\\n     444:  Tweebuffelsmeteenskootmorsdoodgeskiet...       \\nUnited States\\n     333:  Chargoggagoggmanchauggagoggchaubunagu...       \\nWales\\n     222:  Llanfairpwllgwyngyllgogerychwyrndrobw...\",\"extra\":\"\",\"useasexample\":\"0\",\"display\":\"HIDE_IF_SUCCEED\",\"hiderestiffail\":\"1\",\"mark\":\"1.000\"},{\"testtype\":\"0\",\"testcode\":\"sites_info = {90: (\\\"Bristol\\\", \\\"United Kingdom\\\"), 54: (\\\"Lyon\\\", \\\"France\\\"), 77: (\\\"Dresden\\\", \\\"Germany\\\"), 81: (\\\"Cambridge\\\", \\\"United Kingdom\\\"), 674353: (\\\"Hanover\\\", \\\"Germany\\\")}\\nprint_region_summary(sites_info, regions_from_sites(sites_info))\",\"stdin\":\"\",\"expected\":\"France\\n      54:  Lyon                                              \\nGermany\\n      77:  Dresden                                           \\n  674353:  Hanover                                           \\nUnited Kingdom\\n      81:  Cambridge                                         \\n      90:  Bristol\",\"extra\":\"\",\"useasexample\":\"0\",\"display\":\"HIDE\",\"hiderestiffail\":\"1\",\"mark\":\"1.000\"}]""")]
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
    while len(lines) > 1 and original == lines: # Make sure the order changes!
        random.shuffle(lines)
    return '\n'.join(lines)
    
def get_answer():
    """Return the sample answer"""
    answer_json = """{\"answer_code\":[\"def limited_string(string, max_len):\\n    \\\"\\\"\\\" Takes a string parameter and returns that string truncated if necessary\\n        to fit in a maximum field width of max_len.\\n        If the string is more than max_len characters long\\n        returns the first (max_len - 3) characters of s with '...' appended.\\n        Otherwise the whole string is returned.\\n    \\\"\\\"\\\"\\n    if len(string) > max_len:\\n        string = string[:max_len-3] + '...'\\n    return string\\n\\n\\ndef regions_from_sites(site_info):\\n    \\\"\\\"\\\" Takes a dictionary that maps from site_ids to (site_name, site_region) tuples\\n    and returns a dictionary where the keys are region name string and the values\\n    are lists of site_ids in those regions.\\n    The site names should appear in the same order as they do in the site_info dictionary.\\n    \\\"\\\"\\\"\\n    result = dict()\\n    for site_id, info in site_info.items():\\n        name, region = info\\n        if region in result:\\n            result[region].append(site_id)\\n        else:\\n            result[region] = [site_id]\\n    return result\\n\\n\\ndef print_region_summary(site_info, region_info):\\n    \\\"\\\"\\\" Prints out the info about sites in each region.\\n    Regions should be sorted alphabetially by region name string\\n    whereas sites should be sorted by site_id\\\"\\\"\\\"\\n    for region in sorted(region_info.keys()):\\n        print(region)\\n        site_id_list = region_info[region]\\n        for site_id in sorted(site_id_list):\\n            name, region = site_info[site_id]\\n            name = limited_string(name, 40)\\n            print(f'{site_id:8}:  {name:50}')\"],\"test_code\":[\"\"],\"show_hide\":[\"\"],\"prefix_ans\":[\"1\"]}""".strip()
    try:
        answer = json.loads(answer_json)['answer_code'][0]
    except:
        answer = answer_json  # Assume this is the original solution
    return answer
    
def process_global_params():
    """Plug into the PARAMS variable all the "global" parameters from
       the question and its answer (as distinct from the template parameters).
    """
    PARAMS['STUDENT_ANSWER'] = """def limited_string(string, max_len):
    \"\"\" Takes a string parameter and returns that string truncated if necessary
        to fit in a maximum field width of max_len.
        If the string is more than max_len characters long
        returns the first (max_len - 3) characters of s with '...' appended.
        Otherwise the whole string is returned.
    \"\"\"
    if len(string) > max_len:
        string = string[:max_len-3] + '...'
    return string


def regions_from_sites(site_info):
    \"\"\" Takes a dictionary that maps from site_ids to (site_name, site_region) tuples
    and returns a dictionary where the keys are region name string and the values
    are lists of site_ids in those regions.
    The site names should appear in the same order as they do in the site_info dictionary.
    \"\"\"
    result = dict()
    for site_id, info in site_info.items():
        name, region = info
        if region in result:
            result[region].append(site_id)
        else:
            result[region] = [site_id]
    return result


def print_region_summary(site_info, region_info):
    \"\"\" Prints out the info about sites in each region.
    Regions should be sorted alphabetially by region name string
    whereas sites should be sorted by site_id\"\"\"
    for region in sorted(region_info.keys()):
        print(region)
        site_id_list = region_info[region]
        for site_id in sorted(site_id_list):
            name, region = site_info[site_id]
            name = limited_string(name, 40)
            print(f'{site_id:8}:  {name:50}')""".rstrip() + '\n'
    PARAMS['SEPARATOR'] = "#<ab@17943918#@>#"
    PARAMS['IS_PRECHECK'] = "0" == "1"
    PARAMS['QUESTION_PRECHECK'] = 1 # Type of precheck: 0 = None, 1 = Empty etc
    PARAMS['ALL_OR_NOTHING'] = "1" == "1" # Whether or not all-or-nothing grading is being used
    PARAMS['GLOBAL_EXTRA'] = """\n"""
    PARAMS['STEP_INFO'] = json.loads("""{"numchecks":0,"numprechecks":0,"fraction":0,"preferredbehaviour":"deferredfeedback","coderunnerversion":"2025021300","graderstate":""}""")
    answer = get_answer()
    if answer:
        if PARAMS['STUDENT_ANSWER'].strip() == answer.strip():
            PARAMS['AUTHOR_ANSWER'] = "<p>Your answer is an <i>exact</i> match with the author's solution.</p>"
        else:
            with open("__author_solution.html") as file:
                PARAMS['AUTHOR_ANSWER'] = (file.read().strip() % html.escape(answer))
            PARAMS['AUTHOR_ANSWER_SCRAMBLED'] = ''
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
    new_params['STUDENT_ANSWER'] = get_answer()
    new_params['resultcolumns'] = [['Test', 'testcode'], ['Got', 'got']]  # Ensure we have a Got column.
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
        outcome['prologuehtml'] = '<pre class="ace-highlight-code" style="display:none"></pre>'  # Kick filter into life
        feedback = PARAMS['AUTHOR_ANSWER']
    if feedback:
        if 'epiloguehtml' in outcome:
            if outcome['epiloguehtml'].strip():
                outcome['epiloguehtml'] += '<br>'
        else:
            outcome['epiloguehtml'] = ''
        outcome['epiloguehtml'] += f'<div style="background-color: #f4f4f4">{feedback}</div>'
print(json.dumps(outcome))
