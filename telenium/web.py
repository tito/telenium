# coding=utf-8

import os
import functools
import threading
import cherrypy
import json
import subprocess
from mako.template import Template
from uuid import uuid4
from telenium.client import TeleniumHttpClient
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from os.path import dirname, join, realpath
from time import time, sleep

TPL_EXPORT_UNITTEST = u"""<%!
    def pprint(text):
        from pprint import pformat
        return pformat(text)
%># coding=utf-8

from telenium.tests import TeleniumTestCase


class AppTestCase(TeleniumTestCase):
    % if env:
    cmd_env = ${ env }
    % endif

    def test_app(self):
        % for key, value in tests:
        % if key == "wait":
        self.cli.wait('${value}', timeout=10)
        % elif key == "wait_click":
        self.cli.wait_click('${value}', timeout=10)
        % elif key == "assertExists":
        self.assertExists('${value}', timeout=10)
        % elif key == "assertNotExists":
        self.assertNotExists('${value}', timeout=10)
        % endif
        % endfor

# telenium export, don't delete
export = ${ session | pprint,n }
"""


def threaded(f):
    @functools.wraps(f)
    def _threaded(*args, **kwargs):
        thread = threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return _threaded


class ApiWebSocket(WebSocket):
    t_process = None
    cli = None
    session = {"entrypoint": "", "env": {}, "tests": []}

    def opened(self):
        super(ApiWebSocket, self).opened()
        self.load()

    def closed(self, code, reason=None):
        pass

    def received_message(self, message):
        msg = json.loads(message.data)
        getattr(self, "cmd_{}".format(msg["cmd"]))(msg["options"])

    def send_object(self, obj):
        data = json.dumps(obj)
        self.send(data, False)

    def save(self):
        with open("session.dat", "w") as fd:
            fd.write(json.dumps(self.session))

    def load(self):
        try:
            with open("session.dat") as fd:
                self.session.update(json.loads(fd.read()))
        except:
            pass

    # command implementation

    def cmd_recover(self, options):
        self.send_object(["entrypoint", self.session["entrypoint"]])
        self.send_object(["env", self.session["env"].items()])
        self.send_object(["tests", self.session["tests"]])
        if self.t_process is not None:
            self.send_object(["status", "running"])

    def cmd_sync_env(self, options):
        while self.session["env"]:
            self.session["env"].pop(self.session["env"].keys()[0])
        for key, value in options.get("env", {}).items():
            self.session["env"][key] = value
        self.save()

    def cmd_sync_entrypoint(self, options):
        self.session["entrypoint"] = options["entrypoint"]
        self.save()

    def cmd_sync_tests(self, options):
        self.session["tests"] = options["tests"]
        self.save()

    def cmd_select(self, options):
        if not self.cli:
            status = "error"
            results = "Application not running"
        else:
            try:
                results = self.cli.highlight(options["selector"])
                status = "ok"
            except Exception as e:
                status = "error"
                results = u"{}".format(e)
        self.send_object(["select", options["selector"], status, results])

    @threaded
    def cmd_pick(self, options):
        if not self.cli:
            return self.send_object(["pick", "error", "App is not started"])
        objs = self.cli.pick(all=True)
        return self.send_object(["pick", "success", objs])

    @threaded
    def cmd_execute(self, options):
        self.ev_process = threading.Event()
        self.execute()

    def cmd_run_test(self, options):
        self.run_test(options["index"])

    def cmd_run_tests(self, options):
        self.ev_process = threading.Event()
        self.execute()
        self.ev_process.wait()
        self.run_tests()

    def cmd_export(self, options):
        try:
            export = self.export(options["type"])
            self.send_object(["export", options["type"], export])
        except Exception as e:
            self.send_object(["export", "error", u"{}".format(e)])

    def export(self, kind):
        if kind == "python":
            return Template(TPL_EXPORT_UNITTEST).render(session=self.session,
                                                        **self.session)
        elif kind == "json":
            return json.dumps(self.session,
                              sort_keys=True,
                              indent=4,
                              separators=(',', ': '))

    @threaded
    def execute(self, wait=True):
        self.send_object(["status", "running"])
        self.t_process = None
        try:
            self.start_process()
            self.ev_process.set()
            self.t_process.communicate()
            self.send_object(["status", "stopped"])
        except Exception as e:
            try:
                self.t_process.terminate()
            except:
                pass
            self.send_object(["status", "exception", u"{}".format(e)])
        finally:
            self.t_process = None
            self.ev_process.set()

    def start_process(self):
        url = "http://localhost:9901/jsonrpc"
        process_start_timeout = 10
        telenium_token = str(uuid4())
        self.cli = cli = TeleniumHttpClient(url=url, timeout=10)

        # entry no any previous telenium is running
        try:
            cli.app_quit()
            sleep(2)
        except:
            pass

        # prepare the application
        cmd = ["python", "-m", "telenium.execute", self.session["entrypoint"]]
        cwd = dirname(self.session["entrypoint"])
        env = os.environ.copy()
        env.update(self.session["env"])
        env["TELENIUM_TOKEN"] = telenium_token

        # start the application
        self.t_process = subprocess.Popen(cmd, env=env, cwd=cwd)

        # wait for telenium server to be online
        start = time()
        while True:
            try:
                if cli.app_ready():
                    break
            except Exception:
                if time() - start > process_start_timeout:
                    raise Exception("timeout")
                sleep(1)

        # ensure the telenium we are connected are the same as the one we
        # launched here
        if cli.get_token() != telenium_token:
            raise Exception("Connected to another telenium server")

    def run_tests(self):
        for index in range(len(self.session["tests"])):
            if not self.run_test(index):
                break
            sleep(0.2)

    def run_test(self, index):
        try:
            self.send_object(["run_test", index, "running"])
            success = self._run_test(index)
            if success:
                self.send_object(["run_test", index, "success"])
                return True
            else:
                self.send_object(["run_test", index, "error"])
        except Exception as e:
            self.send_object(["run_test", index, "error", str(e)])

    def _run_test(self, index):
        cmd, selector = self.session["tests"][index]
        timeout = 5
        if cmd == "wait":
            return self.cli.wait(selector, timeout=timeout)
        elif cmd == "wait_click":
            self.cli.wait_click(selector, timeout=timeout)
            return True
        elif cmd == "assertExists":
            return self.cli.wait(selector, timeout=timeout) is True
        elif cmd == "assertNotExists":
            return self.assertNotExists(self.cli, selector, timeout=timeout)

    def assertNotExists(self, cli, selector, timeout=-1):
        start = time()
        while True:
            matches = cli.select(selector)
            if not matches:
                return True
            if timeout == -1:
                raise AssertionError("selector matched elements")
            if timeout > 0 and time() - start > timeout:
                raise Exception("Timeout")
            sleep(0.1)


class Root(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/static/index.html")

    @cherrypy.expose
    def ws(self):
        pass


class WebSocketServer(object):
    def __init__(self, host="0.0.0.0", port=8080):
        super(WebSocketServer, self).__init__()
        self.host = host
        self.port = port
        self.daemon = True

    def run(self):
        cherrypy.config.update({
            "server.socket_port": self.port,
            "server.socket_host": self.host,
        })
        cherrypy.tree.mount(Root(),
                            "/",
                            config={
                                "/": {
                                    "tools.sessions.on": True
                                },
                                "/ws": {
                                    "tools.websocket.on": True,
                                    "tools.websocket.handler_cls": ApiWebSocket
                                },
                                "/static": {
                                    "tools.staticdir.on": True,
                                    "tools.staticdir.dir": join(
                                        realpath(dirname(__file__)), "static"),
                                    "tools.staticdir.index": "index.html"
                                }
                            })
        cherrypy.engine.start()
        cherrypy.engine.block()

    def stop(self):
        cherrypy.engine.exit()
        cherrypy.server.stop()


def preload_session(filename):
    import imp
    mod = imp.load_source("session", filename)
    if not hasattr(mod, "export"):
        print "ERROR: no telenium export found in", filename
    else:
        with open("session.dat", "w") as fd:
            fd.write(json.dumps(mod.export))

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

if __name__ == "__main__":
    import sys
    print sys.argv
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        preload_session(filename)
    server = WebSocketServer(port=8080)
    server.run()
    server.stop()
