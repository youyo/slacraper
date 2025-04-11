#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="slacraper",
    use_scm_version=True,
    description="Slack message scraper tool",
    author="youyo",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "slack-sdk>=3.0.0",
        "click>=8.0.0",
        "python-dateutil>=2.8.2",
    ],
    python_requires=">=3.12.0",
    entry_points={
        "console_scripts": [
            "slacraper=slacraper.cli:main",
        ],
    },
    setup_requires=["setuptools_scm>=6.2"],
)
