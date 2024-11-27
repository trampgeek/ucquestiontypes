"""The generic (multi-language) main testing class that does all the work - trial compile, style checks,
   run and grade.
"""
from __resulttable import ResultTable
import html
import os
import re
import __languagetask as languagetask
import base64


# Values of QUESTION.precheck field
PRECHECK_DISABLED = 0
PRECHECK_EMPTY = 1
PRECHECK_EXAMPLES = 2
PRECHECK_SELECTED = 3
PRECHECK_ALL = 4

# Values of testtype
TYPE_NORMAL = 0
TYPE_PRECHECKONLY = 1
TYPE_BOTH = 2

# Global message for when a test-suite timeout occurs
TIMEOUT_MESSAGE = """A timeout occurred when running the whole test suite as a single program.
This is usually due to an endless loop in your code but can also arise if your code is very inefficient
and the accumulated time over all tests is excessive. Please ask a tutor or your lecturer if you need help
with making your program more efficient."""


def get_jpeg_b64(filename):
    """Return the contents of the given file (assumed to be jpeg) as a base64
       encoded string in utf-8.
    """
    with open(filename, 'br') as fin:
        contents = fin.read()

    return base64.b64encode(contents).decode('utf8')


class Tester:
    def __init__(self, params, testcases):
        """Initialise the instance, given the test of template and global parameters plus
           all the testcases. Parameters required by this base class and all subclasses are:
               'STUDENT_ANSWER': code submitted by the student
               'SEPARATOR': the string to be used to separate tests in the output
               'ALL_OR_NOTHING: true if grading is all-or-nothing
               'stdinfromextra': true if the test-case 'extra' field is to be used for
                                 standard input rather than the usual stdin field
               'runtestssingly': true to force a separate run for each test case
               'stdinfromextra': true if the extra field is used for standard input (legacy use only)
               'testisbash': true if tests are bash command line(s) rather than the default direct execution
                             of the compiled program. This can be used to supply command line arguments.

        """
        self.student_answer = self.clean(params['STUDENT_ANSWER'])
        self.separator = params['SEPARATOR']
        self.all_or_nothing = params['ALL_OR_NOTHING']
        self.params = params
        self.testcases = self.filter_tests(testcases)
        self.result_table = ResultTable(params)
        self.result_table.set_header(self.testcases)

        # It is assumed that in general subclasses will prefix student code by a prelude and
        # postfix it by a postlude.
        self.prelude = ''
        self.prelude_length = 0
        self.postlude = ''

        self.task = None  # SUBCLASS MUST DEFINE THIS

    def filter_tests(self, testcases):
        """Return the relevant subset of the question's testcases.
           This will be all testcases not marked precheck-only if it's not a precheck or all testcases if it is a
           precheck and the question precheck is set to "All", or the appropriate subset in all other cases.
        """
        if not self.params['IS_PRECHECK']:
            return [test for test in testcases if test.testtype != TYPE_PRECHECKONLY]
        elif self.params['QUESTION_PRECHECK'] == PRECHECK_ALL:
            return testcases
        elif self.params['QUESTION_PRECHECK'] == PRECHECK_EMPTY:
            return []
        elif self.params['QUESTION_PRECHECK'] == PRECHECK_EXAMPLES:
            return [test for test in testcases if test.useasexample]
        elif self.params['QUESTION_PRECHECK'] == PRECHECK_SELECTED:
            return [test for test in testcases if test.testtype in [TYPE_PRECHECKONLY, TYPE_BOTH]]

    def style_errors(self):
        """Return a list of all the style errors. Implementation is language dependent.
           Default is no style checking.
        """
        return []

    def single_program_build_possible(self):
        """Return true if and only if the current configuration permits a single program to be
           built and tried containing all tests. It should be true for write-a-program questions and
           conditionally true for other types of questions that allow a "combinator" approach,
           dependent on the presence of stdins in tests and other such conditions.
        """
        raise NotImplementedError("Tester must have a single_program_build_possible method")

    def adjust_error_line_nums(self, error):
        """Given a runtime error message, adjust it as may be required by the
           language, e.g. adjusting line numbers
        """
        raise NotImplementedError("Tester must have an adjust_error_line_nums method")

    def single_run_possible(self):
        """Return true if a single program has been built and it is possible to use that in a single run
           with all tests.
        """
        return (self.task.executable_built
                and not self.params['runtestssingly']
                and not self.result_table.has_stdins
                and not self.params['testisbash'])

    def make_test_postlude(self, testcases):
        """Return the postlude testing code containing all the testcode from
           the given list of testcases (which may be the full set or a singleton list).
           A separator must be printed between testcase outputs."""
        raise NotImplementedError("Tester must have a make_test_postlude method")

    def trial_compile(self):
        """This function is the first check on the syntactic correctness of the submitted code.
           It is called before any style checks are done. For compiled languages it should generally
           call the standard language compiler on the student submitted code with any required prelude
           added and, if possible, all tests included. CompileError should be raised if the compile fails,
           which will abort all further testing.
           If possible a complete ready-to-run executable should be built as well; if this succeeds, the
           LanguageTasks 'executable_built' attribute should be set. This should be possible for write-a-program
           questions or for write-a-function questions when there is no stdin data in any of the tests.

           Interpreted languages should perform what syntax checks are possible using the standard language tools.
           If those checks succeeded, they should also attempt to construct a source program that incorporates all
           the different tests (the old "combinator" approach) and ensure the task's 'executable_built' attribute
           is True.

           The following implementation is sufficient for standard compiled languages like C, C++, Java. It
           may need overriding for other languages.
        """
        if self.single_program_build_possible():
            self.setup_for_test_runs(self.testcases)
            make_executable = True
        else:
            self.postlude = ''
            self.task.set_code(self.prelude + self.student_answer, self.prelude_length)
            make_executable = False

        self.task.compile(make_executable)  # Could raise CompileError

    def setup_for_test_runs(self, tests):
        """Set the code and prelude length as appropriate for a run with all the given tests. May be called with
           just a singleton list for tests if single_program_build_possible has returned false or if testing with
           multiple tests has given exceptions.
           This implementation may need to be overridden, e.g. if the student code should follow the test code, as
           say in Matlab scripts.
        """
        self.postlude = self.make_test_postlude(tests)
        self.task.set_code(self.prelude + self.student_answer + self.postlude, self.prelude_length)

    def run_all_tests(self):
        """Run all the tests, leaving self.ResultTable object containing all test results.
           Can raise CompileError or RunError if things break.
           If any runtime errors occur on the full test, drop back to running tests singly.
        """
        done = False
        if self.single_run_possible():
            # We have an executable ready to go, with no stdins or other show stoppers
            output, error = self.task.run_code()
            output = output.rstrip() + '\n'
            error = error.strip() + '\n'

            # Generate a result table using all available test data.
            results = output.split(self.separator + '\n')
            errors = error.split(self.separator + '\n')
            if len(results) == len(errors):
                merged_results = []
                for result, error in zip(results, errors):
                    result = result.rstrip() + '\n'
                    if error.strip():
                        adjusted_error = self.adjust_error_line_nums(error.rstrip())
                        result += '\n*** RUN ERROR ***\n' + adjusted_error
                    merged_results.append(result)

                missed_tests = len(self.testcases) - len(merged_results)

                for test, output in zip(self.testcases, merged_results):
                    self.result_table.add_row(test, output)

                self.result_table.tests_missed(missed_tests)
                if self.task.timed_out:
                    self.result_table.record_global_error(TIMEOUT_MESSAGE)
                done = True

            if not done:
                # Something broke. We will need to run each test case separately
                self.task.executable_built = False
                self.result_table.reset()

        if not done:
            # If a single run isn't appropriate, do a separate run for each test case.
            build_each_test = not self.task.executable_built
            for i_test, test in enumerate(self.testcases):
                if build_each_test:
                    self.setup_for_test_runs([test])
                    self.task.compile(True)
                standard_input = test.extra if self.params['stdinfromextra'] else test.stdin
                if self.params['testisbash']:
                    output, error = self.task.run_code(standard_input, test.testcode)
                else:
                    output, error = self.task.run_code(standard_input)
                adjusted_error = self.adjust_error_line_nums(error.rstrip())
                self.result_table.add_row(test, output, adjusted_error)
                if error and self.params['abortonerror']:
                    self.result_table.tests_missed(len(self.testcases) - i_test - 1)
                    break

    def compile_and_run(self):
        """Phase one of the test operation: do a trial compile and then, if all is well and it's not a precheck,
           continue on to run all tests.
           Return a tuple mark, errors where mark is a fraction in 0 - 1 and errors is a list of all the errors.
           self.test_results contains all the test details.
        """
        mark = 0
        errors = []

        # Do a trial compile, then a style check. If all is well, run the code
        try:
            self.trial_compile()

            if not self.params['nostylechecks']:
                errors = self.style_errors()
            if not errors:
                if self.params['IS_PRECHECK'] and self.params['QUESTION_PRECHECK'] <= 1:
                    mark = 1
                else:
                    self.run_all_tests()
                    max_mark = sum(test.mark for test in self.testcases)
                    mark = self.result_table.get_mark() / max_mark  # Fractional mark 0 - 1
        except languagetask.CompileError as err:
            adjusted_error = self.adjust_error_line_nums(str(err).rstrip())
            errors.append("COMPILE ERROR\n" + adjusted_error)
        except languagetask.RunError as err:
            adjusted_error = self.adjust_error_line_nums(str(err).rstrip())
            errors.append('RUN ERROR\n' + adjusted_error)
        return mark, errors

    def prerun_hook(self):
        """A hook for subclasses to do initial setup or code hacks etc
           Returns a list of errors, to which other errors are appended
        """
        return []

    def get_all_images_html(self):
        """Search the current directory for images named _image.*(Expected|Got)(\d+).png.
           For each such file construct an html img element with the data encoded
           in a dataurl.
           If we're running the sample answer, always return [] - images will be
           picked up when we run the actual answer.
           Returns a list of tuples (img_elements, column_name, row_number) where
           column_name is either 'Expected' or 'Got', defining in which result table
           column the image belongs and row number is the row (0-origin, excluding
           the header row).
        """
        images = []
        if self.params.get('running_sample_answer', False):
            return []
        if self.params['imagewidth'] is not None:
            width_spec = " width={}".format(self.params['imagewidth'])
        else:
            width_spec = ""
        files = sorted(os.listdir('.'))
        for filename in files:
            match = re.match(r'_image[^.]*\.(Expected|Got)\.(\d+).png', filename)
            if match:
                image_data = get_jpeg_b64(filename)
                img_template = '<img{} style="margin:3px;border:1px solid black" src="data:image/jpeg;base64,{}">'
                img_html = img_template.format(width_spec, image_data)
                column = match.group(1)   # Name of column
                row = int(match.group(2)) # 0-origin row number
                images.append((img_html, column, row))
        return images

    def test_code(self):
        """The "main program" for testing. Returns the test outcome, ready to be printed by json.dumps"""
        errors = self.prerun_hook()
        if errors:
            mark = 0
        else:
            mark, errors = self.compile_and_run()

        outcome = {"fraction": mark}

        error_text = '\n'.join(errors)
        # TODO - check if error line numbers are still being corrected in C and matlab
        if self.params['IS_PRECHECK']:
            if mark == 1:
                prologue = "<p class='precheckresult'>Passed 🙂</p>"
            else:
                prologue = "<p class='precheckresult'>Failed, as follows.</p>"
        elif errors:
            prologue = "<div class='coderunner-test-results bad'><h3>Pre-run checks failed</h3>\n"
        else:
            prologue = ""

        if prologue:
            outcome['prologuehtml'] = prologue + self.htmlize(error_text)

        epilogue = ''
        images = self.get_all_images_html()
        if images:
            for (image, column, row) in images:
                self.result_table.add_image(image, column, row)
        outcome['columnformats'] = self.result_table.get_column_formats()

        if len(self.result_table.table) > 1:
            outcome['testresults'] = self.result_table.get_table()
            outcome['showdifferences'] = True

        if self.result_table.global_error:
            epilogue += "<div class='coderunner-test-results bad'><h4>Run Error</h4><pre>{}</pre></div>".format(
                self.htmlize(self.result_table.global_error))

        if self.result_table.aborted:
            epilogue = outcome.get('epiloguehtml', '') + (
                "<div class='coderunner-test-results bad'>Testing was aborted due to runtime errors.</div>")

        if self.result_table.missing_tests != 0:
            template = "<div class='coderunner-test-results bad'>{} tests not run due to previous errors.</div>"
            epilogue += template.format(self.result_table.missing_tests)

        if self.result_table.failed_hidden:
            epilogue += "<div class='coderunner-test-results bad'>One or more hidden tests failed.</div>"

        if epilogue:
            outcome['epiloguehtml'] = epilogue
        return outcome

    @staticmethod
    def clean(code):
        """Return the given code with trailing white space stripped from each line"""
        return '\n'.join([line.rstrip() for line in code.split('\n')]) + '\n'

    @staticmethod
    def htmlize(message):
        """An html version of the given error message"""
        return '<pre>' + html.escape(message) + '</pre>' if message else ''
