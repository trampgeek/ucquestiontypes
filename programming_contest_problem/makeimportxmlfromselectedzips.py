"""Make a question xml export file for a given contest. Takes as a command line
   parameter the name of an output xml file followed by a list of domjudge problem
   zips and outputs to the specified output file a CodeRunner Moodle XML input file
   containing all the selected problems.
"""
import os
import base64
import zipfile
import json
import sys
import io


QUIZ_XML = """<?xml version="1.0" encoding="UTF-8"?>
<quiz>
{questions}
</quiz>"""

QUESTION_XML = """<question type="coderunner">
    <name>
      <text><![CDATA[{question_name}]]></text>
    </name>
    <questiontext format="html">
      <text><![CDATA[<h4>{question_name}</h4>]]></text>
    </questiontext>
    <generalfeedback format="html">
      <text></text>
    </generalfeedback>
    <defaultgrade>1.0000000</defaultgrade>
    <penalty>0.0000000</penalty>
    <hidden>0</hidden>
    <idnumber></idnumber>
    <coderunnertype>programming_contest_problem</coderunnertype>
    <prototypetype>0</prototypetype>
    <allornothing>1</allornothing>
    <penaltyregime>0</penaltyregime>
    <precheck>0</precheck>
    <showsource>0</showsource>
    <answerboxlines>18</answerboxlines>
    <answerboxcolumns>100</answerboxcolumns>
    <answerpreload></answerpreload>
    <globalextra></globalextra>
    <useace></useace>
    <resultcolumns></resultcolumns>
    <template></template>
    <iscombinatortemplate></iscombinatortemplate>
    <allowmultiplestdins></allowmultiplestdins>
    <answer>{answer}</answer>
    <templateparams>{template_params}</templateparams>
    <validateonsave>0</validateonsave>
    <testsplitterre></testsplitterre>
    <language></language>
    <acelang></acelang>
    <sandbox></sandbox>
    <grader></grader>
    <cputimelimitsecs></cputimelimitsecs>
    <memlimitmb></memlimitmb>
    <sandboxparams></sandboxparams>
    <templateparams></templateparams>
    <hoisttemplateparams>1</hoisttemplateparams>
    <twigall>0</twigall>
    <uiplugin></uiplugin>
    <attachments>0</attachments>
    <attachmentsrequired>0</attachmentsrequired>
    <maxfilesize>10240</maxfilesize>
    <filenamesregex></filenamesregex>
    <filenamesexplain></filenamesexplain>
    <displayfeedback>1</displayfeedback>
    <testcases>{support_files}</testcases>
  </question>
"""

def is_solution(pathname):
    """Return true if the pathname looks like it's that of a solution"""
    folders = ['submissions/accepted/', 'Solutions/', 'solutions/', 'solution/', 'soln/']
    return (any(folder in pathname for folder in folders)
            and not pathname.strip().endswith('/')
            and not pathname.split('/')[-1].startswith('.'))


def is_verifier(pathname):
    """Return true if the pathname looks like this is an output verifier zip or cpp file"""
    folders = ['output_verifier', 'output_validator', 'output_validators']
    return (any(folder + '/' in pathname for folder in folders) and
             any(pathname.endswith(ext) for ext in ['.zip', '.cpp', '.c', '.h', '.py']))


def make_utf_8(byte_str):
    """Try to convert bytes to utf-8"""
    return byte_str.decode('utf-8', 'replace')


def make_support_file(filename, file_b64):
    """Return the XML for the <file> element in the support file list for a given
       filename and base-64 encoded contents"""
    return '<file name="{0}" path="/" encoding="base64">{1}</file>'.format(filename, file_b64)


def make_verifier_zip(zippy, verifiers):
    """Given the original ZipFile object and a list of files deemed to be validators,
       return the contents of a zip file to use as a validator as a byte string.
       verifiers is a list of names of files from zippy. If the list has just 1 element
       ending with .zip, the contents of that file are read. Otherwise returns a zip file
       made by zipping up all the given files.
    """
    if len(verifiers) == 1 and verifiers[0].endswith('.zip'):
        return zippy.open(verifiers[0]).read()
    else:
        zip_buffer = io.BytesIO()  #A BytesIO object to hold the zip contents
        
        # Create a zip file in the BytesIO object
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filepath in verifiers:
                filename = filepath.split('/')[-1]
                contents = make_utf_8(zippy.open(filepath).read())
                zip_file.writestr(filename, contents)

        # Seek to the beginning of the BytesIO object
        zip_buffer.seek(0)
        
        # Return the byte contents of the zip file
        return zip_buffer.getvalue()
        
        
def best(solns):
    """Return the best of the set of solutions, with the ordering being
       .py, .cpp, .cc, .java
    """
    def rank(soln):
        ranks = ['py', 'cpp', 'cc', 'java']
        extension = soln.split('.')[-1]
        return ranks.index(extension) if extension in ranks else 4
    
    sorted_solns = sorted(solns, key=rank)
    return sorted_solns[0]


def make_question_xml(problem_name, zip_name):
    """Return the XML for a single question"""
    with open(zip_name, "rb") as infile:
        bytes = infile.read()
        encoded_zip = base64.b64encode(bytes).decode('utf-8')
        files = [(zip_name, encoded_zip)]
        zippy = zipfile.ZipFile(zip_name)
        solns = [member for member in zippy.namelist() if is_solution(member)]
        solns.sort(key=lambda name: 0 if name.endswith('.py') else 1 if name.endswith('.cpp') else 2)
        verifiers = [member for member in zippy.namelist() if is_verifier(member)]
        template_params_dict = {'tests_zip_filename': zip_name}
        soln = ''
        if solns:
            best_soln = best(solns)
            answer_code = make_utf_8(zippy.open(best_soln).read())
            soln = f'<![CDATA[{answer_code}]]>'
            extension = best_soln.split('.')[-1]
            languages = {'py': 'python3', 'py3': 'python3', 'cc': 'cpp', 'cpp': 'cpp'}
            language = languages.get(extension, extension)
            if language == 'python3' and 'raw_input' in answer_code:
                language = 'python2'
            print(f"Found solution {best_soln.split('/')[-1]} for problem {problem_name}")
            template_params_dict["answer_language"] = 'pypy3' if language == 'python3' else language
        if verifiers:
            verifier = make_verifier_zip(zippy, verifiers)
            encoded_verifier = base64.b64encode(verifier).decode('utf-8')
            validator_name = 'output_validator.zip'
            files.append((validator_name, encoded_verifier))
            template_params_dict['validator_zip_filename'] = validator_name
            print(f"Found verifier for problem {problem_name}")
        files_xml = '\n'.join([make_support_file(*file) for file in files])

        template_params = json.dumps(template_params_dict)
    return QUESTION_XML.format(question_name=problem_name,
                               file_b64=encoded_zip,
                               answer=soln,
                               template_params=template_params,
                               support_files=files_xml)



def make_question_list_xml():
    """Return the xml for the list of questions"""
    zips = sys.argv[2:]
    assert all(filename.endswith('.zip') for filename in zips)
    xml = ''
    for name in zips:
        question_name = '.'.join(name.split('.')[:-1])
        xml += make_question_xml(question_name, name)
    return xml


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 makeimportxmlfromselectedzips xmloutputfilename zipfile ...")
        sys.exit(0)
    questions = make_question_list_xml()
    outputfilename = sys.argv[1]
    assert outputfilename.endswith('.xml')
    with open(outputfilename, 'w') as outfile:
        outfile.write(QUIZ_XML.format(questions=questions))

main()

