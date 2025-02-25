# -*- coding: utf-8 -*-
import logging
import pytest
import six
import textwrap

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

from _pytest.outcomes import Skipped

from .report import ImageResult
from .report import TestCaseReport
from .report import TestIndexRoot
from .report import TracebackHandler


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

    def __init__(self, html_path):
        """
        Init TestLogHandler

        Args:
            html_path: Location to save the test report
        """
        super(TestLogHandler, self).__init__(level=logging.DEBUG)
        self.html_path = html_path
        self.records = []
        self.images = []

    def emit(self, record):
        image_data = getattr(record, "image", None)
        if image_data:
            try:
                result = image_data.get("result")
                expected = image_data.get("expected")
            except Exception as e:
                try:
                    logging.getLogger("html-test").error("Fail to add image: %s", e)
                except Exception:
                    pass
            self.images.append(ImageResult(self.html_path, result, expected))
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
        handler = TestLogHandler(self.html_path)
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
        elif call.excinfo.errisinstance(Skipped):
            status = "skip"
        elif call.excinfo.errisinstance(AssertionError):
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
                images=item._log_handler.images,
                tracebacks=tracebacks,
            )
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session):
        yield
        self.index.make_report()
