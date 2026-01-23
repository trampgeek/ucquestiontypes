# RoboTurtle CodeRunner

A Robotic Turtle question type for Moodle CodeRunner, heavily based on [Reeborg](https://reeborg.ca/reeborg.html).

## Overview

This is a complex question type that allows teachers to set turtle-graphics-like Moodle questions that can be
graded by the computer while also allowing the students to observe the graphical behaviour of the 
Turtle within the browser. It is layered on top of Turtle graphics as implemented by the [Skulpt](https://skulpt.org/) 
python-in-the-browser package. 

## Files

  * build.py - the Python program that builds prototypeextra.html and template.py, which are the two modules whose
   contents need to be manually copied into the question prototype.

  * prototypeextra.html.template - the template for prototypeextra.html, q.v. This file is used by build.py to assemble
    the target file from its components.

  * template.py.template - the template for template.py, q.v. This file tells build.py how to assemble the target file
    from its components.

  * assembledrobot.py.template - the template for assembledrobot.py, q.v. This file tells build.py how to assemble the target file
    from its components.

  * assembedrobot.py - the Python code to run the robot through its paces is required in both prototypeextra.html, where
    it is data given to Skulpt to execute, and in template.py where it is run to grade the final submission. This intermediate
    file is therefore built first for inclusion in both.

  * prototypeextra.html - the HTML code, including all the run-time javascript, that must be manually copied into 
   the prototypeextra field in the roboTurtle question prototype. The prototype uses the HTML UI, and the prototypeextra
   field is dynamically loaded into the question answer field that the student sees. It provides the UI to the 
   student.

  * template.py - the Python code that must be manually copied into the template field of the roboTurtle question
    prototype. It is the code that runs on the Jobe server to grade the student's submission. 

  * classes/* - Python files that get assembled into the file assembedrobot.py, which is then included in the
    file prototypeextra.html that provides the runtime environment and template.py which runs on the Jobe server
    to grade the submission.

  * turtle.py - a file to be included in the support files for the RoboTurtle question type so that the statement 
    "from turtle import Turtle, Screen" simply imports a set of mostly empty stubs. When marking on the Jobe
    server, we don't want an actual Turtle and Screen - we just need a simulator for it and that role is played
    by the BotController class in the 'classes' folder.

  * help.html - the instructions to be displayed to a student when they click the RoboTurtle Help button.

  * skulpt/ - this folder and its contents should be copied into the Moodle/public/local directory to
    give the question runtime enviroment access to the skulpt javascript files.

  * skulpt/version.php - required by Moodle for a minimal valid local plugin

  * skulp/skulpt/* - the three compiled Skulpt ("python-in-the-browser") javascript files from skulpt.org

## Building the RoboTurtle prototype.

  1. Run the build.py script in this folder
  2. Create a new CodeRunner question prototype, named PROTOTYPE_robot_turtle or whatever.
  3. Copy the contents of prototypeextra.html into the prototype's 'prototypeextra' field.
  4. Copy the contents of template.py into the prototype's 'template' field.


