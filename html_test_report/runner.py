# -*- coding: utf-8 -*-
from six.moves import cStringIO as StringIO
import datetime
import json
import logging
import sys
import unittest

from .report import FileResult
from .report import ImageResult
from .report import TestCaseReport
from .report import TestFormatter
from .report import TestIndexRoot
from .report import TracebackHandler
from .report import status_dict


# Default stdout
stdout = sys.stdout


class ResultMixIn(object):
    """
    Shared code of HtmlTestResult with nose plugin.
    """

    def __init__(self, *args, **kwargs):
        super(ResultMixIn, self).__init__(*args, **kwargs)
        self._buffer_console = None
        self._buffer_log = None
        self._options = {}

    def setup(self, html_path, links=None):
        self._html_path = html_path
        self._index = TestIndexRoot(html_path, {"links": links})

    def add_result_method(self, status, test, exc_info=None, reason=None):
        """
        Add test result.
        """
        if hasattr(test, 'test'):
            # We are using nosetest. `test` is a nose wrapper.
            test = test.test

        tb = TracebackHandler(exc_info) if exc_info is not None else None
        try:
            console = self._buffer_console.getvalue()
        except AttributeError:
            console = None
        try:
            log = self._buffer_log.getvalue()
            log = [json.loads(x) for x in log.splitlines()]
        except AttributeError:
            log = None

        test_class = test.__class__
        name = "%s.%s.%s" % (
            test_class.__module__, test_class.__name__,
            getattr(test, '_testMethodName', 'test')
        )
        images = []
        for img in getattr(test, "_images", ()):
            try:
                img = ImageResult(
                    html_path=self._html_path,
                    result=img.get("result"),
                    expected=img.get("expected"),
                )
                images.append(img.to_dict())
            except AttributeError:
                pass
        files = []
        for f in getattr(test, "_files", ()):
            files.append(
                FileResult(
                    html_path=self._html_path,
                    title=f.get("title"),
                    content=f.get("content"),
                    content_type=f.get("content_type"),
                ).to_dict()
            )

        self._index.append(
            TestCaseReport(
                name=name,
                status=status,
                doc_class=test_class.__doc__,
                doc_test=getattr(test, "_testMethodDoc", ""),
                console=console,
                logs=log,
                tracebacks=tb,
                reason=reason,
                images=images,
                files=files,
            )
        )

        try:
            color, status_title = status_dict[status]
            status_color = color(status_title, stdout)
        except KeyError:
            status_color = "Unknown"
        stdout.write(status_color + "\n")

    def startTest(self, test):
        stdout.write(
            "Run test: %s.%s... " %
            (test.__class__.__name__, test._testMethodName))
        # Capture stdout and stderr.
        self._old_stderr = sys.stderr
        self._old_stdout = sys.stdout
        self._buffer_console = StringIO()
        sys.stdout = sys.stderr = self._buffer_console

        # Capture logs
        self._old_handlers = []
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            self._old_handlers.append(handler)
        self._buffer_log = StringIO()
        handler = logging.StreamHandler(stream=self._buffer_log)
        handler.setFormatter(TestFormatter())
        handler.setLevel(logging.DEBUG)
        logging.root.addHandler(handler)

    def stopTest(self, test):
        # Restore stdout and stderr.
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr
        if self._buffer_console is not None:
            self._buffer_console.close()
            self._buffer_console = None
        # Restore logs
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        for handler in self._old_handlers:
            logging.root.addHandler(handler)
        if self._buffer_log is not None:
            self._buffer_log.close()
            self._buffer_log = None

    def make_report(self):
        self._index.make_report()


class HtmlTestResult(ResultMixIn, unittest.TestResult):

    def addError(self, test, err):
        super(HtmlTestResult, self).addError(test, err)
        self.add_result_method('error', test, exc_info=err)

    def addFailure(self, test, err):
        super(HtmlTestResult, self).addFailure(test, err)
        self.add_result_method('fail', test, exc_info=err)

    def addSuccess(self, test):
        super(HtmlTestResult, self).addSuccess(test)
        self.add_result_method('success', test)

    def addSkip(self, test, reason):
        super(HtmlTestResult, self).addSkip(test, reason)
        self.add_result_method('skip', test, reason=reason)

    def addExpectedFailure(self, test, err):
        super(HtmlTestResult, self).addExpectedFailure(self, test, err)
        self.add_result_method('fail', test, exc_info=err)

    def addUnexpectedSuccess(self, test):
        super(HtmlTestResult, self).addUnexpectedSuccess(self, test)
        self.add_result_method('fail', test)


class HtmlTestRunner(object):
    """
    Alternative to standard unittest TextTestRunner rendering test with full
    logs, image, attached file, in a nice html way.

    Can be use:
    * standalone, just replace `python -m unittest` with `html-test`
    """

    def __init__(
        self,
        stream=sys.stderr,
        descriptions=True,
        verbosity=1,
        failfast=False,
        buffer=False,
        resultclass=None,
        html_path=None,
        links=None,
    ):
        self.stream = stream
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        self.resultclass = resultclass
        self.start_time = datetime.datetime.now()
        self.html_path = html_path
        self.links = links

    def run(self, tests_collection):
        result = HtmlTestResult(self.verbosity)
        result.setup(self.html_path, self.links)
        tests_collection(result)
        self.stop_time = datetime.datetime.now()
        result.make_report()
        print("Time Elapsed: %s" % (self.stop_time - self.start_time))
        return result
