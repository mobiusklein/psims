import io
import json

with open("./psims/controlled_vocabulary/vendor/record.json") as fh:
    index = json.load(fh)


def translate(self, symbol_table):
    return ''.join([symbol_table.get(c, c) for c in self])


def as_rest_table(data, full=False):
    """
    >>> from report_table import as_rest_table
    >>> data = [('what', 'how', 'who'),
    ...         ('lorem', 'that is a long value', 3.1415),
    ...         ('ipsum', 89798, 0.2)]
    >>> print as_rest_table(data, full=True)
    +-------+----------------------+--------+
    | what  | how                  | who    |
    +=======+======================+========+
    | lorem | that is a long value | 3.1415 |
    +-------+----------------------+--------+
    | ipsum |                89798 |    0.2 |
    +-------+----------------------+--------+

    >>> print as_rest_table(data)
    =====  ====================  ======
    what   how                   who
    =====  ====================  ======
    lorem  that is a long value  3.1415
    ipsum                 89798     0.2
    =====  ====================  ======

    """
    data = data if data else [['No Data']]
    table = []
    # max size of each column
    sizes = list(map(max, zip(*[[len(str(elt)) for elt in member]
                                for member in data])))
    num_elts = len(sizes)

    if full:
        start_of_line = '| '
        vertical_separator = ' | '
        end_of_line = ' |'
        line_marker = '-'
    else:
        start_of_line = ''
        vertical_separator = '  '
        end_of_line = ''
        line_marker = '='

    meta_template = vertical_separator.join(['{{{{{0}:{{{0}}}}}}}'.format(i)
                                             for i in range(num_elts)])
    template = '{0}{1}{2}'.format(start_of_line,
                                  meta_template.format(*sizes),
                                  end_of_line)
    # determine top/bottom borders
    if full:
        to_separator = {"|": "+-"}
    else:
        to_separator = {"|": "+"}
    start_of_line = translate(start_of_line, to_separator)
    vertical_separator = translate(vertical_separator, to_separator)
    end_of_line = translate(end_of_line, to_separator)
    separator = '{0}{1}{2}'.format(start_of_line,
                                   vertical_separator.join(
                                       [x*line_marker for x in sizes]),
                                   end_of_line)
    # determine header separator
    th_separator_tr = "".maketrans('-', '=')
    start_of_line = translate(start_of_line, th_separator_tr)
    line_marker = translate(line_marker, th_separator_tr)
    vertical_separator = translate(vertical_separator, th_separator_tr)
    end_of_line = translate(end_of_line, th_separator_tr)
    th_separator = '{0}{1}{2}'.format(start_of_line,
                                      vertical_separator.join(
                                          [x*line_marker for x in sizes]),
                                      end_of_line)
    # prepare result
    table.append(separator)
    # set table header
    titles = data[0]
    table.append(template.format(*titles))
    table.append(th_separator)

    for d in data[1:-1]:
        table.append(template.format(*d))
        if full:
            table.append(separator)
    table.append(template.format(*data[-1]))
    table.append(separator)
    return '\n'.join(table)


def markdown_table(data):
    buffer = io.StringIO()
    header = data[0]
    body = data[1:]
    n_cols = len(header)
    buffer.write("|")
    for col in header:
        buffer.write(" ")
        buffer.write(col)
        buffer.write(" |")
    buffer.write("\n|")
    for i in range(n_cols):
        buffer.write(" ")
        buffer.write(" :---: |")
    buffer.write("\n")
    for row in body:
        buffer.write("|")
        for col in row:
            buffer.write(" ")
            buffer.write(col)
            buffer.write(" |")
        buffer.write("\n")
    return buffer.getvalue()


table_data = [["Name", "Version", "Checksum"]]
for name, traits in index.items():
    row = [name, traits['version'] if traits['version'] else "-", traits['checksum']]
    table_data.append(row)

print(markdown_table(table_data))
