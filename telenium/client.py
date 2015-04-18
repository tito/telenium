import code
import readline
import rlcompleter

import pyjsonrpc
cli = pyjsonrpc.HttpClient(url="http://localhost:9901/jsonrpc")

vars = globals()
vars.update(locals())
readline.set_completer(rlcompleter.Completer(vars).complete)
readline.parse_and_bind("tab: complete")
shell = code.InteractiveConsole(vars)
shell.interact()
