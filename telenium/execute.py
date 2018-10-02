# coding=utf-8

def run_executable(executable_name):
    # insert the telenium module path
    # we do the import here to be able to load kivy args
    from kivy.modules import Modules
    from kivy.config import Config
    from os.path import dirname, join
    import runpy

    Modules.add_path(join(dirname(__file__), "mods"))
    Config.set("modules", "telenium_client", "")
    runpy.run_path(executable_name, run_name="__main__")


if __name__ == "__main__":
    import sys
    executable_name = sys.argv[1]
    sys.argv = sys.argv[1:]  # pop the first one
    run_executable(executable_name)
