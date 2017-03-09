"""
Telenium: automation for Kivy application
"""

import re
import codecs
import os
try:
    from ez_setup import use_setuptools
    use_setuptools()
except:
    pass
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

try:
    import pypandoc
    long_description = pypandoc.convert("README.md", "rst")
except ImportError:
    long_description = open("README.md").read()


def find_version(*file_paths):
    with codecs.open(os.path.join(here, *file_paths), "r", "latin1") as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="telenium",
    version=find_version("telenium", "__init__.py"),
    url="http://github.com/tito/telenium",
    license="MIT",
    author="Mathieu Virbel",
    author_email="mat@meltingrocks.com",
    description=("Kivy automation, can be used to do GUI tests."),
    long_description=long_description,
    keywords=["kivy", "automate", "unittest", "wait", "condition"],
    packages=["telenium", "telenium.mods"],
    entry_points={
        "console_scripts": [
            "telenium=telenium.web:run",
            "telenium-cli=telenium.client:run"
        ]
    },
    install_requires=[
        "Mako>=1.0.6",
        "CherryPy==8.5.0",  # recent cherrypy are incompatible with ws4py
        "ws4py>=0.3.5",
        "python-jsonrpc>=0.10.0"
    ],
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta", "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License", "Operating System :: POSIX",
        "Operating System :: MacOS", "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Build Tools", "Topic :: Internet",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring"
    ])
