from types import MethodType

_open_files = {}
_regular_open = open

def _my_close(self):
    if self.name in _open_files:
        self.close = _open_files[self.name]
        self.close()
        _open_files.pop(self.name)

def _my_open(filename, *args, **kwargs):
    file = _regular_open(filename, *args, **kwargs)
    _open_files[filename] = file.close
    file.close = MethodType(_my_close, file)
    return file

open = _my_open