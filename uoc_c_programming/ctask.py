""" Classes for compiling and running a C task.

    Support code for the ENCE260 C template
"""
import subprocess
import re
import languagetask

COMPILER = 'gcc'


class CTask(languagetask.LanguageTask):
    """A CTask manages compiling and executing of a C program.
    """
    def __init__(self, params, code=None):
        """Initialisation is delegated to the superclass. However, the params relevant to this subclass
           are:
            'valgrind':       True if the Valgrind should be used when executing
            'flags':          Compile command line flags
            'std':            The dialect of C (default 'C99')
            'nowall':         Suppress the usual --Wall flag at compile time
            'nowerror':       Suppress the usual --Werror flag at compile time
        """
        new_params = {  # Ensure compatibility with legacy customised questions
            'sourcefilename': 'student_answer.c',
            'executablefilename': 'student_answer',
            'usemake': False,
            'makeflags': [],
            'ldflags': []
        }
        for key, default in new_params.items():
            if key not in params:
                params[key] = default

        super().__init__(params, code)

    def make_source_file(self, filename=None):
        """Save the source code to the given file
        """
        if filename is None:
            filename = self.params['sourcefilename']
        with open(filename, 'w') as file:
            file.write(self.code)

    def correct_error_line_num(self, error_string):
        """ Fix up the line numbers so they point to the right place
            in the student's code.
        """
        new_lines = []
        for line in error_string.split('\n'):
            if re.findall(self.params['executablefilename'] + r':\d+:\d+: ', line):
                old_line_no_str = line.split(":")[1]
                new_line_no_str = str(int(old_line_no_str) - self.error_message_offset)
                line = line.replace(old_line_no_str, new_line_no_str, 1)
            new_lines.append(line)
        return '\n'.join(new_lines)

    def compile(self, make_executable=False):
        """Compile the currently set code, either to an object file or
           to an executable file depending on the given make_executable parameter.
           If usesmakefile is True, the supplied Makefile will be used and the make_executable
           parameter will be ignored. Otherwise,
           the executable will be named according to the
           Adjust any error message by subtracting error_message_offset.
           Raise CompileError if the code does not
           compile, with the compilation error message within the exception
           and also recorded in self.compile_error_message.
           No return value.
        """
        self.make_source_file()

        # Set up the command to use
        if self.params['usemake']:
            command = ' '.join(['make'] + self.params['makeflags'])
        else:
            ldflags = self.params['ldflags']
            if make_executable:
                compile_flags = self.params['flags'] + ['-o', self.params['executablefilename']]
            else:
                compile_flags = self.params['flags'] + ['-c']
            support_source_files = []
            if self.params['checkalloc']:
                support_source_files.append("./support/utils/overrides/testalloc.c")
            if self.params['checkfiles']:
                support_source_files.append("./support/utils/overrides/testfiles.c -ldl")
                ldflags += ['-ldl']
            support_source_files += self.params['includesource']

            command_bits = [COMPILER] + compile_flags + [self.params['sourcefilename']] + ldflags + support_source_files
            command = ' '.join(command_bits)

        self.compile_error_message = None
        try:
            self.compile_error_message = subprocess.check_output(
                command,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                shell=True
            )
        except subprocess.CalledProcessError as err:
            self.compile_error_message = self.correct_error_line_num(err.output)

        if self.compile_error_message:
            raise languagetask.CompileError(self.compile_error_message)

        self.executable_built = make_executable and not self.compile_error_message

    def discard_executable(self):
        """Called if something breaks when the executable if built"""
        self.executable_built = False

    def is_clean_valgrind_run(self):
        """Return true if the valgrind output (in self.stderr) is free of
           errors
        """
        return 'ERROR SUMMARY: 0 errors' in self.stderr and 'in use at exit: 0 bytes' in self.stderr

    def fix_valgrind_error_line_nums(self):
        """Edit the current valgrind output (in self.stderr) to adjust line numbers"""
        fixed_lines = []
        for line in self.stderr.splitlines():
            match = re.search(r"\({}:(\d+)\)".format(self.params['executablefilename']), line)
            if match:
                wrong_line_num = int(match.group(1))
                right_line_num = wrong_line_num - self.error_message_offset
                chars = list(line)
                chars[match.start(1):match.end(1)] = list(str(right_line_num))
                line = ''.join(chars)
            fixed_lines.append(line)
        self.stderr = '\n'.join(fixed_lines) + '\n'

    def run_code(self, standard_input=None, bash_command=None):
        """Run the code in the compiled executable program
           (named self.params['executablefilename'])make
           with the given standard input. If a bash_command is supplied it used
           as given, but preceded by valgrind if self.params['valgrind'] is true.
           Otherwise the command to be executed is the compiled executable,
           run with valgrind if self.params['valgrind'] is true.
           Returns a tuple of the output from the
           run and a stderr (or a derivative thereof) string. Those two values
           are also recorded in self.stdout and self.stderr respectively.
        """
        assert self.executable_built
        if standard_input:
            standard_input = standard_input.rstrip() + '\n'

        self.stderr = ''
        self.stdout = ''

        if bash_command:
            command = bash_command
            if self.params['valgrind']:
                command = 'valgrind ' + command
            use_shell = True
        else:
            command = ['./' + self.params['executablefilename']]
            if self.params['valgrind']:
                command = ['valgrind', "--leak-check=full"] + command
            use_shell = False

        try:
            with open(self.params['executablefilename'] + '.stderr', 'w') as f_stderr:
                with open(self.params['executablefilename'] + '.stdout', 'w') as f_stdout:
                    subprocess.run(
                        command,
                        shell=use_shell,
                        stdout = f_stdout,
                        stderr=f_stderr,
                        universal_newlines=True,
                        encoding='utf-8',
                        errors='backslashreplace',
                        input=standard_input,
                        check=True,
                        timeout=self.params['timeout']
                    )
        except subprocess.TimeoutExpired as err:
            self.stderr = "*** Time limit ({} secs) exceeded ***\n".format(self.params['timeout'])
        except subprocess.CalledProcessError as err:
            if err.returncode == -11:
                self.stderr = "*** Segmentation Fault ***\n"
            elif err.returncode > 0 and self.params.get('allowpositivereturn', False):
                pass
            else:
                self.stderr = "*** Runtime Error. Return code: {} ***\n".format(err.returncode)
        except MemoryError:
            self.stderr = "*** Memory error when running test. Excessive output?? ***\n"

        finally:
            with open(self.params['executablefilename'] + '.stdout', errors='backslashreplace') as f_stdout:
                self.stdout = f_stdout.read() + self.stdout
            with open(self.params['executablefilename'] + '.stderr', errors='backslashreplace') as f_stderr:
                self.stderr = f_stderr.read() + self.stderr

            if self.stderr and self.params['valgrind']:
                if self.is_clean_valgrind_run():
                    self.stderr = ''
                else:
                    self.fix_valgrind_error_line_nums()

        if len(self.stdout) > self.params['maxoutputbytes']:
            self.stdout = self.stdout[0:self.params['maxoutputbytes']] + '\n*** EXCESSIVE OUTPUT - TRUNCATED ***'

        if self.stderr and self.params.get('allowstderr', False):
            self.stdout = self.stdout + '\nSTDERR OUTPUT:\n' + self.stderr
            self.stderr = ''

        return self.stdout, self.stderr
