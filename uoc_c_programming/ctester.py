"""The main c-program testing class that does all the work - trial compile, style checks,
   run and grade. A subclass of the generic tester.
"""
import os

import ctask
from tester import Tester
from cstylechecker import StyleChecker

STANDARD_INCLUDES = ['<stdio.h>', '<stdlib.h>', '<ctype.h>', '<string.h>', '<stdbool.h>', '<math.h>']


class CTester(Tester):
    def __init__(self, params, testcases):
        """Initialise the instance, given the test of template and global parameters plus
           all the testcases. Parameters relevant to this class are all those listed for the Tester class plus
               'extra' which takes the values 'pretest' or 'posttest' (the other possible value, 'stdin', has been
               handled by the main template).
           Additionally the support classes like stylechecker and cparser need their
           own params - q.v.
        """
        super().__init__(params, testcases)  # Most of the task is handed by the generic tester

        # C-dependent attributes
        self.task = ctask.CTask(params)
        self.params['includes'] = STANDARD_INCLUDES + self.params['includes']
        if params['isfunction']:
            self.prelude = '\n'.join('#include ' + incl for incl in self.params['includes']) + '\n'
            self.prelude_length = len(self.params['includes'])
        else:
            self.prelude = ''
            self.prelude_length = 0

    def style_errors(self):
        """Return a list of all the style errors"""
        try:
            # Style-check the program without any test cases or other postlude added
            source_to_check = self.prelude + self.student_answer
            style_checker = StyleChecker(source_to_check, self.prelude_length, self.params)
            errors = style_checker.all_style_errors()
        except Exception as e:
            error_text = "Oops. Your program compiled with gcc but not with the Python C parser.\n"
            error_text += "The error occurred at or near " + str(e) + '\n'
            error_text += "Did you use isalpha, isdigit or similar in an if expression without parentheses?\n"
            error_text += "Ask a tutor or Richard for help if you can't figure it out."
            errors = [error_text]

        return errors

    def make_test_postlude(self, testcases):
        """Return the testing main function containing all the testcode from
           the given list of testcases. Separator printing is inserted between
           each test"""

        if self.params['testshavemain']:
            assert len(testcases) == 1
            return testcases[0].testcode
        
        if not self.params['isfunction']:
            return ''   # Nothing to do for a write-a-program question

        tester = 'int main(int argc, char* argv[])\n{\n'
        print_separator_stdout = '   fprintf(stdout, "' + self.separator + '\\n");fflush(stdout);\n\n'
        print_separator_stderr = '   fprintf(stderr, "' + self.separator + '\\n");fflush(stderr);\n\n'
        print_separator = print_separator_stdout + print_separator_stderr
        test_blocks = []
        for test in testcases:
            block = '{\n'
            if self.params['extra'] == 'pretest':
                block += test.extra + '\n'
            block += test.testcode.rstrip()
            if block[-1] != ';':
                block += ';'
            block += '\n'
            if self.params['extra'] == 'posttest':
                block += test.extra + '\n'
            block += '}\n'
            test_blocks.append(block)
        tester += print_separator.join(test_blocks)
        tester += '   return 0;\n}\n'
        return tester

    def single_program_build_possible(self):
        """Return true if and only if the current configuration permits a single program to be
           built, containing all tests. It should be true for write-a-program questions and
           conditionally true for other types of questions that allow a "combinator" approach,
           dependent on the presence of stdins in tests and other such conditions.
        """
        if not self.params['isfunction'] and not self.params['testshavemain']:  # Write-a-program questions
            return True
        else:
            has_stdins = self.result_table.has_stdins
            return not(has_stdins or self.params['testshavemain'] or self.params['runtestssingly'])


    def adjust_error_line_nums(self, error):
        return error
    
    def adjust_run_error_line_nums(self, error):
        return error