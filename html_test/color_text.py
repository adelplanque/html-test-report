# -*- coding: utf-8 -*-
"""
Add ANSI color escape sequence to text.
"""
import sys
import platform


def is_term(stdout):
    return hasattr(stdout, "isatty") and stdout.isatty() \
        and platform.system() != 'Windows'


def color_factory(seq):
    def fct(text, stdout=sys.stdout):
        return seq + text + '\033[0m' if is_term(stdout) else text
    return fct


black = color_factory('\033[0;30m')
blue = color_factory('\033[0;34m')
cyan = color_factory('\033[0;36m')
green = color_factory('\033[0;32m')
red = color_factory('\033[0;31m')
purple = color_factory('\033[0;35m')
yellow = color_factory('\033[0;33m')
light_grey = color_factory('\033[0;37m')
