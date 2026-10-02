// Run a question's model answer under the REAL Skulpt engine (the one the student's browser uses), in Node,
// with the repo's dummy turtle.py standing in for Skulpt's graphics. Checks the Python code assembled into
// prototypeextra.html runs correctly under Skulpt, not just CPython - without needing Moodle or a browser.
//
// usage (from the project dir):  node questions/check_skulpt.js <question dir name> [test number, 0-based]
//   e.g.  node questions/check_skulpt.js swap
// Each questions/<name>/ holds testcases.json (the full template parameters) and answer.py (a model answer).
// Needs skulpt/skulpt/skulpt.min.js and skulpt-stdlib.js, and an up to date prototypeextra.html (run build.py).
const fs = require('fs'), vm = require('vm');
global.window = global; global.self = global;
vm.runInThisContext(fs.readFileSync('skulpt/skulpt/skulpt.min.js', 'utf8'));
vm.runInThisContext(fs.readFileSync('skulpt/skulpt/skulpt-stdlib.js', 'utf8'));
const files = Sk.builtinFiles.files;
delete files['src/lib/turtle.js'];                       // Replace Skulpt's graphics with the repo's no-op stub
files['src/lib/turtle.py'] = fs.readFileSync('turtle.py', 'utf8');

const unescapeHtml = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&amp;/g, '&');
const page = fs.readFileSync('prototypeextra.html', 'utf8');
const prefix = unescapeHtml(page.match(/<textarea id="___textareaId___prefix"[^>]*>([\s\S]*?)<\/textarea>/)[1]);

const q = process.argv[2];
const only = process.argv[3];
const params = JSON.parse(fs.readFileSync(`questions/${q}/testcases.json`, 'utf8'));
const tests = Array.isArray(params) ? params : params.testcases;
const answer = fs.readFileSync(`questions/${q}/answer.py`, 'utf8');
let failures = 0;

(async () => {
  for (let t = 0; t < tests.length; t++) {
    if (only !== undefined && String(t) !== only) continue;
    let out = '';
    Sk.configure({ output: s => { out += s; }, __future__: Sk.python3,
                   read: x => { if (files[x] === undefined) throw "File not found: '" + x + "'"; return files[x]; } });
    // The same program roboturtle.js builds: prefix + world + speed + student code + goal check
    const prog = prefix + "\nimport json\ntests = json.loads('''" + JSON.stringify(tests).replace(/\\/g, '\\\\') + "''')\n" +
      `world = load_world(tests[${t}])\nspeed(0)\n` + answer +
      `\ngoalError = _current_world.fail_message()\nprint("__ROBOTURTLE_GOAL__: " + goalError)\n`;
    try {
      await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody('<stdin>', false, prog, true));
      const m = out.match(/__ROBOTURTLE_GOAL__: ([\s\S]*)/);
      const ok = m && m[1].trim() === '';
      if (!ok) failures++;
      console.log(`${q} test ${t + 1}:`, m ? (ok ? 'PASS' : 'FAIL ' + m[1].trim()) : 'NO GOAL LINE; out=' + out.slice(0, 200));
    } catch (e) {
      failures++;
      console.log(`${q} test ${t + 1}: SKULPT ERROR`, String(e).slice(0, 400));
    }
  }
  process.exit(failures ? 1 : 0);
})();
