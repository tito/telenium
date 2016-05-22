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
    description=(
        "Kivy automation, can be used to do ui tests."),
    keywords=["kivy", "automate", "unittest", "wait", "condition"],
    packages=["telenium"],
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Internet",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring"])
