"""Code for parsing and checking a student's submission, using the
   pycparser class (https://github.com/eliben/pycparser)
   This is a support class for the ENCE260 C question type template
"""
import enum
import re
import support.pycparser as pycparser
from collections import Counter

TEMP_FILENAME = '__temp_source.c'


class IDType(enum.Enum):
    """The ID types used by pycparser"""
    Type = 0
    Function = 1
    Struct = 2
    Pointer = 3
    Array = 4
    Variable = 5


class ParseError(Exception):
    pass


class CParser:
    """The C Parser and support methods. Takes a filename as a parameter
       and does an initial parse to an AST when constructed.
    """

    def __init__(self, source_code, params):
        """Initialise, building the AST of the code in the given file.
           Raise ParseError (????) if it breaks.
           Params is the dictionary of template parameters. Relevant ones
           for this class are:
              1. All the ones defining legal variable names, namely
                'validvariablenames', 'variableregex', 'typeregex',
                'functionregex', 'structregex', 'pointerregex', 'arrayregex'
              2. requiredfuncdecls
        """
        with open(TEMP_FILENAME, 'w') as temp_file:
            temp_file.write(source_code)
        self.ast = pycparser.parse_file(
            TEMP_FILENAME,
            use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E', r'-I./support/utils/fake_libc_include']
        )

        self.params = params
        self.declared_functions = self.declared_functions_dict()
        self.global_variables = self.declared_globals_list()

    def illegal_called_functions(self) -> list:
        """Return a list of all names in illegal_names that are called by the code,
           i.e. are found in the AST.
        """
        bad_used = []
        illegal_names = self.params['proscribedfunctions']

        class FoulFinder(pycparser.c_ast.NodeVisitor):

            def visit_FuncCall(self, node):
                """A function has been called, so check its name
                   against the bad ones."""
                try:
                    name = node.name.name
                    if name in illegal_names:
                        bad_used.append(name)
                except AttributeError:
                    pass  # either not calling a function (??) or it's not named.
                self.generic_visit(node)

        visitor = FoulFinder()
        visitor.visit(self.ast)
        return bad_used

    def declared_functions_dict(self) -> dict:
        """Return a dictionary with the keys being all functions declared and
           values being the function lengths
        """
        function_dict = {}

        def kind_of(node):
            return type(node).__name__

        class FuncCounter(pycparser.c_ast.NodeVisitor):

            def visit_FuncDef(self, node):
                visit_guide = {
                    "FuncDef": lambda f: [f.body],
                    "For": lambda f: [f.stmt],
                    "While": lambda f: [f.stmt],
                    "DoWhile": lambda f: [f.stmt],
                    "If": lambda f: [a for a in [f.iftrue, f.iffalse]
                                     if a is not None],
                    "Switch": lambda f: [f.stmt],
                    "Compound": lambda f: f.block_items
                }

                def count_statements(kind, node):
                    """Number of statements in the given node and its children"""
                    count = 1
                    if kind == "Compound":
                        count = 0
                    children = visit_guide.get(kind, lambda f: [])(node)
                    if children:
                        count += sum(count_statements(kind_of(child), child) for child in children)
                    return count

                # Disregard def itself
                num_statements = count_statements("FuncDef", node) - 1
                function_dict[node.decl.name] = num_statements

        visitor = FuncCounter()
        visitor.visit(self.ast)
        return function_dict

    def declared_globals_list(self) -> list:
        """Returns a list of all globally defined variables.
           The list contains tuples of 'name', 'line_num' pairs."""

        def kind_of(node):
            return type(node).__name__
        
        globals_list = []
        for node in self.ast.ext:
            if kind_of(node) == 'Decl' and kind_of(node.type) != 'FuncDecl':
                # node.name is None when struct is decleared.
                if node.name is not None and not ('static' in node.storage and self.params.get('allowmodulestatics', False)):
                    globals_list.append((node.name, node.coord.line))
        
        return globals_list

    def too_long_funcs(self, max_length) -> list:
        """Return a list of the functions that exceed the given max_length.
           Each list element is a tuple of the function name and the number of statements
           in its body."""

        functions = self.declared_functions
        bad_funcs = [(func, length) for (func, length) in functions.items() if length > max_length]
        return bad_funcs

    def missing_funcs(self) -> list:
        """Return a list of all the functions that should have been declared but weren't
        """
        functions = self.declared_functions
        required_func_decls = self.params['requiredfuncdecls']
        missing = [f for f in required_func_decls if f not in functions]
        return missing

    def used_constructs(self) -> Counter:
        """ Count how many times the various language features are used.
            Return a Counter object mapping construct->count
            Not fully complete, but good enough.
        """
        constructs = Counter()

        class ConstructFinder(pycparser.c_ast.NodeVisitor):
            def visit_Break(self, node):
                constructs['break'] += 1
                self.generic_visit(node)

            def visit_Case(self, node):
                constructs['case'] += 1
                self.generic_visit(node)

            def visit_Cast(self, node):
                constructs['cast'] += 1
                self.generic_visit(node)

            def visit_Continue(self, node):
                constructs['continue'] += 1
                self.generic_visit(node)

            def visit_Default(self, node):
                constructs['default'] += 1
                self.generic_visit(node)

            def visit_DoWhile(self, node):
                constructs['do'] += 1
                self.generic_visit(node)

            def visit_Enum(self, node):
                constructs['enum'] += 1
                self.generic_visit(node)

            def visit_For(self, node):
                constructs['for'] += 1
                self.generic_visit(node)

            def visit_Goto(self, node):
                constructs['goto'] += 1
                self.generic_visit(node)

            def visit_Ife(self, node):
                constructs['if'] += 1
                self.generic_visit(node)

            def visit_Return(self, node):
                constructs['return'] += 1
                self.generic_visit(node)

            def visit_Struct(self, node):
                constructs['struct'] += 1
                self.generic_visit(node)

            def visit_Switch(self, node):
                constructs['switch'] += 1
                self.generic_visit(node)

            def visit_TernaryOp(self, node):
                constructs['ternary'] += 1
                constructs[':?'] += 1
                self.generic_visit(node)

            def visit_Typedef(self, node):
                constructs['typedef'] += 1
                self.generic_visit(node)

            def visit_Union(self, node):
                constructs['union'] += 1
                self.generic_visit(node)

            def visit_While(self, node):
                constructs['while'] += 1
                self.generic_visit(node)

            def visit_Pragma(self, node):
                constructs['pragma'] += 1
                self.generic_visit(node)

        visitor = ConstructFinder()
        visitor.visit(self.ast)
        return constructs

    def identifier_errors(self):
        """Return a list of all identifiers used in the program that do not
           follow the approved form. Each element in the returned list is
           a triple (bad_identifier, ID_Type, line_number).
           Ignore any names that are in the set of standard typedefs.
        """
        fine_names = ['c', 'i', 'j', 'k', 'm', 'n', 's', 't', 'v', 'x', 'y', 'z']
        fine_pointer_names = ['s', 'p'] + ['p' + ok for ok in fine_names] + self.params['validvariablenames']
        fine_names += self.params['validvariablenames']
        ignore_names = CParser.std_typedefs()
        names = []
        rgx = {}

        rgx[IDType.Variable] = re.compile(self.params['variableregex'])
        rgx[IDType.Type] = re.compile(self.params['typeregex'])
        rgx[IDType.Function] = re.compile(self.params['functionregex'])
        rgx[IDType.Struct] = re.compile(self.params['structregex'])
        rgx[IDType.Pointer] = re.compile(self.params['pointerregex'])
        rgx[IDType.Array] = re.compile(self.params['arrayregex'])

        class IdFinder(pycparser.c_ast.NodeVisitor):
            def visit_TypeDecl(self, node):
                if node.declname is not None:
                    names.append((node.declname, IDType.Type, node.coord.line))

            def visit_Decl(self, node):
                if node.name is not None:
                    if isinstance(node.type, pycparser.c_ast.FuncDecl):
                        names.append((node.name, IDType.Function, node.coord.line))
                        if node.type.args is not None:
                            self.generic_visit(node.type.args)
                    elif isinstance(node.type, pycparser.c_ast.PtrDecl):
                        names.append((node.name, IDType.Pointer, node.coord.line))
                    elif isinstance(node.type, pycparser.c_ast.ArrayDecl):
                        names.append((node.name, IDType.Array, node.coord.line))
                    else:
                        names.append((node.name, IDType.Variable, node.coord.line))
                elif isinstance(node.type, pycparser.c_ast.Struct):
                    self.visit_Struct(node.type)

            def visit_Struct(self, node):
                if node.name is not None:
                    names.append((node.name, IDType.Struct, node.coord.line))
                self.generic_visit(node)

        def name_is_ok(name, kind):
            if kind is IDType.Type and name in ignore_names:
                return True
            if kind in [IDType.Variable, IDType.Array] and name in fine_names:
                return True
            if kind in [IDType.Variable, IDType.Array] and name[:-1] in fine_names and name[-1].isdigit():
                return True
            if kind is IDType.Pointer and name in fine_pointer_names:
                return True
            if kind is IDType.Pointer and name[:-1] in fine_pointer_names and name[-1].isdigit():
                return True
            if rgx[kind].match(name):
                return True
            return False

        visitor = IdFinder()
        visitor.visit(self.ast)
        return [n for n in names if not name_is_ok(n[0], n[1])]

    @staticmethod
    def std_typedefs():
        """Return a set of the standard C typedefs, defined in the pycparser
           support file _fake_typedefs.h
        """
        typedefs = set()
        with open("./support/utils/fake_libc_include/_fake_typedefs.h") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("typedef"):
                parts = line.split(' ')
                new_type = parts[-1].strip(';')
                typedefs.add(new_type)
        return typedefs