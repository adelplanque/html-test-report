# -*- coding: utf-8 -*-
"""
Django wrapper.
"""
from __future__ import absolute_import
import six

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

from optparse import make_option
from django.test.runner import DiscoverRunner

from .runner import HtmlTestRunner as BaseHtmlTestRunner

__all__ = ['HtmlTestRunner']


def vararg_callback(option, opt_str, value, parser):
    assert value is None
    value = getattr(parser.values, option.dest) or []
    arg = parser.rargs[0]
    if arg[0] != '-':
        value.append(arg)
        del parser.rargs[0]
        setattr(parser.values, option.dest, value)


def html_test_runner(html_path, links=None):
    def wrapped(*args, **kwargs):
        runner = BaseHtmlTestRunner(*args, html_path=html_path, links=links, **kwargs)
        return runner

    return wrapped


class HtmlTestRunner(DiscoverRunner):

    if hasattr(DiscoverRunner, 'option_list'):
        # Maybe django < 1.8
        option_list = DiscoverRunner.option_list + (
            make_option(
                '--html-test-path', default='html',
                help="Output directory for html test report"),
            make_option(
                '--html-test-link', dest="html_test_link",
                action="callback", callback=vararg_callback,
                help="Add link"),
        )
    else:
        # Maybe django >= 1.8
        @classmethod
        def add_arguments(cls, parser):
            super(HtmlTestRunner, cls).add_arguments(parser)
            parser.add_argument(
                '--html-test-path', default='html',
                help="Output directory for html test report")
            parser.add_argument(
                '--html-test-link', nargs='*',
                help="Add link")

    def __init__(self, **kwargs):
        self.test_runner = html_test_runner(
            html_path=pathlib.Path(kwargs.pop("html_test_path")),
            links=kwargs.pop("html_test_link"),
        )
        super(HtmlTestRunner, self).__init__(**kwargs)
