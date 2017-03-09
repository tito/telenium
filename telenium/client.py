# coding=utf-8

import argparse
import pyjsonrpc
from time import time, sleep


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


def run_client(host="localhost", port=9901):
    import code
    import readline
    import rlcompleter
    url = "http://{host}:{port}/jsonrpc".format(host=host, port=port)
    cli = TeleniumHttpClient(url=url, timeout=5)

    print("Connecting to {}".format(url))
    while not cli.ping():
        sleep(.1)
    print("Connected!")

    vars = globals()
    vars.update(locals())
    readline.set_completer(rlcompleter.Completer(vars).complete)
    readline.parse_and_bind("tab: complete")
    shell = code.InteractiveConsole(vars)
    shell.interact()


def run():
    parser = argparse.ArgumentParser(description="Telenium Client")
    parser.add_argument(
        "host", type=str, default="localhost", help="Telenium Host IP")
    parser.add_argument(
        "--port", type=int, default=9901, help="Telenium Host Port")
    args = parser.parse_args()
    run_client(host=args.host, port=args.port)


if __name__ == "__main__":
    run()
