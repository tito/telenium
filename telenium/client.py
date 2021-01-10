# coding=utf-8

import argparse
import requests
import json
from time import time, sleep


class TeleniumHttpException(Exception):
    pass


class TeleniumHttpClientMethod(object):
    _id = 0
    def __init__(self, client, method):
        self.client = client
        self.method = method
        super(TeleniumHttpClientMethod, self).__init__()

    def __call__(self, *args):
        TeleniumHttpClientMethod._id += 1
        _id = TeleniumHttpClientMethod._id
        payload = {
            "method": self.method,
            "params": args,
            "jsonrpc": "2.0",
            "id": _id
        }
        headers = {"Content-Type": "application/json"}
        print(f"> {self.method}: {args}")
        response = requests.post(
            self.client.url, data=json.dumps(payload),
            headers=headers).json()
        assert(response["jsonrpc"])
        try:
            return response["result"]
        except:
            raise TeleniumHttpException(response["error"]["message"])


class TeleniumHttpClient(object):
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        super(TeleniumHttpClient, self).__init__()

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

    def wait_drag(self, selector, target, duration, timeout):
        if (
            self.wait(selector, timeout=timeout) and
            self.wait(target, timeout=timeout)
        ):
            self.drag(selector, target, duration)

    def screenshot(self, filename=None):
        import base64
        ret = TeleniumHttpClientMethod(self, "screenshot")()
        if ret:
            ret["data"] = base64.b64decode(ret["data"].encode("utf-8"))
            if filename:
                ret["filename"] = filename
                with open(filename, "wb") as fd:
                    fd.write(ret["data"])
        return ret

    def execute(self, code):
        from textwrap import dedent
        return TeleniumHttpClientMethod(self, "execute")(dedent(code))

    def sleep(self, seconds):
        print(f"> sleep {seconds} seconds")
        sleep(seconds)

    def __getattr__(self, attr):
        return TeleniumHttpClientMethod(self, attr)


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
