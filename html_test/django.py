# -*- coding: utf-8 -*-
"""
Django wrapper.
"""

from __future__ import absolute_import
from optparse import make_option
from django.test.runner import DiscoverRunner

from .html_test import HtmlTestRunner as BaseHtmlTestRunner
from .runner import Config

__all__ = ['HtmlTestRunner']


def vararg_callback(option, opt_str, value, parser):
    assert value is None
    value = getattr(parser.values, option.dest) or []
    arg = parser.rargs[0]
    if arg[0] != '-':
        value.append(arg)
        del parser.rargs[0]
        setattr(parser.values, option.dest, value)


class HtmlTestRunner(DiscoverRunner):
    test_runner = BaseHtmlTestRunner

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
            DiscoverRunner.add_arguments(cls, parser)
            parser.add_argument(
                '--html-test-path', default='html',
                help="Output directory for html test report")
            parser.add_argument(
                '--html-test-link', nargs='*',
                help="Add link")

    def __init__(self, **kwargs):
        Config().dest_path = kwargs.pop('html_test_path')
        Config().links = kwargs.pop('html_test_link')
        super(HtmlTestRunner, self).__init__(**kwargs)
