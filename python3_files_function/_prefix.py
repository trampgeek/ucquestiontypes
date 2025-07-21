"""Keep track of file opens and closes in order to identify cases
   where a student has not closed a file.
   Maintains a dictionary that's a map from the id of the file object
   created by the open to a tuple of the filename and the close function
   for that file.
"""
from types import MethodType

_open_files = {}
_regular_open = open

def _my_close(self):
    """Override close method of a file. 
       self is the file object being closed.
    """
    if id(self) in _open_files:
        self.close = _open_files[id(self)][1]
        self.close()
        _open_files.pop(id(self))

def _my_open(filename, *args, **kwargs):
    file = _regular_open(filename, *args, **kwargs)
    _open_files[id(file)] = [filename, file.close]
    file.close = MethodType(_my_close, file)
    return file

open = _my_open # noqa A001  - disable ruff warning