""" Code for compiling (N/A) and running a Python3 task.
"""
import __languagetask as languagetask
import io
import sys
import traceback
import types
from math import floor
import os
import re
import copy
from __watchdog import Watchdog

SOURCE_FILENAME = 'student_answer.py'
DEFAULT_TIMEOUT = 3 # secs
DEFAULT_MAXOUTPUT = 100000 # 100 kB

class OutOfInput(Exception):
    pass

class ExcessiveOutput(Exception):
    pass

# (mct) New exception for handling situations where submitted code does something it should not.
class InvalidAction(Exception):
    def __init__(self, error_message=''):
        Exception.__init__(self, error_message)

def name_matches_res(name, re_strings):
    return bool(re.match(f"^{'$|^'.join(re_strings)}$", name))

class CodeTrap(object):
    """ A safe little container to hold the student's code and grab
        its output, while also reformatting exceptions to be nicer.
    """

    def __init__(self, student_code, params, seconds_remaining=None):
        self.params = params
        if 'timeout' not in params:
            self.params['timeout'] = DEFAULT_TIMEOUT
        if 'maxoutputbytes' not in params:
            self.params['maxoutputbytes'] = DEFAULT_MAXOUTPUT
        if 'echostandardinput' not in params:
            self.params['echostandardinput'] = True
        self.run_code = student_code

        if params["checkfileclosure"]:
            self.run_code += '''
files = _open_files.values() if '_open_files' in vars() else []
open_file_names = [name for name, close_func in files]
if len(open_file_names) == 1:
    print(f"You forgot to close the file '{open_file_names[0]}'.")
elif len(open_file_names) > 1:
    print(f"""You forgot to close the files: '{"', '".join(open_file_names)}'.""")
'''
        self.scoped_globals = self._get_globals()

        if seconds_remaining is None:
            self.seconds_remaining = self.params['timeout']
        else:
            self.seconds_remaining = min(seconds_remaining, self.params['timeout'])
        CodeTrap.MAX_OUTPUT_CHARS = 30000
        CodeTrap.output_chars = 0  # Count of printed chars (more or less)
        CodeTrap.running = False

    def _get_globals(self):
        """ Here we define any globals that must be available """
        # change the default options for 'open'.
        global np  # May not actually be defined but we'll check soon
        def new_open(file, mode='r', buffering=-1,
                     encoding='utf-8', errors=None,
                     newline=None, closefd=True, opener=None):
            
            # (mct63) Only open allowed files.
            if ('restrictedfiles' in self.params
                    and ('onlyallow' not in self.params['restrictedfiles'] or name_matches_res(file, self.params['restrictedfiles']['onlyallow']))
                    and not name_matches_res(file, self.params['restrictedfiles'].get('disallow', []))):
                return open(file, mode, buffering, encoding, errors, newline, closefd, opener)
            else:
                raise InvalidAction(f"You are not allowed to open '{file}'.")
                
        # (mct63) Function that creates stub invalid function.
        def create_invalid_func(name):
            def invalid_func(*args, **kwargs):
                raise InvalidAction(f"You are not allowed to use '{name}'!")
            return invalid_func
        
        # (mct63) Checks what is being imported and makes sure it is allowed. If it is not, the thing that 
        # is not allowed is replaced by an 'invalid function'. If it is an attribute then it is 
        # not included since I could not think of a better thing to do. Could let it raise
        #  'AttributeNotFound' exception and then check if this was caused from removing the 
        # attribute from the module but given how unlikely this is its not worth it at this time.
        def new_import(name, *args, **kwargs):
            module = __import__(name, *args, **kwargs)
            restricted_module = module
            if 'restrictedmodules' in self.params and name in self.params['restrictedmodules']:
                NewModuleType = type('module', (types.ModuleType,), {})
                restricted_module = NewModuleType(name)
                for var in dir(module):
                    if (('onlyallow' not in self.params['restrictedmodules'][name] or
                            name_matches_res(var, self.params['restrictedmodules'][name]['onlyallow'])) and
                            not name_matches_res(var, self.params['restrictedmodules'][name].get('disallow', []))):
                        setattr(restricted_module, var, getattr(module, var))
                    elif callable(getattr(module, var)):
                        setattr(restricted_module, var, create_invalid_func(f'{name}.{var}'))
                    else:
                        try:
                            setattr(NewModuleType, var, property(create_invalid_func(f'{name}.{var}')))
                        except TypeError:
                            # Some attributes can not be set to a property so we ignore them.
                            continue

            return restricted_module

        # (mct63) Insure print always prints to the redirected stdout and not actual stdout.
        # (rjl83) Also keep track of print quantity and raise ExcessiveOutput if too much is generated.
        # (rjl83) I can't see why mct63 (above) prevents printing to files, so I have allowed the value
        # of a file parameter (if given) to be passed on to the actual print. 

        # Need to clone the object being printed first, as some dreadful students mutate objects in the implementation of str!
        # We also need to prevent any output if the print function is called recursively, e.g. via a print student inside
        # a custom __str__ method (since our overridden print calls str on the object to gets its length).
        def new_print(*values, sep=' ', end='\n', file=None, flush=False):
            if self.running:  # Prevent any output if called recursively.
                return None
            for value in values:
                try:
                    clone = copy.deepcopy(value)
                    self.running = True
                    length = len(str(clone))  # This is where recursion could occur if student prints in __str__.
                    self.running = False
                    CodeTrap.output_chars += length
                except:
                    pass
            if CodeTrap.output_chars > self.params['maxoutputbytes']:
                raise ExcessiveOutput()
            return print(*values, sep=sep, end=end, file=file)
            
        # force 'input' to echo stdin to stdout
        if self.params['echostandardinput']:
            def new_input(prompt=''):
                """ Replace the standard input prompt with a cleverer one. """
                try:
                    s = input(prompt)
                except EOFError:
                    raise OutOfInput()
                print(s)
                return s
        else:
            new_input = input
        
        # (mct63) Create a new builtins dictionary, redfining any functions that are not allowed.
        new_builtins = {key:value for key, value in __builtins__.items()}
        new_builtins['open'] = new_open
        new_builtins['input'] = new_input
        new_builtins['print'] = new_print
        new_builtins['__import__'] = new_import

        if 'proscribedbuiltins' in self.params:
            for func in self.params['proscribedbuiltins']:
                new_builtins[func] = create_invalid_func(func)

        # This would be nice but it can mess with testing code.
        # for func in self.params['proscribedfunctions']:
        #         new_builtins[func] = create_invalid_func(func)
        
        global_dict = {
            '__builtins__': new_builtins,
            '__name__': '__main__'
        }
        if 'usesnumpy' in self.params and self.params['usesnumpy']:
            import numpy as np
            global_dict['np'] = np

        return global_dict

    def __enter__(self):
        if 'MPLCONFIGDIR' not in os.environ or os.environ['MPLCONFIGDIR'].startswith('/home'):
            import tempfile
            os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        self.old_path = os.environ["PATH"]
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        os.environ["PATH"] = ''     # (mct63) Get rid of PATH to make it harder to execute commands.
        return self

    def __exit__(self, *args):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        os.environ["PATH"] = self.old_path

    def exec(self):
        """ Run the code. Output to stdout and stderr is stored and
            returned on a call to read
        """
        if self.seconds_remaining <= 1:
            print("Out of time. Aborted.", file=sys.stderr)
        else:
            with Watchdog(self.seconds_remaining):
                try:
                    exec(self.run_code, self.scoped_globals)
                except OutOfInput:
                    print("'input' function called when no input data available.",
                          file=sys.stderr)
                except ExcessiveOutput:
                    print("Excessive output ... job aborted",
                          file=sys.stderr)
                except Watchdog:
                    print("Time limit exceeded", file=sys.stderr)
                # (mct63) Catch any invalid actions.
                except InvalidAction as e:
                    print(f"Invalid Action: {e}", file=sys.stderr)
                except Exception:
                    etype, value, tb = sys.exc_info()
                    tb_tuples = traceback.extract_tb(tb)
                    new_tb = []
                    for filename, linenumber, scope, text in tb_tuples:
                        if filename == "<string>":
                                new_tb.append((
                                    "__source.py",
                                    linenumber,
                                    scope,
                                    self.run_code.splitlines()[linenumber - 1].strip()
                                ))
                    print("Traceback (most recent call last):", file=sys.stderr)
                    print(''.join(traceback.format_list(new_tb)), end='', file=sys.stderr)
                    print(traceback.format_exception_only(etype, value)[-1], end='', file=sys.stderr)
                except SystemExit:
                    print("Unexpected termination: Please do not call exit() or quit().",
                          file=sys.stderr)
                except KeyboardInterrupt:
                    print("KeyboardInterrupt", file=sys.stderr)
                except GeneratorExit:
                    print("GeneratorExit", file=sys.stderr)

                # (mct63) Might as well catch the base exception in case something very strange happens.
                # For example intentionally raiseing the BaseException to try and skip all of this. 
                except BaseException:
                    print("Caught BaseException. You did something very strange to get this message.",
                          file=sys.stderr)



    def read(self):
        """ Get the output and error from the exec
        """
        return sys.stdout.getvalue(), sys.stderr.getvalue()


class PyTask(languagetask.LanguageTask):
    """A PyTask manages compiling (almost a NOP) and executing of a Python3 program.
    """
    def __init__(self, params, code=None):
        """Initialisation is delegated to the superclass.
        """
        super().__init__(params, code)
        self.executable_built = False

    def compile(self, make_executable=False):
        """A No-op for Python.
        """
        pass

    def discard_executable(self):
        """A no-op for python"""
        pass

    def run_code(self, standard_input=None):
        """Run code using Aaron's CodeTrap
        """
        sys.stdin = io.StringIO(standard_input)
        with CodeTrap(self.code, self.params, floor(self.seconds_remaining())) as runner:
            runner.exec()
            output, error = runner.read()
        self.stdout, self.stderr = output, error
        return output, error

