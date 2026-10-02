alice = RoboTurtle("Alice")
bob = RoboTurtle("Bob")

# Alice walks up to the wall, throws everything she is carrying over it, and goes home
while not alice.wall_in_front():
    alice.move()
while alice.carries_object():
    alice.toss()
alice.turn_left()
alice.turn_left()
while alice.front_is_clear():
    alice.move()

# Bob goes to the wall, collects it all, goes home and throws it over the wall to the trash can
while not bob.wall_in_front():
    bob.move()
while bob.object_here():
    bob.take()
bob.turn_left()
bob.turn_left()
while bob.front_is_clear():
    bob.move()
bob.turn_left()
while bob.carries_object():
    bob.toss()
