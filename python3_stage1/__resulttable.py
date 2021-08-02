"""Code for building and managing the result table for the tests.
   The result table itself (the 'table' field of an object of this class)
    is a list of lists of strings. The first row is the header row.
   Columns are "Test", "Input" (optional), "Expected", "Got", "iscorrect", "ishidden"
"""
import html
import re
from collections import defaultdict

MAX_STRING_LENGTH = 4000  # 4k is default maximum string length


class ResultTable:
    def __init__(self, params):
        self.params = params
        self.mark = 0
        self.table = None
        self.failed_hidden = False
        self.aborted = False
        self.has_stdins = False
        self.has_tests = False
        self.hiding = False
        self.num_failed_tests = 0
        self.missing_tests = 0
        self.global_error = ''
        self.column_formats = None
        self.images = defaultdict(list)
        default_params = {
            'stdinfromextra': False,
            'strictwhitespace': True,
            'floattolerance': None,
            'ALL_OR_NOTHING': True
        }
        for param, value in default_params.items():
            if param not in params:
                self.params[param] = value


    def set_header(self, testcases):
        """Given the set of testcases, set the header as the first row of the result table
           and set flags to indicate presence or absence
           of various table columns.
        """
        header = ['iscorrect']
        self.column_formats = ['%s']
        if any(test.testcode.strip() != '' for test in testcases):
            header.append("Test")
            self.has_tests = True
            # If the test code should be rendered in html then set that as column format.
            if any(getattr(test, 'test_code_html', None) for test in testcases):
                self.column_formats.append('%h')
            else:
                self.column_formats.append('%s')

        stdins = [test.extra if self.params['stdinfromextra'] else test.stdin for test in testcases]
        if any(stdin.rstrip() != '' for stdin in stdins):
            header.append('Input')
            self.column_formats.append('%s')
            self.has_stdins = True
        header += ['Expected', 'Got', 'iscorrect', 'ishidden']
        self.column_formats += ['%s', '%s', '%s', '%s']
        self.table = [header]

    def image_column_nums(self):
        """A list of the numbers of columns containing images"""
        return sorted(set([key[0] for key in self.images.keys()]))

    def get_column_formats(self):
        """ An ordered list of the column formats. Columns containing images are forced into %h format.
            Don't have formats for iscorrect and ishidden columns.
        """
        image_columns = self.image_column_nums()
        formats = [self.column_formats[i] if i not in image_columns else '%h' for i in range(len(self.column_formats))]
        return formats[1:-2]

    def get_table(self):
        """Return the current result table, with images added to appropriate cells.
           Columns that contain images anywhere are converted to %h format and existing content in that column
           is html-escaped, newlines replaced with <br> and wrapped in a div.
           """
        result_table = [row[:] for row in self.table]  # Clone the result table

        # Htmlise all columns containing images
        for col_num in self.image_column_nums():
            for row_num in range(1, len(result_table)):
                result_table[row_num][col_num] = self.htmlise(result_table[row_num][col_num])

        # Append images
        for ((col,row), image_list) in self.images.items():
            for image in image_list:
                try:
                    result_table[row][col] += "<br>" + image
                except IndexError:
                    pass  # Testing must have aborted so discard image

        return result_table

    def reset(self):
        if len(self.table) > 1:
            del self.table[1:]
        self.global_error = ''
        self.num_failed_tests = self.mark = 0
        self.failed_hidden = self.hiding = self.aborted = False

    def tests_missed(self, num):
        """Record the fact that we're missing some test results (timeout?)"""
        self.missing_tests = num

    def record_global_error(self, error_message):
        """Record some sort of global failure"""
        self.global_error = error_message

    def add_row(self, testcase, result, error=''):
        """Add a result row to the table for the given test and result"""
        is_correct = self.check_correctness(result + error, testcase.expected)
        row = [is_correct]
        if self.has_tests:
            if getattr(testcase, 'test_code_html', None):
                row.append(testcase.test_code_html)
            else:
                row.append(testcase.testcode)
        if self.has_stdins:
            row.append(testcase.extra if self.params['stdinfromextra'] else testcase.stdin)
        row.append(testcase.expected.rstrip())
        max_len = self.params.get('maxstringlength', MAX_STRING_LENGTH)
        result = sanitise(result.strip('\n'), max_len)

        if error:
            error_message = '*** RUN TIME ERROR(S) ***\n' + sanitise(error, max_len)
            if result:
                result = result + '\n' + error_message
            else:
                result = error_message
        row.append(result)

        if is_correct:
            self.mark += testcase.mark
        else:
            self.num_failed_tests += 1
        row.append(is_correct)
        display = testcase.display.upper()
        is_hidden = (
            self.hiding or
            display == 'HIDE' or
            (display == 'HIDE_IF_SUCCEED' and is_correct) or
            (display == 'HIDE_IF_FAIL' and not is_correct)
        )
        row.append(is_hidden)
        if not is_correct and is_hidden:
            self.failed_hidden = True
        if not is_correct and testcase.hiderestiffail:
            self.hiding = True
        self.table.append(row)
        if error:
            self.aborted = True

    def get_mark(self):
        return self.mark if self.num_failed_tests == 0 or not self.params['ALL_OR_NOTHING'] else 0

    @staticmethod
    def htmlise(s):
        """Convert the given string to html by escaping '<' and '>'.
           Wrap the whole lot in a div tag so the diff checker processes the whole table cell,
           and within that a pre tag for correct laylout.
        """
        return '<div><pre class="tablecell">' + html.escape(s) + '</pre></div>'

    def add_image(self, image_html, column_name, row_num):
        """Store the given html_image for later inclusion in the cell at the given row and given column.
           column_name is the name used for the column in the first (header) row.
           row_num is the row number (0 origin, not including the header row).
        """
        column_num = self.table[0].index(column_name)
        self.images[column_num, row_num + 1].append(image_html)

    def equal_strings(self, s1, s2):
        """ Compare the two strings s1 and s2 (expected and got respectively)
            for equality, with regard to the template parameters
            strictwhitespace and floattolerance.
        """
        s1 = s1.rstrip()
        s2 = s2.rstrip()
        if not self.params['strictwhitespace']:
            # Collapse white space if strict whitespace is not enforced
            s1 = re.sub(r'\s+', ' ', s1)
            s2 = re.sub(r'\s+', ' ', s2)
        if self.params['floattolerance'] is None:
            return s1 == s2
        else:
            # Matching with a floating point tolerance.
            # Use float pattern from Markus Schmassmann at
            # https://stackoverflow.com/questions/12643009/regular-expression-for-floating-point-numbers
            tol = float(self.params['floattolerance'])
            float_pat = r'([-+]?(?:(?:(?:[0-9]+[.]?[0-9]*|[.][0-9]+)(?:[ed][-+]?[0-9]+)?)|(?:inf)|(?:nan)))'
            s1_bits = re.split(float_pat, s1)
            s2_bits = re.split(float_pat, s2)
            if len(s1_bits) != len(s2_bits):
                return False
            match = True
            for bit1, bit2 in zip(s1_bits, s2_bits):
                bit1 = bit1.strip()
                bit2 = bit2.strip()
                try:
                    f1 = float(bit1)
                    f2 = float(bit2)
                    if not (abs(f1 - f2) <= tol or (f1 != 0.0 and abs((f1 - f2) / f1) <= tol)):
                        match = False
                except ValueError:
                    if bit1 != bit2:
                        match = False
            return match

    def check_correctness(self, expected, got):
        """True iff expected matches got with relaxed white space requirements.
           Additionally, if the template parameter floattolerance is set and is
           non-zero, the two strings will be split by a floating-point literal
           pattern and the floating-point bits will be matched to within the
           given absolute tolerance.
        """
        expected_lines = expected.strip().splitlines()
        got_lines = got.strip().splitlines()
        if len(got_lines) != len(expected_lines):
            return False
        else:
            for exp, got in zip(expected_lines, got_lines):
                if not self.equal_strings(exp, got):
                    return False
        return True


def sanitise(s, max_len=MAX_STRING_LENGTH):
    """Replace non-printing chars with escape sequences, right-strip.
       Limit s to max_len by snipping out bits in the middle.
    """
    result = ''
    if len(s) > max_len:
        s = s[0: max_len // 2] + "\n*** <snip> ***\n" + s[-max_len // 2:]
    lines = s.rstrip().splitlines()
    for line in lines:
        for c in line.rstrip() + '\n':
            if c < ' ' and c != '\n':
                if c == '\t':
                    c = r'\t'
                elif c == '\r':
                    c = r'\r'
                else:
                    c = r'\{:03o}'.format(ord(c))
            result += c
    return result.rstrip()
