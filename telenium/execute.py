import sys
import kivy
from kivy.modules import Modules
from kivy.config import Config
from os.path import dirname, join
import runpy

# insert the telenium module path
Modules.add_path(join(dirname(__file__), "mods"))
Config.set("modules", "telenium_client", "")
executable_name = sys.argv[1]
runpy.run_path(executable_name, run_name="__main__")
