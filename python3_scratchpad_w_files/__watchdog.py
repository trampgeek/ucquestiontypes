#!/usr/bin/python
# file: watchdog.py
# license: MIT License
# From https://dzone.com/articles/simple-python-watchdog-timer

import signal

class Watchdog(Exception):
    def __init__(self, time):
        """Set up a timer alarm to go off in 'time' secs."""
        self.time = time

    def __enter__(self):
        """Called on entering a 'with' block"""
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.time)

    def __exit__(self, type, value, traceback):
        """Exiting the with block. Cancel the watchdog"""
        signal.alarm(0)

    def handler(self, signum, frame):
        """Alarm went off. Raise Watchdog exception"""
        raise self

    def __str__(self):
        return "Watchdog timer expired after {} secs".format(self.time)
