# -*- coding: utf-8 -*-

import os

from nose.plugins import Plugin

from .runner import Config
from .runner import Report
from .runner import ResultMixIn


class HtmlTestNosePlugin(ResultMixIn, Plugin):

    enabled = False
    name = "html-test"
    score = 2000

    def __init__(self):
        super(HtmlTestNosePlugin, self).__init__()

    def options(self, parser, env=os.environ):
        """
        Register commandline options.
        """
        super(HtmlTestNosePlugin, self).options(parser, env=env)
        parser.add_option('--html-test-path',
                          default='html',
                          help="Output directory for html test report")

    def configure(self, options, conf):
        super(HtmlTestNosePlugin, self).configure(options, conf)
        if not self.enabled:
            return
        Config().dest_path = options.html_test_path

    def finalize(self, result):
        Report(self).make_report()

    def addError(self, test, err):
        self.add_result_method('error', test, exc_info=err)

    def addFailure(self, test, err):
        self.add_result_method('fail', test, exc_info=err)

    def addSuccess(self, test):
        self.add_result_method('success', test)

    def addSkip(self, test, reason):
        self.add_result_method('skip', test, reason=reason)

    def addExpectedFailure(self, test, err):
        self.add_result_method('fail', test, exc_info=err)

    def addUnexpectedSuccess(self, test):
        self.add_result_method('fail', test)
