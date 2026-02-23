// JavaScript for the live RoboTurtle display.
window._skActive = window._skActive || false;
window._skulptLoader = window._skulptLoader || (function () {
    let loaded = false;
    let loading = false;
    let callbacks = [];

    function loadScript(url) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = url;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    return {
        load: function () {
            if (loaded) {
                return Promise.resolve();
            }
            if (loading) {
                return new Promise(resolve => callbacks.push(resolve));
            }

            loading = true;
            let basepath = (window.location.hostname === 'localhost') ? '/moodle5' : ''

            return loadScript(basepath + "/local/skulpt/skulpt/skulpt.min.js")
                .then(() => loadScript(basepath + "/local/skulpt/skulpt/skulpt-stdlib.js"))
                .then(() => {
                    loaded = true;
                    loading = false;
                    callbacks.forEach(cb => cb());
                });
        }
    };
})();

window._skulptLoader.load().then(() => {
    // When skulpt has loaded ...
    const codeElementId = "___textareaId___answercode";
    const prefixElementId = "___textareaId___prefix";
    const testsElementId = "___textareaId___tests";
    const currentTestElementId = "___textareaId___currenttest";
    const outputElementId = "___textareaId___output";
    const runButtonId = "___textareaId____answer_run-btn";
    const prevButtonId = "___textareaId____answer_prev-btn";
    const nextButtonId = "___textareaId____answer_next-btn";
    const checkButtonId = "___textareaId___".replace('id_', '').replace("_answer", "_-submit");

    const outputElement = document.getElementById(outputElementId); 

    let stopExecution = false;
    let isRunning = false;
    let lastOutput = '';
    let savedOutput = '';
    let goalErrorMessage = null;
    let runCount = 0;
    let runHeaderAdded = false;

    /* Input/Output functions to use with Skulpt */
    function outf(text) {
        lastOutput = text;
        savedOutput = outputElement.textContent;

        // Check for goal status marker
        const match = text.match(/__ROBOTURTLE_GOAL__: (.*)/s);
        if (match) {
            goalErrorMessage = match[1];  // Empty string if no errors.
            // Discard the output
            text = '';
        }


        // Only add to output if there's still text after removing marker
        if (text) {
            // If this is the first real output for this run, add the header
            if (runCount > 0 && !runHeaderAdded) {
                // Add separator if any previous runs had output
                if (outputElement.textContent.trim()) {
                    outputElement.textContent += '\n' + '='.repeat(40) + '\n';
                }
                outputElement.textContent += `RUN ${runCount} PRINT OUTPUT:\n`;
                runHeaderAdded = true;
            }
            outputElement.textContent = outputElement.textContent + text;
        }
    }

    function inf(args) {
        let prompt = lastOutput;
        outputElement.textContent = savedOutput;
        return new Promise((resolve, reject) => {
            setTimeout(function() {
                resolve(window.prompt(lastOutput))
            }, 250)
        })
    }

    /* Modal dialog functions */
    const modalElement = document.getElementById("___textareaId___modal");
    const modalHeader = document.getElementById("___textareaId___modal-header");
    const modalBody = document.getElementById("___textareaId___modal-body");
    const modalBtnPrimary = document.getElementById("___textareaId___modal-btn-primary");
    const modalBtnSecondary = document.getElementById("___textareaId___modal-btn-secondary");

    function showModal(type, title, message, primaryButtonText, primaryCallback, secondaryButtonText, secondaryCallback) {
        // Set theme colors based on type
        if (type === 'success') {
            modalHeader.style.backgroundColor = '#28a745';
            modalBtnPrimary.style.backgroundColor = '#28a745';
        } else if (type === 'failure') {
            modalHeader.style.backgroundColor = '#ffc107';
            modalBtnPrimary.style.backgroundColor = '#ffc107';
        } else if (type === 'error') {
            modalHeader.style.backgroundColor = '#dc3545';
            modalBtnPrimary.style.backgroundColor = '#dc3545';
        }

        modalHeader.textContent = title;
        modalBody.innerHTML = message;
        modalBtnPrimary.textContent = primaryButtonText;
        modalBtnPrimary.style.color = 'white';

        // Set up primary button
        modalBtnPrimary.onclick = () => {
            hideModal();
            if (primaryCallback) primaryCallback();
        };

        // Set up secondary button if provided
        if (secondaryButtonText) {
            modalBtnSecondary.style.display = 'inline-block';
            modalBtnSecondary.textContent = secondaryButtonText;
            modalBtnSecondary.onclick = () => {
                hideModal();
                if (secondaryCallback) secondaryCallback();
            };
        } else {
            modalBtnSecondary.style.display = 'none';
        }

        modalElement.style.display = 'block';
    }

    function hideModal() {
        modalElement.style.display = 'none';
    }


    // Count lines of python code (roughly - doesn't handle
    // multiline docstrings)
    function countPythonLines(code) {
        const lines = code.split('\n');
        let count = 0;
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed === '') continue; // Ignore empty lines
            if (trimmed.startsWith('#')) continue;  // Ignore comments
            
            // Skip lines containing triple quotes (docstrings)
            if (trimmed.includes('"""') || trimmed.includes("'''")) continue;
            count++;
        }
        
        return count;
    }

    // Adjust line number in syntax errors etc from Skulpt.
    function tweakLineNumber(errorMessage, linesBeforeAnswer) {
        const match = errorMessage.match(/(.*Error:.* on line )(\d+)/);
  
        if (match) {
            const adjustedLineNum = parseInt(match[2]) - linesBeforeAnswer + 1;
            if (adjustedLineNum > 0) {
                errorMessage = match[1] + adjustedLineNum;
            }
        }
        return errorMessage;
    }

    function getFriendlyError(errorMsg, linesBeforeAnswer) {
        let errorStr = errorMsg.toString();

        // Map technical errors to friendly messages

        if (errorStr.includes("Cannot toss")) {
            if (errorStr.includes("no items in inventory")) {
                return {
                    title: "RoboTurtle says: My inventory is empty!",
                    message: "I don't have anything to toss! My inventory is empty.<br><br><strong>Tip:</strong> Use <code>carries_object()</code> to check if you have items before tossing."
                };
            } else if (errorStr.includes("out of bounds")) {
                return {
                    title: "RoboTurtle says: Can't toss there!",
                    message: "I can't toss an item over the perimeter wall!"
                };
            } else if (errorStr.includes("blocked")) {
                return {
                    title: "RoboTurtle says: That cell is blocked!",
                    message: "I can't toss an item into a blocked cell!<br><br><strong>Tip:</strong> Use <code>front_is_clear()</code> to check if the cell is accessible."
                };
            }
        }
        if (errorStr.includes("No world loaded")) {
            return {
                title: "RoboTurtle says: No world loaded!",
                message: "There's no world for me to explore yet!<br><br>This shouldn't normally happen. Contact your instructor if you see this message."
            };
        }
        if (errorStr.includes("wall blocks path")) {
            return {
                title: "RoboTurtle says: I hit a wall!",
                message: "I can't move through walls!<br><br><strong>Tip:</strong> Use <code>front_is_clear()</code> to check if the path is clear before moving."
            };
        }
        if (errorStr.includes("out of bounds")) {
            return {
                title: "RoboTurtle says: I can't go there!",
                message: "I can't leave the grid! I'm at the edge of my world.<br><br><strong>Tip:</strong> Use <code>front_is_clear()</code> to check boundaries before moving."
            };
        }
        if (errorStr.includes("cell") && errorStr.includes("blocked")) {
            return {
                title: "RoboTurtle says: That cell is blocked!",
                message: "I can't move into blocked cells!<br><br><strong>Tip:</strong> Use <code>front_is_clear()</code> to check if a cell is accessible."
            };
        }
        if (errorStr.includes("no items at position") || errorStr.includes("Cannot take")) {
            return {
                title: "RoboTurtle says: Nothing to pick up!",
                message: "There's nothing here to pick up! My claws are empty.<br><br><strong>Tip:</strong> Use <code>object_here()</code> to check if there's an item before trying to take it."
            };
        }
        if (errorStr.includes("no items in inventory") || errorStr.includes("Cannot put")) {
            return {
                title: "RoboTurtle says: My inventory is empty!",
                message: "I don't have anything to put down! My inventory is empty.<br><br><strong>Tip:</strong> Use <code>carries_object()</code> to check if you have items before putting."
            };
        }


        // Default for unknown errors
        errorStr = tweakLineNumber(errorStr, linesBeforeAnswer);
        return {
            title: "RoboTurtle says: Something went wrong!",
            message: `An error occurred:<br><br><code>${errorStr}</code>`
        };
    }

    runSkulptWhenFree(false); // Display the initial state
    updateTestButtons(); // Set initial button states


    // The user has clicked Run (or Stop if already running).
    function runit() {
        if (isRunning) {
            stopExecution = true;
            return;
        }
        runSkulptWhenFree(true)
    }

    // Update button states based on current test number
    function updateTestButtons() {
        const testsJson = document.getElementById(testsElementId).textContent;
        const tests = JSON.parse(testsJson);
        const currentTest = parseInt(document.getElementById(currentTestElementId).value);
        const prevButton = document.getElementById(prevButtonId);
        const nextButton = document.getElementById(nextButtonId);

        // Disable Previous if at first test
        prevButton.disabled = (currentTest === 0);
        prevButton.style.opacity = (currentTest === 0) ? '0.5' : '1';

        // Disable Next if at last test
        nextButton.disabled = (currentTest >= tests.length - 1);
        nextButton.style.opacity = (currentTest >= tests.length - 1) ? '0.5' : '1';
    }

    // Navigate to previous test
    function prevTest() {
        const currentTest = parseInt(document.getElementById(currentTestElementId).value);
        if (currentTest > 0) {
            runCount = 0;
            document.getElementById(currentTestElementId).value = currentTest - 1;
            runSkulptWhenFree(false);
            updateTestButtons();
        }
    }

    // Navigate to next test
    function nextTest() {
        const testsJson = document.getElementById(testsElementId).textContent;
        const tests = JSON.parse(testsJson);
        const currentTest = parseInt(document.getElementById(currentTestElementId).value);
        if (currentTest < tests.length - 1) {
            runCount = 0;
            document.getElementById(currentTestElementId).value = currentTest + 1;
            runSkulptWhenFree(false);
            updateTestButtons();
        }
    }

    // Run the prefix code using Skulpt, with the
    // student answer appended if includeAnswer is true.
    // Since Skulpt isn't re-entrant, we need to wait till it's
    // inactive, as determined by the window._skActive flag.
    function runSkulptWhenFree(includeAnswer) {
        if (!window._skActive) {
            window._skActive = true;
            runSkulpt(includeAnswer);
            window._skActive = false;
        } else {
            setTimeout(runSkulptWhenFree, 100);
        }
    }

    // Return the given code with docstring contents replaced with spaces (except
    //  newlines, preserved to ensure line numbers are valid).
    function stripDocstrings(code) {
        return code.replace(/""".*?"""|'''.*?'''/gs, match => match.replace(/[^\n]/g, ' '));
    }

    // Check the student answer for a couple of potentially confusing flaws
    // before running it: missing parentheses in function call or defined
    // support function never called.
    function checkAnswer(answer) {
        const turtleMethods = ['move', 'turn_left', 'turn_right', 'take', 'put', 'toss', 'print_state',
            'speed', 'at_goal', 'front_is_clear', 'right_is_clear', 'wall_in_front', 'wall_on_right',
            'object_here', 'carries_object', 'is_facing_north'];
        
        // Preprocess all lines: split and remove comments once.
        const cleaned = stripDocstrings(answer);
        const lines = cleaned.split('\n').map(line => line.split('#')[0].trim());
        
        // First pass: find all user-defined functions
        const userDefinedFunctions = [];
        for (let i = 0; i < lines.length; i++) {
            const defMatch = lines[i].match(/^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/);
            if (defMatch) {
                userDefinedFunctions.push({
                    name: defMatch[1],
                    lineNumber: i + 1
                });
            }
        }
        
        // Combine turtle methods with user-defined function names for parentheses check
        const allFunctions = [...turtleMethods, ...userDefinedFunctions.map(f => f.name)];
        
        // Second pass: check for missing parentheses
        for (let i = 0; i < lines.length; i++) {   
            if (lines[i].match(/def\s+/)) continue; // Skip def lines

            for (const method of allFunctions) {
                const regex = new RegExp(`\\b${method}\\b(?!\\s*\\()`);
                
                if (regex.test(lines[i])) {
                    return `Line ${i + 1}: missing parentheses in call to function '${method}'`;
                }
            }
        }
        
        // Third pass: check if user-defined functions are actually called
        for (const func of userDefinedFunctions) {
            let functionCalled = false;
            
            for (let i = 0; i < lines.length; i++) {
                 if (lines[i].match(/def\s+/)) continue; // Skip def lines

                // Check if function is called (with parentheses)
                const callRegex = new RegExp(`\\b${func.name}\\s*\\(`);
                if (callRegex.test(lines[i])) {
                    functionCalled = true;
                    break;
                }
            }
            
            if (!functionCalled) {
                return `Line ${func.lineNumber}: function '${func.name}' is defined but never called`;
            }
        }
        
        return '';
    }

    // The main 'runSkulpt' function, called from runSkulptWhenFree
    // when window._skActive is false. Runs as a callback so is essentially async.
    function runSkulpt(includeAnswer) {
        // Reset goal status capture
        goalErrorMessage = '';

        /* Skulpt configuration */
        Sk.configure({
            output:outf,
            yieldLimit: 200, // Give control back to browser every 200 msecs.
            inputTakesPrompt: true,
            inputfun: inf,
            __future__: Sk.python3
        }); 

        //Sk.pre = outputElementId;  // Is this needed?

        (Sk.TurtleGraphics || (Sk.TurtleGraphics = {})).target = '___textareaId___mycanvas';
        
        const prefix = document.getElementById(prefixElementId).value;
        const testsJson = document.getElementById(testsElementId).value;
        const currentTest = parseInt(document.getElementById(currentTestElementId).value);
        let answer = '';
        if (includeAnswer) {
            answer = document.getElementById(codeElementId).value.trimEnd();
            if (!answer) {
                showModal('failure', "⚠️ Can't test", 'No code to run!', 'Close', null);
                return;
            } else {
                answer += "\n";
                const lineCount = countPythonLines(answer);
                const maxnumlines = parseInt(document.getElementById('___textareaId___maxnumlines').value);
                if (maxnumlines > 0 && lineCount > maxnumlines) {
                    const message = `Sorry, too many lines. Maximum is ${maxnumlines}, got ${lineCount}`;
                    showModal('failure', "⚠️ Can't test", message, 'Close', null);
                    return;
                } else {
                    const error = checkAnswer(answer);
                    if (error !== '') {
                        showModal('failure', "⚠️ Error in code", error, 'Close', null);
                        return;
                    }
                }
            }
        }
            
        let fullProg = prefix + "\n" + `import json
tests_json = """${testsJson}
"""
tests = json.loads(tests_json)
world = load_world(tests[${currentTest}])
`;
        // The 'disabledfunctions' template parameter can be used to disable specific functions
        // so students have to implement their own.
        let disabledFunctions = {{ disabledfunctions | default([]) | json_encode }};
        if (disabledFunctions.length > 0) {
            disabledFunctions.forEach(function(func) {
                fullProg += "del " + func + "\n";
            });
        }

        let linesBeforeAnswer = fullProg.split("\n").length;
        fullProg += answer;

        // Append goal checking code when running student answer
        if (includeAnswer) {
            fullProg += `
goalError = _current_world.fail_message();
print("__ROBOTURTLE_GOAL__: " + goalError);
`;
        }

        // Setup for this run
        if (includeAnswer) {
            runCount++;
            runHeaderAdded = false;  // Will add header only if there's print output
        } else {
            outputElement.textContent = '';  // Clear on initial load
        }

        isRunning = true;
        runButton = document.getElementById(runButtonId);
        if (includeAnswer) {  // Suppress flicker of Start/Stop button when initialising.
            runButton.innerText = 'Stop';
            runButton.style.setProperty('background-color', 'darkred', 'important');
        }
        Sk.misceval.asyncToPromise(
            () => Sk.importMainWithBody("<stdin>", false, fullProg, true),
            {
              "*": () => {
                    if (stopExecution) throw "Interrupted...";
                }
            }
        ).then(() => {
            // Execution successful - check goal if student code was run
            if (includeAnswer) {
                const testsJson = document.getElementById(testsElementId).textContent;
                const tests = JSON.parse(testsJson);
                const currentTest = parseInt(document.getElementById(currentTestElementId).value);
                const hasMoreTests = currentTest < tests.length - 1;

                if (goalErrorMessage.trim() === '') {
                    // Success!
                    let last = tests.length == 1 ? '' : ' last';
                    if (hasMoreTests) {
                        // Offer to move to next test
                        showModal(
                            'success',
                            '🎉 Success!',
                            'Congratulations - you passed this test!<br><br>There are more tests to try.',
                            'Next Test',
                            () => nextTest(),
                            'Close',
                            null
                        );
                    } else {
                        // Last test completed (but suppress the word last if only 1 test).
                        showModal(
                            'success',
                            '🎉 Success!',
                            `Congratulations - you\'ve passed the${last} test!`,
                            'Awesome!',
                            null
                        );
                    }
                } else {
                    // Goal not reached
                    const errors = goalErrorMessage.replaceAll('\n', '<br>');
                    showModal(
                        'failure',
                        '⚠️ Sorry, not yet!',
                        `Your code ran without errors, but the final state doesn't satisfy the goal:<br>${errors}`,
                        'Close',
                        null
                    );
                }
            }
        }).catch(err => {
            // Check if it was a user interruption
            if (err.toString().includes("Interrupted")) {
                outf("\n[Execution stopped by user]\n");
            } else if (includeAnswer) {
                // Show friendly error dialog for student code errors
                const friendlyError = getFriendlyError(err, linesBeforeAnswer);
                showModal(
                    'error',
                    friendlyError.title,
                    friendlyError.message,
                    'Close',
                    null
                );
            } else {
                // Error during initial world load (shouldn't happen normally)
                const message = err.toString() + "\nThis shouldn't happen - please report.\n";
                showModal('failure', "*** SYSTEM ERROR ***", message, 'Close', null);
            }
        }).finally(() => {
            stopExecution = false;
            isRunning = false;
            runButton = document.getElementById(runButtonId);
            runButton.innerText = 'Run';
            runButton.style.setProperty('background-color', 'darkgreen', 'important');
        })
    }

    // Let Ace manage the code box.
    M.util.js_pending('qtype_coderunner/userinterfacewrapper');
    require(['qtype_coderunner/userinterfacewrapper'], function(amd) {
        amd.newUiWrapper("ace", "___textareaId___answercode");
        M.util.js_complete('qtype_coderunner/userinterfacewrapper');
    });

    // Add button click event handlers
    document.getElementById('___textareaId___' + '_wrapper').style.resize = 'none';
    document.getElementById(runButtonId).addEventListener('click', runit);
    document.getElementById(prevButtonId).addEventListener('click', prevTest);
    document.getElementById(nextButtonId).addEventListener('click', nextTest);
    let helpButton = document.getElementById("___textareaId___toggle-help-btn");
    if (helpButton) {
        helpButton.addEventListener('click',() => toggleRoboTurtleHelp("___textareaId___")); 
    }
    const checkButton = document.getElementById(checkButtonId);
    if (checkButton) {
        checkButton.textContent = "Submit for grading";
    }
});