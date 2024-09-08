#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()


setup(
    name="html_test_report",
    version="1.1.3",
    description="Python unittest runner with html report.",
    url="https://github.com/adelplanque/html-test-report",
    packages=("html_test_report",),
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "html-test = html_test_report.html_test:main",
        ],
        "nose.plugins.0.10": [
            "html-test = html_test_report.nose_plugin:HtmlTestNosePlugin"
        ],
        "pytest11": ["html_test = html_test_report.pytest_plugin"],
    },
    package_data={
        "html_test_report": [
            "templates/test-case.html",
        ]
    },
    install_requires=[
        "jinja2",
        "pygments",
        "python-magic",
        "six",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
    ],
)
