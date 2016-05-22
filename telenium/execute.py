# coding=utf-8

from kivy.modules import Modules
from kivy.config import Config
from os.path import dirname, join
import runpy


def run_executable(executable_name):
    # insert the telenium module path
    Modules.add_path(join(dirname(__file__), "mods"))
    Config.set("modules", "telenium_client", "")
    runpy.run_path(executable_name, run_name="__main__")


if __name__ == "__main__":
    import sys
    executable_name = sys.argv[1]
    run_executable(executable_name)
