# ============================================================================
# Global functions. The OO version has only speed(); everything else is a
# method of RoboTurtle.
# ============================================================================

global _current_world  #omitfrombuild

def speed(speed_factor: int):
    """Set the speed of all robots from 1 (slow) to 10 (fast). 0 is superfast."""
    _current_world.set_speed(speed_factor)
