# -*- coding: utf-8 -*-
import six

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

from unittest.main import TestProgram
from .runner import HtmlTestRunner


def main():
    runner = HtmlTestRunner(html_path=pathlib.Path("html"))
    TestProgram(module=None, testRunner=runner)


if __name__ == "__main__":
    main()
