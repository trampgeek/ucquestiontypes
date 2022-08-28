"""The template for for a programming contest problem, which takes a .zip file
   in either domjudge import or domjudge export format as a support file.
   It runs all the "write a program" tests present in the .zip file in the
   language chosen by the submitter. As a constraint, the total execution time
   cannot exceed the limit set on the Jobe server (typically 30 seconds).
"""

import subprocess
import re
import json
import os
import sys
import os.path
import urllib.parse
from collections import defaultdict
from enum import Enum
from random import randint
from zipfile import ZipFile

MAX_CELL_ROWS = 20
MAX_CELL_COLS = 65
MAX_STRING_LENGTH = 10000   # Max length of a Data-URI encoded string
MEMLIMIT = 4000000          # Max k-bytes for stack and data segments
TICKS_PER_SEC = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
PID = os.getpid()
VALIDATOR_FILENAME = 'validator_from_archive.zip'

KNOWN_PARAMS = {
    "answer_language": "cpp",   # Used only by validator - ignore it
    "cflags": "-std=gnu17 -w -O2",
    "cppflags": "-std=gnu++17 -w -O2",
    "cldflags": "-lm",
    "float_tolerance": None,   # Hacked up attempt to mimic domjudge
    "fsizelimit": 8192,        # Maximum output (incl. stdout) file size (512byte blocks)
    "pertest_timeout": None,   # Timeout (cpu secs) on each test (actual default is 10 secs).
    "problem_spec_filename": "", # Name of file containing problem spec
    "programming_contest_problem": True,  # We wouldn't be here without this one!
    "result_table_header": 'Sample test case results (all other tests are hidden)',   # Header to display above result table.
    "show_first_fail": False,  # True to display the first failing test.
    "show_all_tests": False,    # True to display all tests
    "show_spoiler": True,       # True to display a spoiler button for first failing test
    "show_tests": [],  # Numbers of test cases to be displayed in the result table
    "total_timeout": 120,       # Maximum permitted time budget (cpu secs).
    "validator_zip_filename": "",
    "tests_zip_filename": ""
}

class BadTestData(Exception): pass

class ValidatorBuildFailure(Exception): pass

class ValidatorFailure(Exception):  pass


class State(Enum):
    correct = 0
    compile_error = 1
    runtime_error = 2
    wrong_answer = 3
    timeout = 4
    time_budget_exceeded = 5
    bad_test_data = 6


SUMMARY_MESSAGES = {
    State.correct: "Correct. Well done  😊",
    State.compile_error: "Compile error",
    State.runtime_error: "Runtime error",
    State.wrong_answer: "Sorry, wrong answer 😞",
    State.timeout: "One of your tests timed out",
    State.time_budget_exceeded: """Testing aborted due to total time budget being exceeded.
Sorry but this server doesn't permit full testing of your answer.
This is probably not your fault.""",
    State.bad_test_data: "Answer cannot be tested"}
    
def process_cpu_time():
    """Return the process CPU time in secs of this process and its various
       children. The reference is arbitary, so only differences are meaningful.
       We use this rather than perf_counter as perf_counter measures wall clock
       time but our time budget in runguard is CPU secs.
    """
    with open(f"/proc/{PID}/stat") as infile:
        cpu_times = map(int, infile.readline().split()[14:18])
        return sum(cpu_times) / TICKS_PER_SEC

def htmlise(s):
    """Convert newlines to <br> and tweak '<'"""
    return s.replace("<", "&lt;").replace("\n", "<br>")


class TestResult:
    def __init__(self, state, output):
        self.state = state
        self.output = output


class Results:
    """A wrapper around the ResultTable, with the addition of a State attribute.
    """
    def __init__(self, state=State.correct, global_error=''):
        self.table = [['iscorrect', 'TestID', 'Input', 'Expected', 'Got', 'ishidden']]
        self.state = state
        self.failed_hidden = False
        self.global_error = global_error  # Any error message belonging outside the test table (e.g. compile err)

    @staticmethod
    def make_data_url(s):
        if len(s) > MAX_STRING_LENGTH:
            s = s[:MAX_STRING_LENGTH] + ' ... (truncated)'
        s = urllib.parse.quote(s, safe='~()*!.\'')
        return f'<a download="download.txt" target="_blank" href="data:text/plain;charset=utf-8,{s}">Download</a>'

    @staticmethod
    def table_cell(s):
        """Return a string suitable for display in the result table that is being
           displayed using raw html formatting.
           If s is less than MAX_CELL_ROWS lines and each line is less than
           MAX_CELL_COLS in width, s is returned wrapped in a <div> element, with html
           sanitisation). Otherwise the data is made into an html Download data-uri
           link.
        """
        lines = s.splitlines()
        if len(lines) <= MAX_CELL_ROWS and all(len(line) <= MAX_CELL_COLS for line in lines):
            return f'<pre style="background-color:inherit">{htmlise(s)}</pre>'
        else:
            return Results.make_data_url(s)

    def add_row(self, test_num, test_result, stdin, expected, is_hidden):
        """Add to this result table the given test result, given also the test stdin and expected output.
           is_hidden will be used by the CodeRunner renderer to control whether the user sees this row.
        """
        self.state = test_result.state
        is_correct = self.state == State.correct
        if not is_correct and is_hidden:
            self.failed_hidden = True
        self.table.append([is_correct,
                           test_num,
                           Results.table_cell(stdin),
                           Results.table_cell(expected),
                           Results.table_cell(test_result.output),
                           is_hidden])


class JobRunner:
    """The class that handles compiling, running and grading a submissions"""
    FREE_BOARD_SECS = 2   # Number of seconds freeboard to allow for cleaning up, overheads etc.
    # Default timeout, only if pertest_timeout parameter missing and no domjudge-ini timeout
    DEFAULT_PER_TEST_TIMEOUT = 10

    def __init__(self, student_answer, language, params, tests, timeout):
        self.student_answer = student_answer
        self.language = language
        self.params = params
        self.tests = tests
        self.timeout = timeout
        self.exec_command = None
        self.validator = None
        self.setup_validator_if_given()

    def setup_validator_if_given(self):
        """If there is a valid supplied as a zip file, build the validator"""
        validator_zip_filename = self.params.get('validator_zip_filename', None)
        if validator_zip_filename:
            os.mkdir("Validator")
            zipfile = ZipFile(validator_zip_filename)
            zipfile.extractall("Validator")
            zipfile.close()
            cwd = os.getcwd()
            os.chdir('Validator')
            cpp_filenames = [filename for filename in os.listdir() if filename.endswith(".cpp")]
            if os.path.isfile('build'):
                build_result = subprocess.run(['/bin/bash', 'build'],
                                          encoding='utf-8',
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
            elif len(cpp_filenames) == 1:
                build_result = subprocess.run(['/usr/bin/g++', cpp_filenames[0], '-o', 'run'],
                                          encoding='utf-8',
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
            else:
                raise Exception("No build file for validator and no (single) cpp source file")
            os.chdir(cwd)
            if build_result.returncode == 0:
                os.chmod('Validator/run', 0O755)
                self.validator = 'Validator/run'
            else:
                raise ValidatorBuildFailure(build_result.stdout)

    def validator_check(self, test, got):
        """Check the answer using a supplied validator. """
        _, stdin, expected = test
        with open('test_stdin', 'w') as outfile:
            outfile.write(stdin)
        with open('test_expected', 'w') as outfile:
            outfile.write(expected)
        try:
            os.mkdir('validator_feedback')
        except FileExistsError:
            pass
        validator_result = subprocess.run([
            self.validator, 'test_stdin', 'test_expected', 'validator_feedback'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, input=got, encoding='utf-8')
        if validator_result.returncode == 42:
            return True
        elif validator_result.returncode == 43:
            #files = os.listdir('validator_feedback')
            #error_out = 'Validator feedback:'
            #for file in files:
            #    with open('validator_feedback/' + file) as input:
            #        error_out += input.read()
            #        
            #raise ValidatorFailure(f"Validator said 'No' with output {error_out}")
            return False
        else:
            raise ValidatorFailure(f"Validator failed with return code {validator_result.returncode}")

    def match(self, test, got):
        """True iff the expected output is correct.
           If there is a validator for this problem, it is used. Otherwise a simple
           comparison of expected and got is performed after stripping whitespace from
           the end of both and from the end of every line in both. Also, for
           each line, if the template_parameter float_tolerance is not None,
           at attempt is made to compare non-matching lines as floats, within
           the given tolerance. This is a gross hack. ** TODO ** fix me.
        """
        if self.validator:
            return self.validator_check(test, got)
        else:
            _, _, expected = test
            expected_lines = [line.rstrip() for line in expected.rstrip().splitlines()]
            got_lines = [line.rstrip() for line in got.rstrip().splitlines()]
            if len(expected_lines) != len(got_lines):
                return False
            for left, right in zip(expected_lines, got_lines):
                if left != right:
                    if self.params['float_tolerance']:
                        try:
                            fl = float(left)
                            fr = float(right)
                            tol = self.params['float_tolerance']
                            if abs(fl - fr) < tol or abs((fl - fr) / fl) < tol:
                                continue
                        except ValueError:
                            return False
                    return False
            return True

    def test_sequence(self):
        """Return a list of the order in which tests should be performed.
           Namely all sample tests, then all tests listed in show_tests, then
           everything else.
        """
        shows = [i for i in range(len(self.tests)) if self.tests[i][0]]  # All sample tests
        shows += self.params['show_tests']
        rest = sorted(set(range(0, len(self.tests))) - set(shows))
        return shows + rest

    def get_output(self, stdoutfile, stderrfile):
        """Read the subprocesses standard output and standard error files"""
        output = ''
        with open(stdoutfile) as out:
            output += out.read()
        with open(stderrfile) as err:
            stderr_output = err.read()
            if stderr_output:
                spacer = '\n====Output prior to error====\n' if output else ''
                output = stderr_output + spacer + output
        return output

    def run_one_test(self, stdin, remaining_secs, pertest_timeout):
        """ Run a single test of the compiled ready-to-run program
            using the given exec_command. remaining_secs is the total CPU time
            remaining. The job will be run with a time out pertest_timeout or
            remaining_secs, whichever is the smaller. All times are CPU times,
            not wall clock time (since runguard uses ulimit -t which is CPU time).
            If the test times out at pertest_timeout, it is considered a failure.
            However, if remaining_secs  is less than that and the job times out, 
            it is considered a question-type failure as the total time budget
            was insufficient for testing. In this case InsufficientTimeBudget is
            raised.
            return value is a TestResult object in which the State is 'correct' if
            no runtime errors occurred. This might later change to wrong_answer when
            the output is checked.
            Use subprocess.run with output to files in order that ulimit filesize
            works on stdout and stderr.
        """
        output = ''
        timeout = int(min(remaining_secs, pertest_timeout))
        if timeout <= 0:
            return TestResult(State.time_budget_exceeded, "*** Time budget exceeded ***")
        t_start = process_cpu_time()
        state = State.correct  # In this context, 'correct' means the run didn't break
        cmd = ' '.join(self.exec_command)
        fsizelimit = self.params['fsizelimit']
        bash_cmd = f"ulimit -s unlimited; ulimit -c 0; ulimit -v {MEMLIMIT}; ulimit -t {timeout}; ulimit -f {fsizelimit}; {cmd}"
        try:
            with open('__stdout__.txt', 'w') as output:
                with open('__stderr__.txt', 'w') as err_output:
                    subprocess.run(
                        bash_cmd,
                        input=stdin,
                        stdout=output,
                        stderr=err_output,
                        universal_newlines=True,
                        check=True,
                        shell=True)

        except subprocess.CalledProcessError as e:
            output = self.get_output('__stdout__.txt', '__stderr__.txt')
            state = State.runtime_error
            spacer = '\n' if output else ''
            if output.startswith('Killed'):
                # Job killed by bash, almost certainly due to ulimit.
                # We assume that if wall clock time has run out, that the ulimit
                # that was hit was cpu time. However, ulimit can actually kill
                # a job due to CPU time *before* the wall clock time has reached
                # (evidenced by Java). Hence the cautious classification in
                # the following.
                if process_cpu_time() - t_start >= timeout:
                    # Job timed out. Decide if this is a test case timeout
                    #  (user's fault) or total time budget exceeded (our fault).
                    if timeout >= pertest_timeout:
                        state = State.timeout
                        output = output.replace('Killed', '*** TIMEOUT ***')
                    else:
                        state = State.time_budget_exceeded
                elif e.returncode == (128 + 9): # Always true? Dunno!
                    output = output.replace('Killed', '*** Killed by timeout or excessive output ***')
                elif e.returncode > 128:
                    # Why did we get killed??
                    output = output.replace('Killed', f'*** Killed by signal {e.returncode - 128} ***')
                else:
                    output = output.replace('Killed', f'*** Killed with returncode = {e.returncode} ***')
            elif output.endswith('MemoryError'):
                output = output.replace('MemoryError', '*** Memory limit exceeded ***')
            elif e.returncode <= 128:
                # Probably program exited with its own error code
                output += spacer + f'*** Program exited with return code of {e.returncode} ***'
            else:  # e.returncode > 128 - a signal
                output += spacer + f"*** Program failed with signal {e.returncode - 128} ***"
            if state != state.correct and output:
                output += "\nFurther testing aborted"
            
        else:
            output = self.get_output('__stdout__.txt', '__stderr__.txt')

        return TestResult(state, output)

    def run_all_tests(self, end_time):
        """Run the compiled program (defined by self.exec_command, set by previous compile)
           on all tests passed to the constructor.
           Must complete by given end_time (which is measured in CPU secs,
           not wall clock time), which is the value returned by process_cpu_time.
           Return value is a Results object (q.v.)
        """

        if self.params['pertest_timeout'] is None:
            if self.timeout is not None:
                self.params['pertest_timeout'] = self.timeout
            else:
                self.params['pertest_timeout'] = JobRunner.DEFAULT_PER_TEST_TIMEOUT
        results = Results()

        for i in self.test_sequence():
            is_sample, stdin, expected = self.tests[i]
            secs_remaining = end_time - process_cpu_time()
            pertest_timeout = self.params['pertest_timeout']
            test_result = self.run_one_test(stdin, secs_remaining, pertest_timeout)
            if test_result.state == State.correct and not self.match(self.tests[i], test_result.output):
                test_result.state = State.wrong_answer
            is_shown = is_sample or self.params['show_all_tests'] or i in self.params['show_tests'] or (
                self.params['show_first_fail'] and test_result.state != State.correct)
            #test_result.output += f"\n[Job was run with {secs_remaining:.2f} secs remaining]"
            results.add_row(i, test_result, stdin, expected, not is_shown)
            if test_result.state != State.correct:
                break  # Lazy evaluation
        return results

    def compile(self, filename):
        """Compile C, C++, C# and Java (and Python, but it's almost a no-op).
           Return the output from the compile (empty if a clean compile)
           and set self.exec_command to the command required to execute
           the
        """
        basename = '.'.join(filename.split('.')[:-1])

        if self.language == 'c':
            cflags = self.params['cflags']
            cldflags = self.params['cldflags']
            command = f"gcc {cflags} -o {basename} {filename} {cldflags}"
            compile_result = subprocess.run(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
            self.exec_command = [f"./{basename}"]

        elif self.language == 'cpp':
            cppflags = self.params['cppflags']
            command = f"g++ {cppflags} -o {basename} {filename}"
            compile_result = subprocess.run(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
            self.exec_command = [f"./{basename}"]

        elif self.language == 'java':
            compile_result = subprocess.run(
                ['javac', "-J-Xss64m", "-J-Xmx4g", filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
            self.exec_command = ["java", "-Xss64m", "-Xmx512m", basename]
            
        elif self.language == 'csharp':
            compile_result = subprocess.run(	
                ['mcs', filename],	
                stdout=subprocess.PIPE,	
                stderr=subprocess.STDOUT,	
                universal_newlines=True)	
            self.exec_command = ["mono", basename + '.exe']	
            
        else:  # Python doesn't need a compile phase
            compile_result = None
            self.exec_command = ["python3", filename]

        compile_output = compile_result.stdout if compile_result else ''
        return compile_output

    def make_executable(self):
        """Try to compile self.student_answer in language self.language.
           Return value is the empty string if all goes well, and in that
           case the value self.exec_command has the command to run the executable.
           If there's any compile error, return the compiler output.
        """
        language_extension_map = {'c': 'c', 'cpp': 'cpp', 'java': 'java', 'python3': 'py', 'csharp': 'cs'}
        if self.language not in language_extension_map.keys():
            raise Exception('Error in question. Unknown/unexpected language ({})'.format(self.language))

        if self.language == 'java':
            # Need to determine public class name in order to name output file. Sigh.
            # The best I can be bothered to do is to use a regular expression match.
            match_obj = re.search(r'public\s+class\s+([_a-zA-Z][_a-zA-Z0-9]*)',
                                  self.student_answer, re.DOTALL | re.MULTILINE)
            if match_obj is None:
                raise Exception("Unable to determine class name. Does the file include 'public class name'?")
            classname = match_obj.group(1)
            filename = classname + '.java'
        else:
            filename = 'prog.' + language_extension_map[self.language]

        # Write the student code to a file

        with open(filename, "w") as src:
            print(self.student_answer, file=src)

        compile_output = self.compile(filename)
        return compile_output

    def compile_and_run(self):
        """Try to compile and execute the given student answer in the given
           language.
           Return a Result object.
        """

        # Compute the time by which we must be done (less FREE_BOARD SECS for cleaning up)
        start_time = process_cpu_time()
        end_time = start_time + self.params['total_timeout'] - self.FREE_BOARD_SECS
        try:
            error_message = self.make_executable()
        except Exception as e:
            error_message = str(e)

        if error_message:
            result = Results(State.compile_error, error_message)
        else:
            # Compile OK: unzip the expected support file and try running all the tests.
            result = self.run_all_tests(end_time)

        return result


def tests_and_timeout_from_zip(zipfilename):
    """Return a tuple consisting of the timeout value from the domjudge.ini file
       (if present - None if not) and a list of (isSample, inputdata, outputdata)
       tuples of test data from the given zipfile. Test data must be either at the top level or
       must be in a folder called 'secret' or 'judge' or 'sample'.
    """
    tests = []
    allowed_folder_names = ['secret', 'sample', 'judge', 'judge data', 'sample data']
    zf = ZipFile(zipfilename)
    filenames = zf.namelist()
    folders = defaultdict(list)
    for f in filenames:
        path_bits = f.split('/')
        folder = '/'.join(path_bits[:-1])
        if (folder == '' or any(folder.endswith(fname) for fname in allowed_folder_names)) and any(f.endswith(ext) for ext in ['.in', '.out', '.ans']):
            folders[folder].append(path_bits[-1])

    for folder, names in folders.items():
        infiles = sorted([f for f in names if f.endswith('.in')])
        outfiles = sorted([f for f in names if (f.endswith('.out') or f.endswith('.ans'))])
        infile_names = [f.split('.')[:-1] for f in infiles]
        outfile_names = [f.split('.')[:-1] for f in outfiles]
    
        if infile_names != outfile_names:
            error = f"Set of .in files doesn't match set of .out/.ans  files in {folder}"
            raise BadTestData(error)
        else:
            for i in range(len(infiles)):
                if folder and not folder.endswith('/'):
                    folder += '/'
                with zf.open(f"{folder}{infiles[i]}") as infile:
                    stdin = infile.read().decode('utf-8')
                with zf.open(f"{folder}{outfiles[i]}") as infile:
                    expected = infile.read().decode('utf-8')
                is_sample = 'sample' in folder or infiles[i].lower().startswith('samp')
                expected = expected.replace('\r', '')  # Windows line endings, grrr.
                tests.append((is_sample, stdin, expected))
                
    timeout = None
    ini_files = [f for f in filenames if f.endswith('domjudge-problem.ini')]
    if (len(ini_files) == 1):
        with zf.open(ini_files[0]) as ini_file:
            lines = ini_file.read().decode('utf-8').splitlines()
            for line in lines:
                match_obj = re.match(r"^timelimit *= *'?(\d+)'?.*", line)
                if match_obj:
                    timeout = int(match_obj[1])
    return tests, timeout
    
def get_zip_filename(params):
    """Try to find the ICPC problem archive zip, either via a specified
       filename in the params or by the presence of a single zip file
       in the current working directory. Return its name.
    """
    zipfilename = params.get('tests_zip_filename', '')
    if not zipfilename:
        files = os.listdir('.')
        zips = [filename for filename in files if filename.endswith('.zip')]
        if len(zips) == 1:
            zipfilename = zips[0]
        else:
            raise BadTestData(f"We're dead fred! Expected exactly one .zip file. Got: {str(files)}")
    return zipfilename
    

def get_all_tests(params):
    """Unzip the expected .zip attachment and extract a list of tests from it.
       A test is a (issample, stdin, expected) tuple.
       Return value is a tuple: (timeout value. list of tests).
    """
    zipfilename = get_zip_filename(params)
    tests, timeout = tests_and_timeout_from_zip(zipfilename)
    if len(tests) == 0:
        raise BadTestData('No test data found!')

    return tests, timeout
    
    
def get_validator_from_zip(params):
    """If the zip archive file has an entry for output_validators/*.zip,
       extract it to a file and return its filename. Otherwise return None.
    """
    zipfilename = get_zip_filename(params)
    zf = ZipFile(zipfilename)
    filenames = zf.namelist()    
    validators = [f for f in filenames if 'output_validators/' in f and f.endswith('.zip')]
    if not validators:
        return None
    if len(validators) > 1:
        raise ValidatorFailure("More than one validator found in zip")
    with zf.open(validators[0]) as infile:
        zip_contents = infile.read()
        with open(VALIDATOR_FILENAME, 'wb') as validator:
            validator.write(zip_contents)
    return VALIDATOR_FILENAME
        

def get_question_params():
    params = json.loads("""{{ QUESTION.parameters | json_encode | e('py') }}""")
    unknown_params = set(params.keys()) - set(KNOWN_PARAMS.keys())
    if unknown_params:
        print("Unknown template parameter(s):", list(unknown_params))
    for param_name, default in KNOWN_PARAMS.items():
        if param_name in params:
            param = params[param_name]
            if type(param) != type(default) and default is not None:
                print("Template parameter {} has wrong type (expected {})".format(param_name, type(default)))
        else:
            params[param_name] = default
    cputimelimit = json.loads("""{{ QUESTION.cputimelimitsecs | json_encode | e('py') }}""")

    if cputimelimit and params['total_timeout'] > int(cputimelimit):
        raise Exception("total_timeout cannot exceed cputimelimitsecs value in prototype  ({cputimelimit} secs)")
    return params
    
    
def make_spoiler(fail_case):
    """ Return the html for a spoiler allowing the user to see the first
        failing case (which is passed as the last row of the result table).
    """
    assert(not fail_case[0])  # iscorrect should be false
    element_id = "spoiler" + str(randint(10000, 99999))
    return """<script>
document.toggle = document.toggle || function (element_id) {
    var el = document.getElementById(element_id);
    if (el.style.display === 'none') {
        el.style.display = 'block';
    } else {
        el.style.display = 'none';
    }
}
</script>
""" + """
<br><input type="button" value="Spoiler (show failing test)"
    onclick="document.toggle('{0}')"/><br>
<div id="{0}" class="coderunner-test-results bad" style="display:none">
<table class="coderunner-test-results"><thead>
<tr style="background-color: #e0e0e0"><th>Input</th><th>Expected</th><th>Got</th></tr></thead>
<tbody>
<tr class="r0"><td>{1}</td><td>{2}</td><td>{3}</td></tr>
</tbody></table></div>""".format(element_id, fail_case[2], fail_case[3], fail_case[4])


def main():
    student_answer = """{{ STUDENT_ANSWER | e('py') }}"""
    language = """{{ ANSWER_LANGUAGE | e('py') }}""".lower()
    student = json.loads("""{{ STUDENT | json_encode | e('py') }}""")
    can_view_hidden = student.get('canviewhidden', False)
    params = get_question_params()
    tests, timeout = get_all_tests(params)
    validator_file_name = get_validator_from_zip(params)
    if validator_file_name:
        if params['validator_zip_filename']:
            raise Validator_Failure('Validator present in zip and also specified in params')
        else:
            params['validator_zip_filename'] = validator_file_name

    job_runner = JobRunner(student_answer, language, params, tests, timeout)

    try:
        results = job_runner.compile_and_run()
    except BadTestData as e:
        print(e)
        results = Results(State.bad_test_data, "BAD QUESTION: Invalid zip file - no test data.")

    result_dict = {"fraction": 1.0 if results.state == State.correct else 0.0}

    if results.state == State.compile_error:
        result_dict['prologuehtml'] = "<h5>*** COMPILE ERROR ***</h5>\n" + htmlise(results.global_error)
    else:
        epilogue_messages = []

        # Display a results table only if there is at least one non-hidden row.
        # unless student/user has the canviewhidden attribute set to true
        if len(results.table) > 1 and (can_view_hidden or any(not row[5] for row in results.table[1:])):
            wrapped_header = f"<h5>{params['result_table_header']}</h5>"
            if 'prologuehtml' in result_dict:
                result_dict['prologuehtml'] += '<br>' + wrapped_header
            else:
                result_dict['prologuehtml'] = wrapped_header
            result_dict['testresults'] = results.table
            result_dict['columnformats'] = ['%s', '%h', '%h', '%h']
            if results.failed_hidden:
                epilogue_messages.append('One or more hidden tests failed')
                
        epilogue_messages.append(SUMMARY_MESSAGES[results.state])
        result_dict['epiloguehtml'] = htmlise('\n'.join(epilogue_messages))
        if results.failed_hidden and params['show_spoiler']:
            fail_case = results.table[-1]  # Fail case is always the last
            result_dict['epiloguehtml'] += make_spoiler(fail_case)

    print(json.dumps(result_dict))


main()
