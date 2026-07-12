<?php
// This file is part of CodeRunner - http://coderunner.org.nz
//
// CodeRunner is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// CodeRunner is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with CodeRunner.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Browse AI-feedback pairs captured in CodeRunner question attempts.
 *
 * Index mode  (no parameters): lists every quiz in which at least one
 *   CodeRunner question attempt contains AI feedback, grouped by course.
 *
 * Detail mode (?quizid=NNN): displays a card for every attempt step that
 *   recorded AI feedback, showing the student code and the AI response.
 *
 * Place this file in question/type/coderunner/scripts/ on your Moodle server.
 *
 * @package   qtype_coderunner
 * @copyright 2025 Richard Lobb, The University of Canterbury
 * @license   http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

namespace qtype_coderunner;

use context_course;
use context_system;
use html_writer;
use moodle_url;

define('NO_OUTPUT_BUFFERING', true);

require_once(__DIR__ . '/../../../../config.php');
require_once($CFG->libdir . '/questionlib.php');

// ── Parameters ────────────────────────────────────────────────────────────────

$quizid = optional_param('quizid', 0, PARAM_INT);

// ── Auth ─────────────────────────────────────────────────────────────────────

$systemcontext = context_system::instance();
require_login();

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Extract the author's model solution from the stored -output HTML blob.
 */
function extract_author_solution(string $html): ?string {
    $pattern = '/<div\s+class="coderunner-authors-solution collapse"[^>]*>.*?' .
               '<pre\s+class="code-highlight">(.*?)<\/pre>/si';
    if (preg_match($pattern, $html, $m)) {
        return html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    }
    return null;
}

/**
 * Extract the AI feedback text from the stored -output HTML blob.
 */
function extract_ai_feedback(string $html): ?string {
    $pattern = '/<div\s+class="coderunner-ai-feedback collapse"[^>]*>\s*' .
               '<div[^>]*>(.*?)<\/div>\s*<\/div>/si';
    if (preg_match($pattern, $html, $m)) {
        return html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    }
    return null;
}

// ── Shared CSS (injected once in detail mode) ─────────────────────────────────

function ai_feedback_css(): string {
    return <<<'CSS'
<style>
:root {
  --bg:            #f4f6f8;
  --card:          #fff;
  --border:        #dde1e7;
  --head-bg:       #3a4f70;
  --head-fg:       #fff;
  --label:         #5a6a7e;
  --code-bg:       #f8f9fb;
  --ai-bg:         #fffef4;
  --ai-border:     #e6d96b;
  --author-bg:     #f0f7ff;
  --author-border: #90b8e0;
}
*, *::before, *::after { box-sizing: border-box; }
.aifb-controls {
  padding: 14px 0; display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
}
.aifb-controls input {
  flex: 1; min-width: 220px; padding: 6px 10px;
  border: 1px solid var(--border); border-radius: 4px; font-size: .9rem;
}
.aifb-counter { margin-left: auto; font-size: .85rem; color: var(--label); }
.aifb-group { margin: 20px 0 0; }
.aifb-group-header {
  font-size: 1rem; font-weight: 700; color: var(--head-bg);
  padding: 8px 0 6px; border-bottom: 2px solid var(--head-bg); margin-bottom: 12px;
}
.aifb-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  margin-bottom: 16px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.aifb-card-meta {
  display: flex; flex-wrap: wrap; gap: 12px; padding: 10px 14px;
  background: #f7f8fa; border-bottom: 1px solid var(--border);
  font-size: .8rem; color: var(--label);
}
.aifb-card-meta span b { color: #333; }
.aifb-card-body { display: grid; grid-template-columns: 1fr 1fr; }
@media (max-width: 800px) { .aifb-card-body { grid-template-columns: 1fr; } }
.aifb-panel { padding: 14px 16px; }
.aifb-panel + .aifb-panel { border-left: 1px solid var(--border); }
.aifb-panel-label {
  font-size: .72rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; margin-bottom: 8px;
}
.aifb-author-panel  { background: var(--author-bg); }
.aifb-author-panel  .aifb-panel-label { color: #3070a0; }
.aifb-ai-panel      { background: var(--ai-bg); }
.aifb-ai-panel      .aifb-panel-label { color: #8a7000; }
.aifb-card pre {
  font: 13px/1.5 'Fira Mono', 'Consolas', monospace;
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 4px; padding: 10px 12px;
  white-space: pre-wrap; word-break: break-word; margin: 0;
}
.aifb-ai-text { white-space: pre-wrap; font-size: .875rem; line-height: 1.65; }
.aifb-missing { color: #c00; font-style: italic; font-size: .85rem; }
.aifb-fraction { padding: 1px 7px; border-radius: 10px; font-size: .78rem; font-weight: 700; }
.aifb-fraction-good { background: #d4edda; color: #155724; }
.aifb-fraction-bad  { background: #f8d7da; color: #721c24; }
.aifb-fraction-part { background: #fff3cd; color: #856404; }
.aifb-hidden { display: none !important; }
</style>
CSS;
}

// ── Detail mode ───────────────────────────────────────────────────────────────

if ($quizid) {
    // Resolve context and check capability.
    $quiz = $DB->get_record('quiz', ['id' => $quizid], '*', MUST_EXIST);
    $coursecontext = context_course::instance($quiz->course);
    require_capability('moodle/question:editall', $coursecontext);

    $PAGE->set_url(
        '/question/type/coderunner/scripts/export_ai_feedback.php',
        ['quizid' => $quizid]
    );
    $PAGE->set_context($coursecontext);
    $PAGE->set_title('AI Feedback — ' . $quiz->name);

    $sql = "
        SELECT qasd.id          AS stepdata_id,
               qasd.value       AS html_value,
               q.name           AS question_name,
               u.username,
               u.firstname,
               u.lastname,
               qas.timecreated,
               qas.fraction,
               ans.value        AS student_code
          FROM {question_attempt_step_data} qasd
          JOIN {question_attempt_steps}     qas  ON qas.id  = qasd.attemptstepid
          JOIN {question_attempts}          qa   ON qa.id   = qas.questionattemptid
          JOIN {question}                   q    ON q.id    = qa.questionid
     LEFT JOIN {user}                       u    ON u.id    = qas.userid
     LEFT JOIN {question_attempt_step_data} ans
                ON ans.attemptstepid = qasd.attemptstepid AND ans.name = 'answer'
          JOIN {quiz_attempts}              qzat ON qzat.uniqueid = qa.questionusageid
          JOIN {quiz}                       qz   ON qz.id   = qzat.quiz
         WHERE qasd.name = '-output'
           AND " . $DB->sql_like('qasd.value', ':pattern') . "
           AND qz.id = :quizid
      ORDER BY q.name, qas.timecreated
    ";

    $rows = $DB->get_records_sql($sql, [
        'pattern' => '%Show AI feedback%',
        'quizid'  => $quizid,
    ]);

    echo $OUTPUT->header();
    echo $OUTPUT->heading('AI Feedback Report: ' . $quiz->name);
    echo ai_feedback_css();

    $total = count($rows);
    $backurl = new moodle_url('/question/type/coderunner/scripts/export_ai_feedback.php');

    echo html_writer::link($backurl, '&larr; Back to quiz list');

    echo '<div class="aifb-controls">';
    echo '<label>Filter:</label>';
    echo '<input type="search" id="aifb-filter" placeholder="Student name, username, or question…"'
        . ' oninput="aifbApplyFilter()">';
    echo '<span class="aifb-counter" id="aifb-counter">' . $total . ' shown</span>';
    echo '</div>';

    $currentquestion = null;
    $shown = 0;

    foreach ($rows as $row) {
        $authorsolution = extract_author_solution($row->html_value);
        $aifeedback     = extract_ai_feedback($row->html_value);

        if ($authorsolution === null && $aifeedback === null) {
            continue;
        }

        $qname    = $row->question_name ?? '(unknown question)';
        $username = $row->username ?? '';
        $fullname = trim(($row->firstname ?? '') . ' ' . ($row->lastname ?? ''));
        $time     = $row->timecreated ? userdate((int)$row->timecreated, '%Y-%m-%d %H:%M') : '';
        $fraction = $row->fraction;

        if ($fraction !== null) {
            $pct = round((float)$fraction * 100);
            if ($pct >= 90) {
                $frclass = 'aifb-fraction-good';
            } else if ($pct >= 50) {
                $frclass = 'aifb-fraction-part';
            } else {
                $frclass = 'aifb-fraction-bad';
            }
            $frlabel = '<span class="aifb-fraction ' . $frclass . '">' . $pct . '%</span>';
        } else {
            $frlabel = '';
        }

        if ($qname !== $currentquestion) {
            if ($currentquestion !== null) {
                echo "</div>\n";
            }
            $currentquestion = $qname;
            echo '<div class="aifb-group" data-qname="'
                . htmlspecialchars($qname, ENT_QUOTES) . '">' . "\n";
            echo '<div class="aifb-group-header">'
                . htmlspecialchars($qname) . "</div>\n";
        }

        $dataattrs = 'data-qname="' . htmlspecialchars($qname, ENT_QUOTES) . '" '
            . 'data-student="' . htmlspecialchars(strtolower("$fullname $username"), ENT_QUOTES) . '"';

        echo '<div class="aifb-card" ' . $dataattrs . ">\n";
        echo '  <div class="aifb-card-meta">' . "\n";
        if ($fullname || $username) {
            echo '    <span><b>' . htmlspecialchars($fullname ?: $username) . '</b>';
            if ($fullname && $username) {
                echo ' (' . htmlspecialchars($username) . ')';
            }
            echo "</span>\n";
        }
        if ($time) {
            echo '    <span>Submitted: <b>' . $time . "</b></span>\n";
        }
        if ($frlabel) {
            echo '    <span>Mark: ' . $frlabel . "</span>\n";
        }
        echo "  </div>\n";

        echo '  <div class="aifb-card-body">' . "\n";

        echo '  <div class="aifb-panel aifb-author-panel">' . "\n";
        echo '    <div class="aifb-panel-label">Author\'s solution</div>' . "\n";
        if ($authorsolution !== null) {
            echo '    <pre>' . htmlspecialchars($authorsolution) . "</pre>\n";
        } else {
            echo '    <span class="aifb-missing">Not found in stored HTML</span>' . "\n";
        }
        echo "  </div>\n";

        echo '  <div class="aifb-panel aifb-ai-panel">' . "\n";
        echo '    <div class="aifb-panel-label">AI feedback</div>' . "\n";
        if ($aifeedback !== null) {
            echo '    <div class="aifb-ai-text">' . htmlspecialchars($aifeedback) . "</div>\n";
        } else {
            echo '    <span class="aifb-missing">Not found in stored HTML</span>' . "\n";
        }
        echo "  </div>\n";

        echo "  </div>\n"; // card-body
        echo "</div>\n";   // card

        $shown++;
    }

    if ($currentquestion !== null) {
        echo "</div>\n"; // close last group
    }

    if ($shown === 0) {
        echo html_writer::tag('p', 'No AI-feedback records found for this quiz.');
    }

    echo <<<'JS'
<script>
function aifbApplyFilter() {
    const q = document.getElementById('aifb-filter').value.toLowerCase().trim();
    let shown = 0;
    document.querySelectorAll('.aifb-card').forEach(card => {
        const qname   = (card.dataset.qname   || '').toLowerCase();
        const student = (card.dataset.student || '').toLowerCase();
        const match = !q || qname.includes(q) || student.includes(q);
        card.classList.toggle('aifb-hidden', !match);
        if (match) shown++;
    });
    document.querySelectorAll('.aifb-group').forEach(group => {
        const anyVisible = [...group.querySelectorAll('.aifb-card')]
            .some(c => !c.classList.contains('aifb-hidden'));
        group.classList.toggle('aifb-hidden', !anyVisible);
    });
    document.getElementById('aifb-counter').textContent = shown + ' shown';
}
</script>
JS;

    echo $OUTPUT->footer();

} else {
    // ── Index mode: list quizzes that have AI-feedback data ───────────────────

    $PAGE->set_url('/question/type/coderunner/scripts/export_ai_feedback.php');
    $PAGE->set_context($systemcontext);
    $PAGE->set_title('AI Feedback Report Index');

    // One row per quiz that contains at least one AI feedback step.
    $sql = "
        SELECT DISTINCT qz.id   AS quizid,
                        qz.name AS quizname,
                        c.id    AS courseid,
                        c.fullname AS coursename
          FROM {question_attempt_step_data} qasd
          JOIN {question_attempt_steps}     qas  ON qas.id       = qasd.attemptstepid
          JOIN {question_attempts}          qa   ON qa.id        = qas.questionattemptid
          JOIN {quiz_attempts}              qzat ON qzat.uniqueid = qa.questionusageid
          JOIN {quiz}                       qz   ON qz.id        = qzat.quiz
          JOIN {course}                     c    ON c.id         = qz.course
         WHERE qasd.name = '-output'
           AND " . $DB->sql_like('qasd.value', ':pattern') . "
      ORDER BY c.fullname, qz.name
    ";

    $quizzes = $DB->get_records_sql($sql, ['pattern' => '%Show AI feedback%']);

    echo $OUTPUT->header();
    echo $OUTPUT->heading('AI Feedback Report Index');

    if (empty($quizzes)) {
        echo html_writer::tag('p', 'No AI-feedback data found across any accessible quiz.');
    } else {
        echo html_writer::tag(
            'p',
            '<strong>Instructions:</strong> Click a quiz link to view the AI feedback report for that quiz.'
        );

        $currentcourse = null;
        foreach ($quizzes as $row) {
            // Skip quizzes in courses where the user cannot view questions.
            $coursecontext = context_course::instance($row->courseid);
            if (!has_capability('moodle/question:editall', $coursecontext)) {
                continue;
            }

            if ($row->coursename !== $currentcourse) {
                if ($currentcourse !== null) {
                    echo html_writer::end_tag('ul');
                }
                $currentcourse = $row->coursename;
                echo html_writer::tag('h3', htmlspecialchars($row->coursename));
                echo html_writer::start_tag('ul');
            }

            $detailurl = new moodle_url(
                '/question/type/coderunner/scripts/export_ai_feedback.php',
                ['quizid' => $row->quizid]
            );
            echo html_writer::start_tag('li');
            echo html_writer::link($detailurl, htmlspecialchars($row->quizname));
            echo html_writer::end_tag('li');
        }

        if ($currentcourse !== null) {
            echo html_writer::end_tag('ul');
        }
    }

    echo $OUTPUT->footer();
}
