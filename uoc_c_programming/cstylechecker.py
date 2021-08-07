"""Class AstyleChecker checks a given student's program for style compatibility
   with astyle
"""

from collections import namedtuple
import os
import re
import subprocess

import cparser

TEMP_FILENAME = '__temp_code.py'

Code = namedtuple('Code', ['source', 'parser', 'error_message_offset'])


class StyleChecker:
    def __init__(self, code, error_message_offset, params):
        """Initialise, given the code to be checked, an offset to use to adjust any error
           messages, and the dictionary of template params.
           Throws a parse exception if the pycparser can't parse the code.
        """
        self.params = params
        # Maps from source file name to 'code' object.
        self.code_objects = {f"{self.params.get('sourcefilename', 'student_answer.c')} (answer box code)": Code(code, cparser.CParser(code, params), error_message_offset)}

        # For handling extra source files.
        filenames = os.listdir()
        ignore_files = [self.params.get('sourcefilename', 'student_answer.c')]
        for filename in filenames:
            if filename.endswith('.c') and not filename.startswith('__') and filename not in ignore_files:
                with open(filename) as f:
                    code = f.read().replace('\t', '    ')   # Replace tabs with spaces.
                    code = '\n'.join([line.rstrip() for line in code.split('\n')]) + '\n'   # Remove trailing whitespace.
                    self.code_objects[filename] = Code(code, cparser.CParser(code, params), 0)

    def all_style_errors(self) -> list:
        errors = self.tab_check_errors() + self.style_error_list() + self.local_check_errors()
        if self.params.get('checkheaders', False):
            errors += self.header_guard_check()
            errors += self.code_implementation_in_header_check()
        return errors

    def tab_check_errors(self) -> list:
        """Return a list containing an error message about tabs if any tabs are
           present in the student_answer, or an empty list otherwise
        """
        errors = []
        for filename, code in self.code_objects.items():
            lines = code.source.split('\n')
            tab_lines = [line_num + 1 - code.error_message_offset for (line_num, line) in enumerate(lines) if "\t" in line]
            if tab_lines:
                tab_error = f"Tab characters are present in file '{filename}' on line"
                if len(tab_lines) > 1:
                    tab_error += 's'
                tab_error += " " + ", ".join(str(tab) for tab in tab_lines) + '\n'
                tab_error += "Please set your editor preferences to replace tabs with spaces."
                errors.append(tab_error)
        return errors

    def style_error_list(self) -> list:
        """ Check the "style" (or something like it).
            Return a list of errors ([] if no errors)
        """
        errors = []
        for filename, code in self.code_objects.items():

            astyle_error_list = self.astyle_errors(code)
            if astyle_error_list:
                errors.append(f"Your code in '{filename}' did not pass the style checks.")
                errors.extend(astyle_error_list)

            name_errors = code.parser.identifier_errors()
            if name_errors:
                errors.append("The following identifiers are unacceptable in ENCE260:")
                errors.append("    " + "\n    ".join(f"{filename}: line " + str(n[2] - code.error_message_offset) + ": " + n[0]
                                                    for n in name_errors))

            max_length = self.params['maxfunctionlength']
            too_long = code.parser.too_long_funcs(max_length)
            if too_long:
                bad_funcs = ['{} ({}/{})'.format(name, length, max_length) for name, length in too_long]
                errors.append(f"The following functions in '{filename}' are too long:")
                errors.append("    " + ", ".join(bad_funcs))

        return errors

    def astyle_errors(self, code) -> list:
        """ Attempt to check the code provided to the constructor astyle errors
        """
        with open(TEMP_FILENAME, 'w') as outfile:
            outfile.write(code.source)
        program = "./support/astyle"
        flags = self.params['styleflags']
        command = [program] + flags + ['./' + TEMP_FILENAME]
        try:
            output = subprocess.check_output(
                command,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
        except subprocess.CalledProcessError:
            # style check failed, hope it's fine...
            return []
        if output.startswith('Unchanged'):
            return []
        # Astyle makes the original 'filename.orig'
        # and the improved one 'filename'
        try:
            diff = subprocess.check_output(
                ['diff', TEMP_FILENAME + '.orig', TEMP_FILENAME],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
        except subprocess.CalledProcessError as err:
            # diff found a difference, save it!
            diff = str(err.output)
        errors = self.pretty_diff(diff.split('\n'), code.source, code.error_message_offset)
        return errors

    def header_guard_check(self) -> list:
        """Checks that all .h files have a header guard.
           Returns a list of error messages where header 
           guards have been missed.
        """
        errors = []
        filenames = os.listdir()
        cpp_command = ["cpp", "-isystem", "./support/utils/fake_libc_include/", "-P"]

        for filename in filenames:
            if filename.endswith('.h'):
                output_1include = subprocess.check_output(
                        cpp_command,
                        input=f'#include "{filename}"',
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                # Now include the header file twice.
                output_2include = subprocess.check_output(
                        cpp_command,
                        input=f'#include "{filename}"\n#include "{filename}"',
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                if output_1include != output_2include:
                    errors.append(f"You have not included a header guard in '{filename}'")

        return errors

    def code_implementation_in_header_check(self) -> list:
        """ Check to see if code implementation has occuured in the header file.
            Return a list of errors (empty if no errors)
        """
        errors = []
        filenames = os.listdir()
        cpp_command = ["cpp", "-isystem", "./support/utils/fake_libc_include/", "-P"]

        for filename in filenames:
            if filename.endswith('h'):
                output_include = subprocess.check_output(
                        cpp_command,
                        input=f'#include "{filename}"',
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                pattern = re.compile(r"\w+[*]*\s+[*\s]*\w+\s*\(?:.*\)\s*\{")
                if pattern.search(output_include):
                    errors.append(f"You appear to have more than declarations in your header file; it looks like a function definition in {filename}.")
                #pattern = re.compile(r"((?<!typedef)\s+\w+[*]*\s+[*\s]*\w+(?:\s*=\s*.*)*(?:\s*,[*\s]*\w+(?:\s*=\s*.*)*)*);")
                #if pattern.search(output_include):
                #    errors.append(f"You appear to have more than declarations in your header file; it looks like a variable instantiation in {filename}.")

        return errors            


    def local_check_errors(self) -> list:
        """ Any other checks on the code that we want to handle.
            Return a list of errors (empty if no errors)
        """
        errors = []

        for filename, code in self.code_objects.items():
            bad_funcs = code.parser.illegal_called_functions()
            if bad_funcs:
                names = ', '.join("'" + name + "'" for name in bad_funcs)
                errors.append(f"You called the banned function(s) {names} in '{filename}'. Tsk tsk!")

            if 'proscribedsubstrings' in self.params: # Needed for customised legacy questions
                for bad in self.params['proscribedsubstrings']:
                    if bad in code.source:
                        errors.append(f"Your answer must not contain '{bad}' anywhere, including in comments")
            
            if not self.params.get('allowglobals', False) and len(code.parser.global_variables) > 0:
                errors.append("Your code is not allowed to include any global variables.")
                for name, line_num in code.parser.global_variables:
                    errors.append(f"Global variable '{name}' found on line {line_num-code.error_message_offset} in '{filename}'")
                    
            constructs = code.parser.used_constructs()
            constructs_set = set(constructs.keys())
            bad_constructs = set(self.params['proscribedconstructs'])
            if bad_constructs.intersection(constructs_set):
                errors.append("You cannot use the following language features:")
                errors.append("    " + ", ".join(bad_constructs.intersection(constructs_set)))
            

            if 'constructlimits' in self.params:
                construct_limits = self.params['constructlimits']
                for construct, limit in construct_limits.items():
                    if constructs[construct] > limit:
                        plural = 's' if limit != 1 else ''
                        errors.append(f"You can use at most {limit} {construct}{plural}. You have used {constructs[construct]} in '{filename}'.")

        
        # Check for required substrings.
        for required in self.params.get('requiredsubstrings', []):
            if isinstance(required, str) and not any((required in source for source, _, _ in self.code_objects.values())):
                errors.append(f'The string "{required}" must occur somewhere in your code.')
            elif isinstance(required, dict): 
                if 'pattern' in required and not any((re.findall(required['pattern'], source, flags=re.DOTALL) for source, _, _ in self.code_objects.values())):
                    errors.append(required['errormessage'])
                elif 'string' in required and not any((required['string'] in source for source, _, _ in self.code_objects.values())):
                    errors.append(required['errormessage'])

        missing = set.intersection(*[set(parser.missing_funcs()) for _, parser, _ in self.code_objects.values()])
        if missing:
            names = ', '.join("'" + name + "'" for name in missing)
            errors.append("You have not declared the required function(s) {}".format(names))

        needed_constructs = set(self.params['requiredconstructs'])

        constructs_set = set.union(*[set(parser.used_constructs().keys()) for _, parser, _ in self.code_objects.values()])
        if not all(c in constructs_set for c in needed_constructs):
            missing = needed_constructs - constructs_set
            errors.append("You must use the following language features:")
            errors.append("    " + ", ".join(missing))

        return errors

    def pretty_diff(self, diff_lines, source, error_message_offset):
        """ Fix up the lines of diff output to be something pretty.
        """
        err_lines = []
        errors = []
        curr_error = {}
        min_line = error_message_offset
        max_line = min_line + len(source.splitlines())
        for line in diff_lines:
            if line.startswith("<"):
                curr_error['old_lines'].append(line[1:])
            elif line.startswith(">"):
                curr_error['new_lines'].append(line[1:])
            elif line == '---':
                pass  # old/new separator
            elif line == '':
                pass  # blank line...
            else:
                # finish error
                errors.append(curr_error)
                if 'a' in line:
                    old, new = line.split('a')
                elif 'c' in line:
                    old, new = line.split('c')
                elif 'd' in line:
                    old, new = line.split('d')
                curr_error = {
                    'old_line_nums': tuple(int(i) for i in old.split(',')),
                    'new_line_nums': tuple(int(i) for i in old.split(',')),
                    'old_lines': [],
                    'new_lines': [],
                }
        errors.append(curr_error)
        errors = errors[1:]  # The first is empty
        for error in errors:
            line_nums = error['old_line_nums']
            if any(i < min_line or i > max_line for i in line_nums):
                continue
            if len(line_nums) > 1:
                linum = "lines " + ", ".join(str(l - min_line) for l in line_nums)
            else:
                linum = "line " + str(line_nums[0] - min_line)
            linum += ' got:'
            err_lines.append(linum)
            err_lines.extend(error['old_lines'])
            err_lines.append("expected:")
            err_lines.extend(error['new_lines'])
            err_lines.append('')
        return err_lines
