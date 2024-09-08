# -*- coding: utf-8 -*-
import codecs
import collections
import datetime
import json
import logging
import magic
import os
import pkg_resources
import pprint
import re
import six
import socket
import subprocess
import sys
import uuid

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

from jinja2 import Template
from pygments import highlight
from pygments import formatters
from pygments import lexers

from .color_text import red, yellow, green


# Default stdout
stdout = sys.stdout


status_dict = {
    'success': (green, 'Success'),
    'fail': (red, 'Fail'),
    'error': (red, 'Error'),
    'skip': (yellow, 'Skip'),
}


pygments_css = formatters.HtmlFormatter().get_style_defs()


def safe_text(s):
    if not s:
        return six.u("")
    try:
        if six.PY2:
            if isinstance(s, unicode):
                return s
            if isinstance(s, str):
                return unicode(s, "utf-8", errors="replace")
            try:
                return six.ensure_text(str(s), encoding="utf-8", errors="replace")
            except Exception:
                try:
                    return six.ensure_text(repr(s), encoding="utf-8", errors="replace")
                except Exception:
                    return "Unable to get any valid unicode representation"
        else:
            return str(s)
    except Exception as e:
        return six.u(e)


def get_img_ext(data):
    """
    Return extension of an image.
    """
    try:
        mg = magic.Magic(mime=True)
        mime = mg.from_buffer(data)
        typ, ext = mime.split("/")
    except Exception as e:
        print("Fail to get image type: %s" % e)
        return
    if typ == "image":
        return ext


class TestFormatter(logging.Formatter):
    """
    Format log entry as json (logger, level, message)
    """

    def format(self, record):
        try:
            if record.args:
                msg = record.msg % record.args
            else:
                msg = record.msg
        except Exception as e:
            msg = "Invalid log record: %s" % e
        msg = safe_text(msg)
        return json.dumps((record.name, record.levelname, msg))


class ImageResult(object):

    def __init__(self, html_path, result, expected=None):
        self._html_path = html_path
        imgdir = self._html_path / "img"
        if not imgdir.exists():
            imgdir.mkdir()
        self.result = self.write_img(result)
        if expected:
            self.expected = self.write_img(expected)
            self.rmse = self.compare_rmse(self.result, self.expected)
        else:
            self.expected = None
            self.rmse = None

    def get_random_filename(self, img_type):
        return pathlib.Path("img", "img-%s.%s" % (str(uuid.uuid4()), img_type))

    def write_img(self, data):
        """
        Save image and return filename.
        """
        if not data:
            return
        try:
            if isinstance(data, six.string_types):
                p = pathlib.Path(data)
                if p.exists():
                    with p.open("rb") as infile:
                        data = infile.read()
        except Exception:
            pass
        img_ext = get_img_ext(data)
        if not img_ext:
            return
        filename = self.get_random_filename(img_ext)
        with (self._html_path / filename).open("wb") as outfile:
            outfile.write(data)
        return filename

    def compare_rmse(self, img1, img2):
        """
        Compute RMSE difference between `img1` and `img2` and return filename
        for the diff image.
        """
        filename = self.get_random_filename("png")
        cmd = ["compare", "-metric", "rmse", str(img1), str(img2), str(filename)]
        try:
            subprocess.call(cmd, cwd=str(self._html_path))
        except Exception as e:
            stdout.write(
                "Enable to run ImageMagic compare: %s: %s\n" % (e.__class__.__name__, e)
            )
        if (self._html_path / filename).exists():
            return filename

    def to_dict(self):
        return {
            "result": self.result,
            "expected": self.expected,
            "rmse": self.rmse,
        }


class FileResult(object):
    """
    File to be add to test report.
    """

    def __init__(self, html_path, content, title=None, content_type=None):
        destdir = html_path / "data"
        if not destdir.exists():
            destdir.mkdir()
        self.filename = pathlib.Path("data", "file-%s" % str(uuid.uuid4()))
        with (html_path / self.filename).open("wb") as outfile:
            outfile.write(safe_text(content).encode("utf-8"))
        self.title = safe_text(title) or self.filename.name

    def to_dict(self):
        return {"title": self.title, "filename": self.filename}


class TestCaseReport(object):
    """
    Report for one test.
    """

    def __init__(
        self,
        name,
        status,
        doc_class=None,
        doc_test=None,
        console=None,
        logs=None,
        tracebacks=None,
        reason=None,
        images=None,
        files=None,
    ):
        self.name = name
        self.status = status
        try:
            status_title = status_dict[status][1]
        except KeyError:
            status_title = "unknow"
        self.context = {
            "name": six.ensure_text(name),
            "status": status,
            "status_title": status_title,
            "doc_class": safe_text(doc_class),
            "doc_test": safe_text(doc_test),
            "console": safe_text(console),
            "logs": [
                (name, level, safe_text(msg)) for name, level, msg in (logs or ())
            ],
            "tracebacks": tracebacks,
            "reason": safe_text(reason),
            "images": images,
            "files": files,
            "pygments_css": pygments_css,
        }

    def render(self, html_path, global_context):
        self.context.update(global_context)
        template = Template(
            pkg_resources.resource_string(
                "html_test_report", os.path.join("templates", "test-case.html")
            ).decode("utf-8")
        )
        filename = self.name + ".html"
        with open(str(html_path / filename), "wb") as outfile:
            report = template.render(self.context)
            outfile.write(report.encode("utf-8"))
        return filename


class TbFrame(object):
    """
    Expose one frame of a traceback to jinja2.
    """

    CodeLine = collections.namedtuple(
        'CodeLine', ('lineno', 'code', 'highlight', 'extended'))
    VarLine = collections.namedtuple('VarLine', ('name', 'value'))
    coding_regex = re.compile(
        six.b(r"^[ \t\f]*#.*?coding[:=][ \t]*(?P<coding>[-_.a-zA-Z0-9]+)"))

    def __init__(self, frame, lineno):
        self.frame = frame
        self.filename = frame.f_code.co_filename
        self.lineno = lineno
        self.name = frame.f_code.co_name
        self.id = str(uuid.uuid4())

    @staticmethod
    def get_charset(filename):
        with open(filename, 'rb') as srcfile:
            for i in range(2):
                l = srcfile.readline()
                m = TbFrame.coding_regex.match(l)
                if m:
                    return m.group('coding').decode('ascii')
        if six.PY2:
            return u'ascii'
        else:
            return u'utf-8'

    @property
    def code_fragment(self):
        fragment_length = 50
        start = max(1, self.lineno - fragment_length)
        stop = self.lineno + fragment_length
        lexer = lexers.Python3Lexer(stripnl=False)
        formatter = formatters.HtmlFormatter(full=False, linenos=False)

        loader = self.frame.f_globals.get('__loader__')
        module_name = self.frame.f_globals.get('__name__') or ''
        source = None
        if loader is not None and hasattr(loader, "get_source"):
            try:
                source = loader.get_source(module_name)
            except Exception:
                pass
        if source is None:
            try:
                charset = self.get_charset(self.filename)
                with codecs.open(self.filename, 'r', encoding=charset) as infile:
                    source = infile.read()
            except IOError:
                return

        try:
            for lineno, frag in enumerate(
                    formatter._highlight_lines(
                        formatter._format_lines(
                            lexer.get_tokens(source))),
                    start=1):
                if lineno >= start:
                    yield self.CodeLine(
                        lineno, frag[1].rstrip(),
                        lineno == self.lineno,
                        lineno <= self.lineno - 2 or lineno >= self.lineno + 2
                    )
                if lineno >= stop:
                    break
        except UnicodeDecodeError as e:
            yield self.CodeLine(None, six.u(str(e)), True, False)

    @property
    def loc_vars(self):
        lexer_text = lexers.TextLexer()
        lexer = lexers.Python3Lexer(stripnl=False)
        formatter = formatters.HtmlFormatter(full=False, linenos=False)
        for name, value in sorted(self.frame.f_locals.items()):
            try:
                value = pprint.pformat(value, indent=4)
                value = highlight(value, lexer, formatter)
            except Exception as e:
                value = highlight("%s: %s" % (e.__class__.__name__, str(e)),
                                  lexer_text, formatter)
            yield self.VarLine(name, value)


class Traceback(object):
    """
    Expose one traceback to jinja2.
    """

    def __init__(self, name, msg, tb):
        self.name = name
        lines = msg.splitlines()
        self.title = lines[0] if lines else "Unknow"
        if len(lines) > 1:
            self.description = u'\n'.join(lines[1:])
        else:
            self.description = None
        self.tb = tb

    def __iter__(self):
        tb = self.tb
        while tb:
            yield TbFrame(tb.tb_frame, tb.tb_lineno)
            tb = tb.tb_next


class TracebackHandler(list):
    """
    Expose traceback list to jinja2.
    """

    @staticmethod
    def get_msg(ev):
        if six.PY2:
            try:
                return six.binary_type(ev).decode('utf-8')
            except UnicodeEncodeError:
                try:
                    return six.text_type(ev)
                except Exception:
                    return u"encoding error while retreiving message"
        else:
            try:
                return six.text_type(ev)
            except Exception:
                return u"encoding error while retreiving message"

    def __init__(self, exc_info):
        etype, evalue, tb = exc_info
        if six.PY2:
            self.append(Traceback(evalue.__class__.__name__,
                                  self.get_msg(evalue), tb))
        else:
            while evalue:
                self.append(Traceback(evalue.__class__.__name__,
                                      self.get_msg(evalue),
                                      evalue.__traceback__))
                evalue = evalue.__context__
        self.reverse()


class TestIndexNode(dict):

    def __init__(self, name=None, status=None, url=None):
        self._name = name
        self._status = status
        self._url = url

    def get_status(self):
        if self._status is None:
            status_count = {
                'success': 0,
                'fail': 0,
                'error': 0,
                'skip': 0,
            }
            for child in self.values():
                status_count[child.get_status()] += 1
            for name in ('error', 'fail', 'skip', 'success'):
                if status_count[name]:
                    self._status = name
                    break
        return self._status

    def as_json(self):
        return {
            'title': self._name,
            'url': str(self._url),
            'status': self.get_status(),
            'childs': [x[1].as_json() for x in sorted(self.items())]
        }


class TestIndexRoot(TestIndexNode):

    def __init__(self, html_path, global_context=None):
        super(TestIndexRoot, self).__init__()
        html_path.mkdir(exist_ok=True, parents=True)
        self._html_path = html_path
        self._global_context = global_context or {}
        self._global_context.update(
            {
                "hostname": socket.gethostname(),
                "date": datetime.datetime.now(),
            }
        )

    def append(self, test_report):
        filename = test_report.render(self._html_path, self._global_context)
        toks = test_report.name.split(".")
        name = toks[-1]
        node = self
        for tok in toks[:-1]:
            if tok not in node:
                node[tok] = TestIndexNode(tok)
            node = node[tok]
        node[name] = TestIndexNode(name, test_report.status, filename)

    def make_report(self):
        """
        Create html report for the tests results.
        """
        # Create index data
        template = Template("var index = {{data|safe}};")
        index_js = self._html_path / "index.js"
        with index_js.open("w") as outfile:
            outfile.write(
                template.render({"data": json.dumps(self.as_json(), indent=4)})
            )
        # Create index page
        template = Template(
            pkg_resources.resource_string(
                "html_test_report", os.path.join("templates", "test-case.html")
            ).decode("utf-8")
        )
        index_html = self._html_path / "index.html"
        with codecs.open(str(index_html), "w", encoding="utf-8") as outfile:
            outfile.write(template.render(self._global_context))
