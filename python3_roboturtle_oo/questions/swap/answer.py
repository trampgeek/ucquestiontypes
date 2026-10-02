alice = RoboTurtle("Alice")
bob = RoboTurtle("Bob")

# Alice walks east until she finds the bay on her left, then steps into it
while True:
    alice.turn_left()
    if alice.front_is_clear():
        break
    alice.turn_right()
    alice.move()
alice.move()

# Bob walks all the way home
while bob.front_is_clear():
    bob.move()

# Alice comes out of the bay and carries on east
alice.turn_left()
alice.turn_left()
alice.move()
alice.turn_left()
while alice.front_is_clear():
    alice.move()
