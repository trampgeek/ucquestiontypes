""" The prototype template for a python gap-filler.
"""

import subprocess, sys, json, re, html, ast

CHECK_ONLY = 0
PRECHECK_ONLY = 1
BOTH = 2

KNOWN_PARAMS = {
    "gapfiller_ui_source": "globalextra",
    'checksyntax': True,
    'proscribedsubstrings': [";", "print"],
    'proscribedconstructs': [],
    'requiredconstructs': [],
    'maxfieldlength': 50,
    'maxnumlines': 5,  # Relevant only for text areas
    'useanswerfortests': False,
    'prefix': '',
    'extra': 'posttest',
    'echostdin': True,
    'suffix': '',
    'stripwhitespace': True
}

FAKE_INPUT = """
REAL_INPUT = input
def input(prompt=''):
    '''Version of input func that echos input to output'''
    print(prompt, end='')
    line = REAL_INPUT()
    print(line)
    return line
"""

PARAMS = json.loads("""{{ QUESTION.parameters | json_encode | e('py') }}""")
unknown_params = set(PARAMS.keys()) - set(KNOWN_PARAMS.keys())
filtered_params = [param for param in unknown_params if not param.startswith('_')]
if filtered_params:
    print("Unexpected template parameter(s):", list(sorted(filtered_params)))
for param, default in KNOWN_PARAMS.items():
    if param not in PARAMS:
        PARAMS[param] = default
    
PARAMS['IS_PRECHECK'] = "{{ IS_PRECHECK }}" == "1"
PARAMS['ALL_OR_NOTHING'] = json.loads("""{{ QUESTION.allornothing}}""")
        
        
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
        
        
class TestResults:
    """Manage the set of test results in order to build a test result table"""
    
    def __init__(self, tests):
        self.show_test_col = any(test.testcode.strip() != '' for test in tests)
        self.show_input_col = any(test.stdin.strip() != '' for test in tests)
        self.all_correct = True
        self.hiding_rest = False
        self.hidden_fails = 0
        self.mark = 0
        self.total_avail = 0
        header = []
        self.column_formats = []
        if self.show_test_col:
            header.append('Test')
            self.column_formats.append('%h')
        if self.show_input_col:
            header.append('Input')
            self.column_formats.append('%s')
    
        header += ["Expected", "Got", "iscorrect", "ishidden"]
        self.column_formats += ['%s', '%s']
        self.result_table = [header]
        
    def is_empty(self):
        """True if the only result table row is the header"""
        return len(self.result_table) == 1
        
    def add_row(self, test, source, output, field_values):
        """Add a row with given info"""
        global splitter_used
        row = []
        if self.show_test_col:
            test_col = htmlize(test.testcode)
            if source == 'test0':
                test_col = insert_fields(test_col, field_values, splitter_used, True)
            row.append(test_col)
        if self.show_input_col:
            row.append(test.stdin)
        if PARAMS['stripwhitespace']:
            correct = output.strip() == test.expected.strip()
        else:
            correct = output == test.expected
        hidden = test.display == 'HIDE' or self.hiding_rest or (test.display == 'HIDE_IF_SUCCEED' and correct)
        row += [test.expected, output, correct, hidden]
        self.result_table.append(row)
        self.total_avail += test.mark
        if correct:
            self.mark += test.mark
        else:
            self.all_correct = False
            if hidden:
                self.hidden_fails += 1
        self.hiding_rest = test.hiderestiffail and not correct
        
    def get_fraction(self):
        return self.mark / self.total_avail if self.total_avail != 0 else 1
        
    def get_results(self):
        return self.result_table
        
    def get_column_formats(self):
        return self.column_formats
    
        
def get_test_cases():
    """Return an array of Test objects from the template parameter TESTCASES"""
    test_cases = [TestCase(test) for test in json.loads("""{{ TESTCASES | json_encode | e('py') }}""")]
    return test_cases


def constructs_used(code_snippet):
    """Return a set of all constructs encountered in the given code snippet,
       which must a syntactically valid bit of Python
    """
    constructs_seen = set()
    class ConstructFinder(ast.NodeVisitor):
        def visit_Assert(self, node):
            constructs_seen.add('assert')
            self.generic_visit(node)
        def visit_Raise(self, node):
            constructs_seen.add('raise')
            self.generic_visit(node)
        def visit_Lambda(self, node):
            constructs_seen.add('lambda')
            self.generic_visit(node)
        def visit_Import(self, node):
            constructs_seen.add('import')
            self.generic_visit(node)
        def visit_ImportFrom(self, node):
            constructs_seen.add('import')
            self.generic_visit(node)
        def visit_For(self, node):
            constructs_seen.add('for')
            self.generic_visit(node)
        def visit_While(self, node):
            constructs_seen.add('while')
            self.generic_visit(node)
        def visit_Comprehension(self, node):
            constructs_seen.add('comprehension')
            self.generic_visit(node)
        def visit_ListComp(self, node):
            constructs_seen.add('listcomprehension')
            self.generic_visit(node)
        def visit_SetComp(self, node):
            constructs_seen.add('setcomprehension')
            self.generic_visit(node)
        def visit_DictComp(self, node):
            constructs_seen.add('dictcomprehension')
            self.generic_visit(node)
        def visit_Subscript(self, node):
            constructs_seen.add('subscript')
        def visit_Slice(self, node):
            constructs_seen.add('slice')
        def visit_If(self, node):
            constructs_seen.add('if')
            self.generic_visit(node)
        def visit_Break(self, node):
            constructs_seen.add('break')
            self.generic_visit(node)
        def visit_Continue(self, node):
            constructs_seen.add('continue')
            self.generic_visit(node)
        def visit_Try(self, node):
            constructs_seen.add('try')
            self.generic_visit(node)
        def visit_TryExcept(self, node):
            constructs_seen.add('try')
            constructs_seen.add('except')
            self.generic_visit(node)
        def visit_TryFinally(self, node):
            constructs_seen.add('try')
            constructs_seen.add('finally')
            self.generic_visit(node)
        def visit_ExceptHandler(self, node):
            constructs_seen.add('except')
            self.generic_visit(node)
        def visit_With(self, node):
            constructs_seen.add('with')
            self.generic_visit(node)
        def visit_Yield(self, node):
            constructs_seen.add('yield')
            self.generic_visit(node)
        def visit_YieldFrom(self, node):
            constructs_seen.add('yield')
            self.generic_visit(node)
        def visit_Return(self, node):
            constructs_seen.add('return')
            self.generic_visit(node)

    tree = ast.parse(code_snippet)
    visitor = ConstructFinder()
    visitor.visit(tree)
    return constructs_seen

    

# Expand the given code by inserting the given fields into the
# given code, after splitting it with the given regular expression.
# If highlight is true, the inserted text is wrapped in a <span> element
# with a special blue-grey background.
def insert_fields(code, fields, splitter=r"\{\[.*?\]\}", highlight=False):
    global splitter_used
    splitter_used = splitter # Hack - save for re-use when displaying tests
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
    
    
def run_one_test(prog, stdin):
    with open("prog.py", "w") as src:
        print(prog, file=src)
    try:
        output = subprocess.check_output(
            ["python3", "prog.py"],
            input=stdin,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=3,
        )
    except subprocess.CalledProcessError as e:
        output = e.output + '\n' if e.output else ''
    except subprocess.TimeoutExpired:
        output = "*** Timeout error ***"
    return output


def snip(field):
    """Return the given field, snipped to a max of 10 chars"""
    return field if len(field) <= 10 else field[0:10] + '...'


def precheck(field_values):
    """Checks field lengths and ensure no proscribed strings present"""
    errors = []
    all_constructs = set()
    for field in field_values:
        if len(field) > PARAMS['maxfieldlength']:
            errors.append(f"Field '{snip(field)}' is too long. Maximum length is {PARAMS['maxfieldlength']}")
        if len(field.rstrip().splitlines()) > PARAMS['maxnumlines']:
            errors.append(f"Field '{snip(field)}' has too many lines. Maximum is {PARAMS['maxnumlines']}")
        for bad in PARAMS['proscribedsubstrings']:
            if bad in field:
                errors.append(f"Field '{snip(field)}' contains the banned string '{bad}'")
                
        if PARAMS['checksyntax']:
            try:
                constructs = constructs_used(field)
                all_constructs = all_constructs.union(constructs)
                
                for bad in PARAMS['proscribedconstructs']:
                    if bad in constructs:
                        errors.append(f"Field '{snip(field)}' contains the banned constructs '{bad}'")
            except (SyntaxError, ValueError) as e:
                errors.append(f"Syntax error in field '{snip(field)}'")
            
        if not errors:
            for good in PARAMS['requiredconstructs']:
                if good not in all_constructs:
                    errors.append(f"You must use a {good} somewhere")
                
    return errors


def htmlize(message):
    """An html version of the given error message"""
    return '<pre>' + html.escape(message) + '</pre>' if message else ''
    
def set_expected(source, test):
    """Plug the expected answer into the given test by running the
       sample answer. Does nothing if useanswerfortests is False
       or if the expected field of the test is non-empty.
    """
    if not PARAMS['useanswerfortests'] or test.expected.rstrip():
        return
    field_values = json.loads(""" {{ QUESTION.answer | e('py') }}""")
    prog = make_prog_to_run(source, test, field_values)
    output = run_one_test(prog, test.stdin)
    test.expected = output
    
def make_prog_to_run(source, test, field_values):
    raw_prog = PARAMS['prefix']
    if PARAMS['echostdin']:
        raw_prog += FAKE_INPUT
    if PARAMS['extra'] == 'pretest' and test.extra:
        raw_prog += test.extra + '\n'
    if source and source == 'test0':
        raw_prog += test.testcode
    else:
        raw_prog += """{{ QUESTION.globalextra | e('py')}}"""
    if PARAMS['extra'] == 'posttest' and test.extra:
        raw_prog += '\n' + test.extra + '\n'
    prog = insert_fields(raw_prog, field_values)
    if source != 'test0':
        prog += '\n' + test.testcode
    prog += '\n' + PARAMS['suffix']
    return prog

def run_tests_prechecked(tests, field_values):
    """Run the given set of tests, knowing there are no precheck errors.
       Return the outcome dictionary.
    """
    ui_params = json.loads("""{{ QUESTION.uiparameters | json_encode | e('py') }}""")
    if ui_params and 'ui_source' in ui_params:
        source = ui_params['ui_source']
    else:
        source = 'globalextra'
    is_precheck = PARAMS['IS_PRECHECK']
    table = TestResults(tests)

    for test in tests:
        if is_precheck and test.testtype not in [PRECHECK_ONLY, BOTH]:
            continue
        if not is_precheck and test.testtype not in [CHECK_ONLY, BOTH]:
            continue
        prog = make_prog_to_run(source, test, field_values)
        output = run_one_test(prog, test.stdin)
        set_expected(source, test)
        table.add_row(test, source, output, field_values)
        
    if PARAMS['ALL_OR_NOTHING']:
        fraction = 1 if table.all_correct else 0
    else:
        fraction = table.get_fraction()
    outcome = {'fraction': fraction}
    if not table.is_empty():
        outcome['testresults'] = table.get_results()
        outcome['columnformats'] = table.get_column_formats()
        outcome['showdifferences'] = True

    if table.all_correct:
        if is_precheck:
            outcome['epiloguehtml'] = '<p>Precheck passed 😊 </p>'
    else:
        if table.hidden_fails:
            outcome['epiloguehtml'] = '<p>One or more hidden tests failed.</p>'
        else:
            outcome['epiloguehtml'] = ''
        if PARAMS['ALL_OR_NOTHING']:
            outcome['epiloguehtml'] += '<p>Sorry, you must pass all tests to earn any marks 😞.</p>'
        
    return outcome


def run_tests():
    """Run all tests. Do prechecks first then pass on to run_tests_prechecked"""
    tests = get_test_cases()
    field_values_raw = json.loads(""" {{ STUDENT_ANSWER | e('py') }}""")
    field_values = [field.strip() for field in field_values_raw]
    errors = precheck(field_values)
    if errors:
        prologue = '<p>' + htmlize('\n'.join(errors)) + '</p><p></p>'
        prologue += '<p>Sorry, precheck failed 😞</p>'
        outcome = {'fraction': 0, "prologuehtml": prologue}
    else:
        # Can't skip this when prechecking as there may be prechecked tests
        outcome = run_tests_prechecked(tests, field_values)

    print(json.dumps(outcome))

run_tests()
