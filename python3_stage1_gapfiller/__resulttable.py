"""Code for building and managing the result table for the tests.
   The result table itself (the 'table' field of an object of this class)
    is a list of lists of strings. The first row is the header row.
   Columns are "Test", "Input" (optional), "Expected", "Got", "iscorrect", "ishidden"
"""
import html
import re
import base64
from collections import defaultdict
from urllib.parse import quote

MAX_STRING_LENGTH = 4000  # 4k is default maximum string length


class ResultTable:
    def __init__(self, params):
        self.params = params
        self.mark = 0
        self.max_mark = 0
        self.table = None
        self.failed_hidden = False
        self.aborted = False
        self.has_stdins = False
        self.has_tests = False
        self.has_extra = False
        self.has_expected = False
        self.has_got = False
        self.hiding = False
        self.num_failed_tests = 0
        self.num_failed_hidden_tests = 0
        self.missing_tests = 0
        self.global_error = ''
        self.column_formats = {}  # Map from raw column name to format
        self.column_formats_by_hdr = {}  # Map from header name to format
        self.images = defaultdict(list)
        default_params = {
            'stdinfromextra': False,
            'strictwhitespace': True,
            'floattolerance': None,
            'resultcolumns': [['Test', 'testcode'], ['Input', 'stdin'], ['Expected', 'expected'], ['Got', 'got']],
            'ALL_OR_NOTHING': True
        }
        for param, value in default_params.items():
            if param not in params:
                self.params[param] = value

        self.is_file_question = self.params['extra'] == 'files'


    def set_header(self, testcases):
        """Given the set of testcases, set the header as the first row of the result table
           and set flags to indicate presence or absence
           of various table columns.
        """
        header = ['iscorrect']
        required_columns = {}
        for hdr, field, *format in self.params['resultcolumns']:
            required_columns[field] = hdr
            if field == 'extra' and self.is_file_question:
                format = '%h'  # See format_extra function.
            else:
                format = format[0] if format else '%s'
            self.column_formats[field] = format
            self.column_formats_by_hdr[hdr] = format

        if 'testcode' in required_columns and any(test.testcode.strip() != '' for test in testcases):
            header.append(required_columns['testcode'])
            self.has_tests = True

            # *** WHAT WAS THIS ABOUT??? ***
            # If the test code should be rendered in html then set that as column format.
            #if any(getattr(test, 'test_code_html', None) for test in testcases):
            #    self.column_formats.append('%h')
            #else:
            #    self.column_formats.append('%s')

        # If this is a write-a-function file question, the stdin field is hidden regardless.
        # TODO: are there exceptions to this?
        hide_stdin = self.is_file_question and self.params['isfunction']
        if not hide_stdin:
            stdins = [test.extra if self.params['stdinfromextra'] else test.stdin for test in testcases]
            if 'stdin' in required_columns and any(stdin.rstrip() != '' for stdin in stdins):
                header.append(required_columns['stdin'])
                self.has_stdins = True

        if 'extra' in required_columns:
            header.append(required_columns['extra'])
            self.has_extra = True
    
        if 'expected' in required_columns:
            header.append(required_columns['expected'])
            self.has_expected = True

        # *** CONSIDER USE OF GOT IN FILES questions (and others). Can contain error messages. Should always include??
        if 'got' in required_columns:
            header.append(required_columns['got'])
            self.has_got = True

        header += ['iscorrect', 'ishidden']
        self.table = [header]

    def image_column_nums(self):
        """A list of the numbers of columns containing images"""
        return sorted(set([key[0] for key in self.images.keys()]))

    def get_column_formats(self):
        """ An ordered list of the column formats. Columns containing images are forced into %h format.
            Don't have formats for iscorrect and ishidden columns.
        """
        image_columns = self.image_column_nums()
        formats = []
        for i, column_hdr in enumerate(self.table[0]):
            if i in image_columns:
                formats.append('%h')
            else:
                formats.append(self.column_formats_by_hdr.get(column_hdr, '%s'))
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
  
    def format_extra_for_files(self, extra, filename):
        """Format the extra field (which should be the contents of a file). 
           Firstly the file contents are displayed unless the longest line exceeds
           filemaxwidth (or, legacy, filedownloadwidth) or the number of lines
           exceeds filemaxlines (or, legacy, filedownloadlines).
           In addition, a download data URI link is added at the end.
        """
        lines = extra.splitlines()
        max_width = max(self.params.get('filedownloadwidth', 0), self.params.get('filemaxwidth', 0))
        max_lines = max(self.params.get('filedownloadlines', 0), self.params.get('filemaxlines', 0))
        too_wide = len(lines) > 0 and (max(len(line) for line in lines) > max_width)
        too_high = len(lines) > max_lines
        contents = ''
        if extra:
            if not too_wide and not too_high:
                contents += '<pre style="padding-bottom:15px">' + extra + '</pre>'
            quoted = quote(extra)
            link_style = "display: inline-block; padding: 4px 8px; background-color: #6c757d; color: white; text-decoration: none; border-radius: 3px; font-size: 12px; border: none; cursor: pointer;"
            link = f'<a href="data:text/plain;charset=utf-8,{quoted}" download="{filename}" style="{link_style}">Download</a>'
            contents += link
        return contents

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

        if self.has_extra:
            if self.params['extra'] == 'files':
                filename = testcase.stdin.splitlines()[0]
                row.append(self.format_extra_for_files(testcase.extra, filename))
            else:
                row.append(testcase.extra)
            
        if self.has_expected:
            row.append(testcase.expected.rstrip())

        max_len = self.params.get('maxstringlength', MAX_STRING_LENGTH)
        result = sanitise(result.rstrip('\n'), max_len)

        if error:
            error_message = '*** RUN TIME ERROR(S) ***\n' + sanitise(error, max_len)
            if result:
                result = result + '\n' + error_message
            else:
                result = error_message

        if self.has_got:
            row.append(result)

        display = testcase.display.upper()
        self.max_mark += testcase.mark
        if is_correct:
            self.mark += testcase.mark
        else:
            self.num_failed_tests += 1
            if display == 'HIDE':
                self.num_failed_hidden_tests += 1
        row.append(is_correct)

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
        if self.num_failed_tests == 0:
            return self.mark
        # Failed one or more tests
        elif (self.num_failed_tests == self.num_failed_hidden_tests) and self.params.get('failhiddenonlyfract', 0) > 0:
            return self.max_mark * self.params['failhiddenonlyfract']
        elif not self.params['ALL_OR_NOTHING']:
            return self.mark
        else:
            return 0
 

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
           It should be either Expected or Got (all we can handle in this code).
           row_num is the row number (0 origin, not including the header row).
        """
        try:
            column_num = self.table[0].index(column_name)
            self.images[column_num, row_num + 1].append(image_html)
        except (IndexError, ValueError):
            raise Exception(f"Can't insert '{column_name}' image into result table as the column does not exist.")

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
            # except we don't match inf or nan which can be embedded in text strings.
            tol = float(self.params['floattolerance'])
            float_pat = r'([-+]?(?:(?:(?:[0-9]+[.]?[0-9]*|[.][0-9]+)(?:[ed][-+]?[0-9]+)?)))'
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
                    if abs(f1 - f2) > tol * 1.001: # Allow tolerance on the float tolerance!
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
        expected_lines = expected.rstrip().splitlines()
        got_lines = got.rstrip().splitlines()
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
