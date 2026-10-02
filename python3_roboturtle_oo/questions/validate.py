"""Run a question's answer*.py through the CPython grader (template.py), each test case separately.
   usage (from the project dir, after running build.py):  python questions/validate.py questions/swap
   Prints (fraction, message) per answer file and test. See also check_skulpt.js, which does the same
   under the real Skulpt engine."""
import sys, json, subprocess, pathlib, tempfile
qdir = pathlib.Path(sys.argv[1])
scratch = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(tempfile.mkdtemp())
src = open('template.py').read()
tests = json.load(open(qdir / 'testcases.json'))
if isinstance(tests, dict):  # full template params
    tests = tests['testcases']
for f in sorted(qdir.glob('*.py')):
    for i, test in enumerate(tests):
        s = (src.replace('"""{{ STUDENT_ANSWER | e(\'py\') }}"""', repr(f.read_text()))
                .replace('"""{{testcases | json_encode}}"""', repr(json.dumps([test])))
                .replace('"""{{maxnumlines |default(\'0\') | e(\'py\')}}"""', '"0"')
                .replace('"""{{disabledfunctions | default([]) | json_encode}}"""', '"[]"'))
        (scratch / 'run.py').write_text(s)
        r = subprocess.run([sys.executable, str(scratch / 'run.py')], capture_output=True, text=True)
        out = json.loads(r.stdout) if r.stdout.strip() else r.stderr[-400:]
        print(f.name, f'test {i + 1}', '->', out if isinstance(out, str) else (out['fraction'], out['prologuehtml'][-150:]))
