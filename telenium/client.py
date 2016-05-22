
def run_client():
    import code
    import readline
    import rlcompleter
    import pyjsonrpc
    cli = pyjsonrpc.HttpClient(url="http://localhost:9901/jsonrpc", timeout=5)

    vars = globals()
    vars.update(locals())
    readline.set_completer(rlcompleter.Completer(vars).complete)
    readline.parse_and_bind("tab: complete")
    shell = code.InteractiveConsole(vars)
    shell.interact()

if __name__ == "__main__":
    import sys
    import subprocess
    proc = None
    if len(sys.argv) > 1:
        executable_name = sys.argv[1]
        proc = subprocess.Popen(["python", "-m", "telenium.execute", executable_name])
    run_client()
