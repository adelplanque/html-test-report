# -*- coding: utf-8 -*-
import logging
import pytest
import six
import textwrap

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

from .runner import TestCaseReport
from .runner import TestIndexRoot
from .runner import TracebackHandler


def pytest_addoption(parser):
    group = parser.getgroup("Html test report options")
    group.addoption(
        "--with-html-test",
        default=False,
        action="store_true",
        help="Generates a test report in html",
    )
    group.addoption(
        "--html-test-path",
        default=pathlib.Path("html"),
        help="Output directory for html test report",
    )
    group.addoption("--html-test-link", nargs="*", help="Add link")


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    enabled = config.getoption("with_html_test")
    if enabled:
        config.pluginmanager.register(HtmlTestPlugin(config), "html-test")


class TestLogHandler(logging.Handler):

    def __init__(self):
        super(TestLogHandler, self).__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append((record.name, record.levelname, self.format(record)))


class HtmlTestPlugin(object):

    def __init__(self, config):
        self.html_path = pathlib.Path(config.getoption("html_test_path"))
        self.index = TestIndexRoot(
            self.html_path,
            {
                "links": config.getoption("html_test_link"),
            },
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        root = logging.getLogger()
        handler = TestLogHandler()
        old_handlers = root.handlers
        old_level = root.level
        try:
            root.handlers = [handler]
            root.level = logging.DEBUG
            yield
        finally:
            root.handlers = old_handlers
            root.level = old_level
        item._log_handler = handler

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        yield
        if call.when != "call":
            return

        path, lineno, name = item.reportinfo()
        if isinstance(item, pytest.Function):
            name = item.function.__module__ + "." + name
        if call.excinfo is None:
            status = "success"
        elif isinstance(call.excinfo, AssertionError):
            status = "fail"
        else:
            status = "error"

        if call.excinfo:
            tracebacks = TracebackHandler(
                (call.excinfo.type, call.excinfo.value, call.excinfo.tb)
            )
        else:
            tracebacks = None

        if isinstance(item, pytest.Function):
            doc_test = textwrap.dedent(item.function.__doc__ or "")

        if item.parent:
            doc_class = textwrap.dedent(item.parent._getobj().__doc__ or "")
        else:
            doc_class = ""

        sections = {x[1]: x[2] for x in item._report_sections if x[0] == "call"}

        self.index.append(
            TestCaseReport(
                name=name,
                status=status,
                doc_class=doc_class,
                doc_test=doc_test,
                console="stdout:\n%s\nstderr:\n%s"
                % (sections.get("stdout", ""), sections.get("stderr", "")),
                logs=item._log_handler.records,
                tracebacks=tracebacks,
            )
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session):
        yield
        self.index.make_report()
