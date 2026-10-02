alice = RoboTurtle("Alice")
bob = RoboTurtle("Bob")

# Alice collects everything up to the wall, then throws it all over
while True:
    while alice.object_here():
        alice.take()
    if alice.wall_in_front():
        break
    alice.move()
while alice.carries_object():
    alice.toss()

# Bob goes to the wall, then down to the bottom, counting the steps
while not bob.wall_in_front():
    bob.move()
bob.turn_left()
steps = 0
while bob.front_is_clear():
    bob.move()
    steps += 1
while bob.object_here():
    bob.take()

# ... and back up the same distance, then home and up into the dump
bob.turn_left()
bob.turn_left()
for _ in range(steps):
    bob.move()
bob.turn_right()
while bob.front_is_clear():
    bob.move()
bob.turn_left()
bob.move()
while bob.carries_object():
    bob.put()
