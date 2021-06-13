"""Infinite line"""
from . import _infline_key_bindings
from .infline import InfLine

# Note that importing _infline_key_bindings is needed as the InfLine layer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
del _infline_key_bindings
