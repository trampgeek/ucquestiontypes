import sys, json

NUM_ROWS = 4
NUM_VARS = 2
def main():
    #args = {param.split('=')[0]: param.split('=')[1] for param in sys.argv[1:]}

    num_cols = NUM_VARS + 1
    width = 100 / num_cols
    html = '<table class="deskcheck" style="border-collapse: collapse;" border="1">';  
    colgroup = '<colgroup>'
    for i in range(num_cols): 
        colgroup += f'<col style="width: {width}%">'
    colgroup += '</colgroup>'
    html += colgroup + '<tbody>';
    html += f'<tr><td></td><td colspan="{vars}"><strong>Variables</strong></td></tr>'
    html += '<tr><td><strong>&nbsp;Line number&nbsp;</strong></td>'
    for j in range(NUM_VARS):
        html += '<td><strong><input class="coderunner-ui-element" name="variable_name"></strong></td>'
    
    html += '</tr>';
    for i in range(NUM_ROWS):
        html += '<tr><td><input class="coderunner-ui-element" name="line_number"></td>'
        for j in range(NUM_VARS):
            html += '<td><input class="coderunner-ui-element" name="variable_value"></td>'
        html += '</tr>'
    html += '</tbody></table>'


    
    print(json.dumps({'html': html}))


main()




