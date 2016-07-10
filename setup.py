#!/usr/bin/env python
import os.path
from setuptools import setup, find_packages

setup(
    name="funnel-web",
    version="1.0.0",
    author="Jenda Mudron",
    author_email="jenmud@gmail.com",
    maintainer="Jenda Mudron",
    maintainer_email="jenmud@gmail.com",
    url="https://github.com/jenmud/module-dependencies",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Software Development :: Libraries",
    ],
    keywords="graph db momory database in-memory module dependencies",
    description=(
        "Graph and visualize a module's dependencies."
    ),
    packages=find_packages(),
    install_requires=[
        "ruruki-eye",
    ],
    entry_points={
        'console_scripts': [
            'funnel-web = funnel_web.__main__:main'
        ]
    },
)
