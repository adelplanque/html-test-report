#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from setuptools import setup

setup(
    name                 = 'html_test',
    version              = '0.1',
    description          = 'Python unittest runner with html report.',
    packages             = ('html_test', ),
    entry_points         = {
        "console_scripts": [
            "html-test = html_test.html_test:main",
        ],
        'nose.plugins.0.10': [
            'html-test = html_test.nose_plugin:HtmlTestNosePlugin'
        ]
    },
    package_data         = {
        'html_test': [
            'templates/test-case.html',
        ]
    },
    install_requires=[
        "jinja2",
        "pygments",
        "six",
    ]
)
