from time import time, sleep
import pyjsonrpc


class TeleniumHttpClient(pyjsonrpc.HttpClient):
    def wait(self, selector, timeout=-1):
        start = time()
        while True:
            matches = self.select(selector)
            if matches:
                return True
            if timeout == -1:
                return False
            if timeout > 0 and time() - start > timeout:
                raise Exception("Timeout")
            sleep(0.1)

    def wait_click(self, selector, timeout=-1):
        if self.wait(selector, timeout=timeout):
            self.click_on(selector)


def run_client():
    import code
    import readline
    import rlcompleter
    cli = TeleniumHttpClient(url="http://localhost:9901/jsonrpc", timeout=5)

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
        proc = subprocess.Popen(["python", "-m", "telenium.execute",
                                 executable_name])
    run_client()
