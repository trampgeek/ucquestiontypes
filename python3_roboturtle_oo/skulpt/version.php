<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Version information for local_skulpt plugin
 *
 * Provides the Skulpt JavaScript library for running Python in the browser.
 * Skulpt itself is licensed under MIT/PSFLv2.
 *
 * @package    local_skulpt
 * @copyright  Skulpt developers (https://skulpt.org/)
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$plugin->component = 'local_skulpt';
$plugin->version = 2025120300;
$plugin->requires = 2023100900; // Moodle 4.3.0 or later.
$plugin->maturity = MATURITY_STABLE;
$plugin->release = '1.0';

