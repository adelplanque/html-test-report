# -*- coding: utf-8 -*-

from unittest.main import TestProgram
from .runner import HtmlTestRunner


def main():
    TestProgram(module=None, testRunner=HtmlTestRunner)

if __name__ == "__main__":
    main()
