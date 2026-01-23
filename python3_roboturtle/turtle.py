"""Dummy Turtle and Screen classes for when running headless.
   Needs to be a support file in the prototype.
"""

# ============================================================================
# Dummy Turtle class
# ============================================================================
class Turtle:
    def __init__(self, *args, **kwargs):
        self.pen_is_down = False
    def goto(*args, **kwargs): pass
    def forward(*args, **kwargs): pass
    def left(*args, **kwargs): pass
    def right(*args, **kwargs): pass
    def clearsceen(): pass
    def color(*args, **kwargs): pass
    def pencolor(*args, **kwargs): pass
    def fillcolor(*args, **kwargs): pass
    def begin_fill(*args, **kwargs): pass
    def end_fill(*args, **kwargs): pass
    def setheading(*args, **kwargs): pass 
    def circle(*args, **kwargs): pass
    def speed(*args, **kwargs): pass
    def heading(*args, **kwargs): pass
    def pendown(self, *args, **kwargs):
        self.pen_is_down = True
    def penup(self, *args, **kwargs):
        self.pen_is_down = False;
    def pensize(*args, **kwargs): pass
    def showturtle(*args, **kwargs): pass
    def hideturtle(*args, **kwargs): pass
    def tracer(*args, **kwargs): pass
    def write(*args, **kwargs): pass
    def shape(*args, **kwargs): pass
    def isdown(self, *args, **kwargs):
        return self.pen_is_down

# ============================================================================
# Dummy Screen class
# ============================================================================
class Screen:
    def setup(*args, **kwargs): pass
    def setworldcoordinates(*args, **kwargs): pass
    def title(*args, **kwargs): pass
    def tracer(*args, **kwargs): pass
    def update(*args, **kwargs): pass
    def clear(*args, **kwargs): pass