"""The main python-program testing class that does all the work - style checks,
   run and grade. A subclass of the generic tester.
   Since each test can by run within the current instance of Python using
   an exec, we avoid the usual complication of combinators by running
   each test separately regardless of presence of stdin, testcode, etc.
"""
import __pytask as pytask
import re
from __tester import Tester
from __pystylechecker import StyleChecker
from random import randint


class PyTester(Tester):
    def __init__(self, params, testcases):
        """Initialise the instance, given the test of template and global parameters plus
           all the testcases. Parameters relevant to this class are all those listed for the Tester class plus
               'extra' which takes the values 'pretest' or 'posttest' (the other possible value, 'stdin', has been
               handled by the main template).
           Additionally the support classes like stylechecker and pyparser need their
           own params - q.v.
        """
        super().__init__(params, testcases)  # Most of the task is handed by the generic tester
        
        # If the extra field is set to files, the first line of stdin must be filenames.
        # Create all required files.
        if params['extra'] == 'files':
            if not params['IS_PRECHECK']:
                for test in testcases:
                    stdin_lines = test.stdin.splitlines()
                    filename = stdin_lines[0].strip() if stdin_lines else ''
                    if filename == '':
                        raise Exception('The first line of stdin must be the filename')
                    if filename not in params['protectedfiles']:
                        with open(filename, 'w') as outfile:
                            outfile.write(test.extra.rstrip() + '\n')

        # Py-dependent attributes
        self.task = pytask.PyTask(params)
        self.prelude = ''

        if params['isfunction']:
            if not self.has_docstring():
                self.prelude = '"""Dummy docstring for a function"""\n'

        if params['usesmatplotlib']:
            self.prelude += '\n'.join([
                'import os',
                'import matplotlib as _mpl',
                '_mpl.use("Agg")',
                'from __plottools import print_plot_info',
            ]) + '\n'
            self.params['pylintoptions'].append("--disable=ungrouped-imports")

        if params['usesnumpy']:
            self.prelude +=  'import numpy as np\n'
            self.params['pylintoptions'].append("--disable=unused-import,ungrouped-imports")
            self.params['pylintoptions'].append("--extension-pkg-whitelist=numpy")

        for import_string in params['imports']:
            if ' ' not in import_string:
                self.prelude += 'import ' + import_string + '\n'
            else:
                self.prelude += import_string + '\n'

        if params['prelude'] != '':
            self.prelude += '\n' + params['prelude'].rstrip() + '\n'

        try:
            with open('_prefix.py') as prefix:
                prefix_code = prefix.read()
                self.prelude += prefix_code.rstrip() + '\n'

        except FileNotFoundError:
            pass

        self.prelude_length = len(self.prelude.splitlines())
        if self.has_docstring() and self.prelude_length > 0:
            # If we insert prelude in front of the docstring, pylint will
            # give a missing docstring error. Our horrible hack solution is
            # to insert an extra docstring at the start and turn off the
            # resulting 'string statement has no effect' error.
            self.prelude = '"""Dummy docstring for a function"""\n' + self.prelude
            self.prelude_length += 1
            self.params['pylintoptions'].append("--disable=W0105")
        self.style_checker = StyleChecker(self.prelude, self.params['STUDENT_ANSWER'], self.params)

    def has_docstring(self):
        """True if the student answer has a docstring, which means that,
           when stripped, it starts with a string literal.
        """
        prog = self.params['STUDENT_ANSWER'].lstrip()
        return prog.startswith('"') or prog.startswith("'")
    

    def tweaked_warning(self, message):
        """Improve the warning message by updating line numbers and replacing <string>: with Line
        """
        return self.adjust_error_line_nums(message).replace('<string>:', 'Line ')
    

    def style_errors(self):
        """Return a list of all the style errors. Start with local tests and continue with pylint
           only if there are no local errors.
        """
        errors = []
        if self.params.get('localprechecks', True):
            try:
                errors += self.style_checker.local_errors() # Note: prelude not included so don't adjust line nums
            except Exception as e:
                errors += [str(e)]
            else:
                check_for_passive = (self.params['warnifpassiveoutput'] and self.params['isfunction'])
                if check_for_passive:
                    passive = self.passive_output()
                    warning_messages = [line for line in passive.splitlines() if 'Warning:' in line]
                    if warning_messages:
                        errors += [self.tweaked_warning(message) for message in warning_messages]
                    elif passive:
                        errors.append("Your code was not expected to generate any output " +
                                      "when executed stand-alone.\nDid you accidentally include " +
                                      "your test code?\nOr you might have a wrong import statement - have you tested in Wing?")
                        errors.append(passive)

        if len(errors) == 0 or self.params.get('forcepylint', False):
            # Run precheckers (pylint, mypy)
            try:
                # Style-check the program without any test cases or other postlude added
                errors += self.style_checker.style_errors()
            except Exception as e:
                error_text = '*** Unexpected error while running precheckers. Please report ***\n' + str(e)
                errors += [error_text]
            errors = [self.simplify_error(self.adjust_error_line_nums(error)) for error in errors]
            errors = [error for error in errors if not error.startswith('************* Module')]

        errors = [error.replace('<unknown>, ', '') for error in errors]  # Another error tidying operation
        if errors:
            errors.append("\nSorry, but your code doesn't pass the style checks.")
        return errors

    def prerun_hook(self):
        """A hook for subclasses to do initial setup or code hacks etc
           Returns a list of errors, to which other errors are appended.
           In this class we use it firstly to check that the number of Prechecks
           allowed has not been exceeded and then, of not, to perform
           required hacks to disable calls to main. If the call to main_hacks
           fails, assume the code is bad and will get flagged by pylint in due course.
        """
        step_info = self.params['STEP_INFO']
        max_prechecks = self.params.get('maxprechecks', None)
        if max_prechecks and step_info['numprechecks'] >= max_prechecks:
            return [f"Sorry, you have reached the limit on allowed prechecks ({max_prechecks}) for this question."]
        
        try:
            return self.main_hacks()
        except:
            return []

    def passive_output(self):
        """ Return the passive output from the student answer code
            This is essentially a "dry run" of the code.
        """
        code = self.prelude + self.params['STUDENT_ANSWER']
        if self.params['usesmatplotlib']:
            code += '\n'.join([
                'figs = _mpl.pyplot.get_fignums()',
                'if figs:',
                '    print(f"{len(figs)} figures found")',
                '    print(f"{_mpl.pyplot.get_figlabels()}")'
            ]) + '\n'
        task = pytask.PyTask(self.params, code)
        task.compile()
        captured_output, captured_error = task.run_code()
        return (captured_output + '\n' + captured_error).strip()

    def make_test_postlude(self, testcases):
        """Return the code that follows the student answer containing all the testcode
           from the given list of testcases, which should always be of length 1
           (because we don't bother trying to combine all the tests into a
           single run in Python)
        """
        assert len(testcases) == 1
        if self.params['notest']:
            return ''
        test = testcases[0]
        tester = ''
        if self.params['globalextra'] and self.params['globalextra'] == 'pretest':
            tester += self.params['GLOBAL_EXTRA'] + '\n'
        if test.extra and self.params['extra'] == 'pretest':
            tester += test.extra + '\n'
        if test.testcode:
            tester += test.testcode.rstrip() + '\n'
        if self.params['globalextra'] and self.params['globalextra'] == 'posttest':
            tester += self.params['GLOBAL_EXTRA'] + '\n'
        if test.extra and self.params['extra'] == 'posttest':
            tester += test.extra + '\n'

        if self.params['usesmatplotlib']:
            if 'dpi' in self.params and self.params['dpi']:
                extra = f", dpi={self.params['dpi']}"
            else:
                extra = ''
            if self.params.get('running_sample_answer', False):
                column = 'Expected'
            else:
                column = 'Got'
            test_num = len(self.result_table.table) - 1  # 0-origin test number from result table
            tester += '\n'.join([
                'figs = _mpl.pyplot.get_fignums()',
                'for fig in figs:',
                '    _mpl.pyplot.figure(fig)',
                '    row = {}'.format(test_num),
                '    column = "{}"'.format(column),
                '    _mpl.pyplot.savefig("_image{}.{}.{}.png".format(fig, column, row), bbox_inches="tight"' + '{})'.format(extra),
                '    _mpl.pyplot.close(fig)'
            ]) + '\n'
        return tester

    def single_program_build_possible(self):
        """We avoid all the complication of trying to run all tests in
           a single subprocess run by using exec to run each test singly.
        """
        return False

    def adjust_error_line_nums(self, error):
        """Subtract the prelude length of all line numbers in the given error message
        """
        error_patterns = [
                (r'(.*<fstring>.* \(syntax-error\).*)', []),
                (r'(.*File ".*", line +)(\d+)(, in .*)', [2]),
                (r'(.*: *)(\d+)(, *\d+:.*\(.*line +)(\d+)(\).*)', [2, 4]),
                (r'(.*: *)(\d+)(, *\d+:.*\(.*\).*)', [2]),
                (r'(.*:)(\d+)(:\d+: [A-Z]\d+: .*line )(\d+)(.*)', [2, 4]),
                (r'(.*:)(\d+)(:\d+: [A-Z]\d+: .*)', [2]),
                (r'(.*:)(\d+)(: [a-zA-Z]*Warning.*)', [2]),
        ]
        output_lines = []
        for line in error.splitlines():
            for pattern, line_group_nums in error_patterns:
                match = re.match(pattern, line)
                if match:
                    line = ''
                    for i, group in enumerate(match.groups(), 1):
                        if i in line_group_nums:
                            linenum = int(match.group(i))
                            adjusted = linenum - self.prelude_length
                            line += str(adjusted)
                        else:
                            line += group
                    break

            output_lines.append(line)
        return '\n'.join(output_lines)

    def simplify_error(self, error):
        """Return a simplified version of a pylint error with Line <n> inserted in
           lieu of __source.py:<n><p>: Xnnnn
        """
        pattern = r'_?_?source.py:(\d+): *\d+: *[A-Z]\d+: (.*)'
        match = re.match(pattern, error)
        if match:
            return f"Line {match.group(1)}: {match.group(2)}"
        else:
            return error

    def main_hacks(self):
        """Modify the code to be tested if params stripmain or stripmainifpresent'
           are specified. Returns a list of errors encountered while so doing.
        """
        errors = []
        if self.params['stripmain'] or self.params['stripmainifpresent']:
            main_calls = self.style_checker.find_function_calls('main')
            if self.params['stripmain'] and main_calls == []:
                errors.append("No call to main() found")
            else:
                student_lines = self.student_answer.split('\n')
                for (line, depth) in main_calls:
                    if depth == 0:
                        main_call = student_lines[line]
                        if not re.match(r' *main\(\)', main_call):
                            errors.append(f"Illegal call to main().\n" +
                                "main should not take any parameters and should not return anything.")
                        else:
                            student_lines[line] = main_call.replace(
                                                "main", "pass   # Disabled call to main")
                    else:
                        student_lines[line] += "  # We've let you call main here."
                self.params['STUDENT_ANSWER'] = self.student_answer = '\n'.join(student_lines) + '\n'

        return errors
