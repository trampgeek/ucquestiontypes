import json
import ast

class BadLiteral(Exception): pass

def partition(values, num_cols):
    """Return the given list of values partitioned into a 2D array with given number of columns"""
    num_rows = len(values) // num_cols
    table = [[values[row * num_cols + col] for col in range(num_cols)] for row in range(num_rows)]
    return table

def first_error(got_cells, expected_cells):
    """Return the index of the first difference"""
    for i, (got, expect) in enumerate(zip(got_cells, expected_cells)):
        if got != expect:
            return i
    return None  # Shouldn't happen


def parse_literals(lits):
    """Use ast.eval_literal to convert a list of string values into
       a list of Python literal values, which is returned.
       Any parse errors raise BadLiteral(bad_string).
    """
    values = []
    for lit in lits:
        if lit == '':
            values.append(lit)
        else:
            try:
                values.append(ast.literal_eval(lit))
            except:
                raise BadLiteral(lit)
    return values
    

def check_return(got_return, expected_return):
    """Return true if return value is correct, print and
       error and return false otherwise
    """
    try:
        expected_return_value = ast.literal_eval(expected_return)
    except:
        print("Naughty question author: invalid literal for expected return value")
        return False
        
    try:
        got_return_value = ast.literal_eval(got_return)
    except:
        print("Your return value is not valid. Missing quotes perhaps?")
        
    if type(got_return_value) != type(expected_return_value):
        print("Your return value is of the wrong type.")
        print(f"Expected {type(expected_return_value)}, got {type(got_return_value)}")
        return False
        
    if got_return_value != expected_return_value:
        print("Your return value is wrong")
        return False
    
    return True

got = json.loads("""{{ STUDENT_ANSWER | e('py') }}""")
expected = json.loads("""{{ QUESTION.answer | e('py') }}""")

ok = True
got_vars = [s.strip() for s in got['variable_name']]
got_vars_lc = [s.lower() for s in got_vars]
expected_vars = [s.strip() for s in expected['variable_name']]
num_vars = len(expected_vars)
expected_vars_lc = [s.lower() for s in expected_vars]
has_output = 'output' in expected
has_return = 'return_value' in expected

if has_output:
    expected_output = [s.strip() for s in expected['output']]
    got_output = [s.strip() for s in got['output']]

if has_return:
    expected_return = expected['return_value'][0].strip()
    got_return = got['return_value'][0].strip()

if  got_vars != expected_vars:
    # Deal with wrong list of variable names
    if set(got_vars) == set(expected_vars):
        print("Your variable names are in the wrong order")
    elif got_vars_lc == expected_vars_lc:
        print('Variable names must be lower case')
    else:
        print("The variable names in the top row are not right.")
        #print(expected_vars, got_vars)
    ok = False

if ok:
    # Process the list of line numbers
    got_line_nums = [s.strip().lower() for s in got['line_number']]
    expected_line_nums  = [s.strip().lower() for s in expected['line_number']]
    if got_line_nums != expected_line_nums:
        print("The sequence of line numbers is wrong.")
        ok = False

if ok:
    # Process the list of variables
    got_values = partition([s.strip() for s in got['variable_value']], num_vars)
    expected_values = partition([s.strip() for s in expected['variable_value']], num_vars)
    for i, var in enumerate(got_vars):
        try:
            got_var_values = parse_literals([got_values[row][i] for row in range(len(got_values))])
            expected_var_values = parse_literals([expected_values[row][i] for row in range(len(expected_values))])
            if got_var_values != expected_var_values:
                print(f"Your values for the variable '{var}' aren't right.")
                line = first_error(got_var_values, expected_var_values)
                print(f"The first error is at step {line + 1} (line number {got_line_nums[line]}).")
                got = got_var_values[line]
                expected = expected_var_values[line]
                if type(got) != type(expected):
                    print("Your value is of the wrong type.")
                    print(f"Expected {type(expected)}, got {type(got)}")
                ok = False
        except BadLiteral as bl:
            print(f"'{bl}' is an invalid value. Might be missing quotes?")
            ok = False

            
if ok and has_output:
    # Process the output
    if got_output != expected_output:
        print("The output table is wrong")
        step = first_error(got_output, expected_output)
        line_number = got_line_nums[step]
        print(f"The first error is at step {step + 1} (line number {line_number}).")
        ok = False

if ok and has_return:
    ok = check_return(got_return, expected_return)

if ok:
    print("OK")
