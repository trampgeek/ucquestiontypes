"""All the style checking code for Python3"""

from io import BytesIO
import os
import subprocess
import ast
import tokenize
import token
import re
import shutil
from collections import defaultdict

class StyleChecker:
    def __init__(self, prelude, student_answer, params):
        self.prelude = prelude
        self.student_answer = student_answer
        self.params = params
        self.function_call_map = None
        self._tree = None

    @property
    def tree(self):
        if self._tree is None:
            self._tree = ast.parse(self.student_answer)
        return self._tree

    def style_errors(self):
        """Return a list of errors from local style checks plus pylint and/or mypy
        """
        errors = []
        source = open('__source.py', 'w', encoding="utf-8")
        code_to_check = self.prelude + self.student_answer
        prelude_len = len(self.prelude.splitlines())
        source.write(code_to_check)
        source.close()
        env = os.environ.copy()
        env['HOME'] = os.getcwd()
        pylint_opts = self.params.get('pylintoptions',[])
        precheckers = self.params.get('precheckers', ['pylint'])
        result = ''

        if 'pylint' in precheckers:
            try:  # Run pylint
                cmd = 'python3.9 -m pylint ' + ' '.join(pylint_opts) + ' __source.py'
                result = subprocess.check_output(cmd,
                                             stderr=subprocess.STDOUT,
                                             universal_newlines=True,
                                             env=env,
                                             shell=True)
            except Exception as e:
                result = e.output
                
            else:
                # (mct63) Abort if there are any comments containing 'pylint:'.
                try:
                    tokenizer = tokenize.tokenize(BytesIO(self.student_answer.encode('utf-8')).readline)
                    for token_type, token_text, *_ in tokenizer:
                        if token_type == tokenize.COMMENT and 'pylint:' in token_text:
                            errors.append("Comments can not include 'pylint:'")
                            break
        
                except Exception:
                    errors.append("Something went wrong while parsing comments. Report this.")

            if "Using config file" in result:
                result = '\n'.join(result.splitlines()[1:]).split()

        if result == '' and 'mypy' in precheckers:
            code_to_check = 'from typing import List as list, Dict as dict, Tuple as tuple, Set as set, Any\n' + code_to_check
            with open('__source2.py', 'w', encoding='utf-8') as outfile:
                outfile.write(code_to_check)
            cmd = 'python3.8 -m mypy --no-error-summary --no-strict-optional __source2.py'
            try: # Run mypy
                subprocess.check_output(cmd,  # Raises an exception if there are errors
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True,
                                     env=env,
                                     shell=True)
            except Exception as e:
                result = e.output
                line_num_fix = lambda match: "Line " + str(int(match[1]) - 1 - prelude_len) + match[2]
                result = re.sub(r'__source2.py:(\d+)(.*)', line_num_fix, result)

        if result == '' and self.params.get('requiretypehints', False):
            bad_funcs = self.check_type_hints()
            for fun in bad_funcs:
                result += f"Function '{fun}' does not have correct type hints\n"

        if result:
            errors = result.strip().splitlines()
            errors.append("Sorry, but your code doesn't pass the style checks.")

        return errors
    
    def prettied(self, construct):
        """Expand, if possible, the name of the given Python construct to a more
           user friendly version, e.g. 'listcomprehension' -> 'list comprehension'
        """
        expanded = {
            'listcomprehension': 'list comprehension',
            'while': 'while loop',
            'for': 'for loop',
            'try': 'try ... except statement',
            'dictcomprehension': 'dictionary comprehension',
            'slice': 'slice'
        }
        if construct in expanded:
            return expanded[construct]
        else:
            return f"{construct} statement"

    def local_errors(self):
        """Perform various local checks as specified by the current set of
           template parameters.
        """
        errors = []

        for banned in self.params.get('proscribedsubstrings', []):
            if banned in self.student_answer:
                errors.append(f"The string '{banned}' is not permitted anywhere in your code.")

        for required in self.params.get('requiredsubstrings', []):
            if isinstance(required, str) and required not in self.student_answer:
                errors.append(f'The string "{required}" must occur somewhere in your code.')
            elif isinstance(required, dict): 
                if 'pattern' in required and not re.findall(required['pattern'], self.student_answer):
                    errors.append(required['errormessage'])
                elif 'string' in required and required['string'] not in self.student_answer:
                    errors.append(required['errormessage'])

        if self.params.get('banglobalcode', True):
            errors += self.find_global_code()

        if not self.params.get('allownestedfunctions', True):
            # Except for legacy questions or where explicitly allowed, nested functions are banned
            nested_funcs = self.find_nested_functions()
            for func in nested_funcs:
                errors.append("Function '{}' is defined inside another function".format(func))

        max_length = self.params['maxfunctionlength']
        bad_funcs = self.find_too_long_funcs(max_length)
        for func, count in bad_funcs:
            errors.append("Function '{}' is too long\n({} statements, max is {})"
                          "".format(func, count, max_length))

        bad_used = self.find_illegal_functions()
        for name in bad_used:
            errors.append("You called the banned function '{}'.".format(name))

        missing_funcs = self.find_missing_required_function_calls()
        for name in missing_funcs:
            errors.append("You forgot to use the required function '{}'.".format(name))

        missing_funcs = self.find_missing_required_function_definitions()
        for name in missing_funcs:
            errors.append("You forgot to define the required function '{}'.".format(name))

        missing_constructs = self.find_missing_required_constructs()
        for reqd in missing_constructs:
            expanded = self.prettied(reqd)
            errors.append(f"Your program must include at least one {expanded}.")

        bad_constructs = self.find_illegal_constructs()
        for notallowed in bad_constructs:
            expanded = self.prettied(notallowed)
            errors.append(f"Your program must not include any {expanded}s.")

        num_constants = len([line for line in self.student_answer.split('\n') if re.match(' *[A-Z_][A-Z_0-9]* *=', line)])
        if num_constants > self.params['maxnumconstants']:
            errors.append("You may not use more than " + str(self.params['maxnumconstants']) + " constants.")

        # (mct63) Check if anything restricted is being imported.
        if 'restrictedmodules' in self.params:
            restricted = self.params['restrictedmodules']
            for import_name, names in self.find_all_imports().items():
                if import_name in restricted:
                    if restricted[import_name].get('onlyallow', None) == []:
                        errors.append("Your program should not import anything from '{}'.".format(import_name))
                    else:
                        for name in names:
                            if (('onlyallow' in restricted[import_name] and name not in restricted[import_name]['onlyallow']) or
                                    name in restricted[import_name].get('disallow', [])):
                                errors.append("Your program should not import '{}' from '{}'.".format(name, import_name))

        return errors

    def find_all_imports(self):
        """Returns a dictionary mapping in which the keys are all modules
           being imported and the values are a list of what things within
           the module are being modules. An empty list indicates the entire
           module is imported."""
        found_imports = {}
        class ImportFinder(ast.NodeVisitor):
            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name not in found_imports:
                        found_imports[alias.name] = []
                self.generic_visit(node)
            def visit_ImportFrom(self, node):
                if node.module not in found_imports:
                    found_imports[node.module] = []
                for alias in node.names:
                    found_imports[node.module].append(alias.name)
                self.generic_visit(node)

        visitor = ImportFinder()
        visitor.visit(self.tree)
        return found_imports

    def find_all_function_calls(self):
        """Return a dictionary mapping in which the keys are all functions
           called by the source code and values are a list of
           (line_number, nesting_depth) tuples."""
        class FuncFinder(ast.NodeVisitor):

            def __init__(self, *args, **kwargs):
                self.depth = 0
                self.found_funcs = defaultdict(list)
                super().__init__(*args, **kwargs)

            def visit_FunctionDef(self, node):
                """ Every time we enter a function, we get 'deeper' into the code.
                    We want to note how deep a function is when we find its call."""
                self.depth += 1
                self.generic_visit(node)
                self.depth -= 1

            def visit_Call(self, node):
                """A function has been called, so check its name
                   against the given one."""
                try:
                    if 'id' in dir(node.func):
                        name = node.func.id
                    else:
                        name = node.func.attr
                    # Line numbers are 1-indexed, so decrement by 1
                    self.found_funcs[name].append((node.lineno - 1, self.depth))
                except AttributeError:
                    pass  # either not calling a function (??) or it's not named.
                self.generic_visit(node)

        if self.function_call_map is None:
            visitor = FuncFinder()
            visitor.visit(self.tree)
            self.function_call_map = visitor.found_funcs
        return self.function_call_map


    def find_defined_functions(self):
        """Find all the functions defined."""
        defined = set()
        class FuncFinder(ast.NodeVisitor):

            def __init__(self):
                self.prefix = ''

            def visit_ClassDef(self, node):
                old_prefix = self.prefix
                self.prefix += node.name + '.'
                self.generic_visit(node)
                self.prefix = old_prefix

            def visit_FunctionDef(self, node):
                defined.add(self.prefix + node.name)
                old_prefix = self.prefix
                self.prefix += node.name + '.'
                self.generic_visit(node)
                self.prefix = old_prefix

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

        visitor = FuncFinder()
        visitor.visit(self.tree)
        return defined


    def constructs_used(self):
        """Return a set of all constructs encountered in the parse tree"""
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

        visitor = ConstructFinder()
        visitor.visit(self.tree)
        return constructs_seen

    def check_type_hints(self):
        """Return a list of the names of functions that don't have full type hinting."""
        unhinted = []
        class MyVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                if node.returns is None or any([arg.annotation is None for arg in node.args.args]):
                    unhinted.append(node.name)

        visitor = MyVisitor()
        tree = self.tree
        visitor.visit(self.tree)
        return unhinted

    def find_function_calls(self, name):
        """Look for occurances of a specific function call"""
        return self.find_all_function_calls().get(name, [])


    def find_illegal_functions(self):
        """Find a set of all the functions that the student uses
           that they are not allowed to use. """
        func_calls = self.find_all_function_calls()
        return func_calls.keys() & set(self.params['proscribedfunctions'])


    def find_missing_required_function_calls(self):
        """Find a set of the required functions that the student fails to use"""
        func_calls = self.find_all_function_calls()
        return set(self.params['requiredfunctioncalls']) - func_calls.keys()


    def find_missing_required_function_definitions(self):
        """Find a set of required functions that the student fails to define"""
        func_defs = self.find_defined_functions()
        return set(self.params['requiredfunctiondefinitions']) - func_defs


    def find_illegal_constructs(self):
        """Find all the constructs that were used but not allowed"""
        constructs = self.constructs_used()
        return constructs & set(self.params['proscribedconstructs'])


    def find_missing_required_constructs(self):
        """Find which of the required constructs were not used"""
        constructs = self.constructs_used()
        return set(self.params['requiredconstructs']) - constructs


    def find_too_long_funcs(self, max_length):
        """Return a list of the functions that exceed the given max_length
           Each list element is a tuple of the function name and the number of statements
           in its body."""

        bad_funcs = []

        class MyVisitor(ast.NodeVisitor):

            def visit_FunctionDef(self, node):

                def count_statements(node):
                    """Number of statements in the given node and its children"""
                    count = 1
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                        count = 0
                    else:
                        for attr in ['body', 'orelse', 'finalbody']:
                            if hasattr(node, attr):
                                children = node.__dict__[attr]
                                count += sum(count_statements(child) for child in children)
                    return count

                num_statements = count_statements(node) - 1 # Disregard def itself
                if num_statements > max_length:
                    bad_funcs.append((node.name, num_statements))

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

        visitor = MyVisitor()
        visitor.visit(self.tree)
        return bad_funcs


    def find_global_code(self):
        """Return a list of error messages relating to the existence of
           any global assignment, for, while and if nodes. Ignores
           global assignment statements with an ALL_CAPS target."""

        global_errors = []
        class MyVisitor(ast.NodeVisitor):
            def visit_Assign(self, node):
                if node.col_offset == 0:
                    if len(node.targets) > 1:
                        global_errors.append(f"Multiple targets in global assignment statement at line {node.lineno}")
                    elif not node.targets[0].id.isupper():
                        global_errors.append(f"Global assignment statement at line {node.lineno}")

            def visit_For(self, node):
                if node.col_offset == 0:
                    global_errors.append(f"Global for loop at line {node.lineno}")

            def visit_While(self, node):
                if node.col_offset == 0:
                    global_errors.append(f"Global while loop at line {node.lineno}")

            def visit_If(self, node):
                if node.col_offset == 0:
                    global_errors.append(f"Global if statement at line {node.lineno}")

        visitor = MyVisitor()
        visitor.visit(self.tree)
        return global_errors


    def find_nested_functions(self):
        """Return a list of functions that are declared with non-global scope"""
        bad_funcs = []

        class MyVisitor(ast.NodeVisitor):
            is_visiting_func = False

            def visit_FunctionDef(self, node):
                if self.is_visiting_func:
                    bad_funcs.append(node.name)
                self.is_visiting_func = True
                self.generic_visit(node) # Visit all children recursively
                self.is_visiting_func = False

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

        visitor = MyVisitor()
        visitor.visit(self.tree)
        return bad_funcs
