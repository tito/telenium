# coding=utf-8

import os
import re
import sys
import functools
import threading
import cherrypy
import json
import subprocess
import traceback
import webbrowser
import argparse
from mako.template import Template
from uuid import uuid4
import telenium
from telenium.client import TeleniumHttpClient
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from os.path import dirname, join, realpath
from time import time, sleep

SESSION_FN = ".telenium.dat"

TPL_EXPORT_UNITTEST = u"""<%!
    def capitalize(text):
        return text.capitalize()
    def camelcase(text):
        return "".join([x.strip().capitalize() for x in text.split()])
    def funcname(text):
        if text == "init":
            return "init"
        import re
        suffix = re.sub(r"[^a-z0-9_]", "_", text.lower().strip())
        return "test_{}".format(suffix)
    def getarg(text):
        import re
        return re.match("^(\w+)", text).groups()[0]
%># coding=utf-8

import time
from telenium.tests import TeleniumTestCase


class ${settings["project"]|camelcase}TestCase(TeleniumTestCase):
    % if env:
    cmd_env = ${ env }
    % endif
    cmd_entrypoint = [u'${ settings["entrypoint"] }']
    % for test in tests:
    % if test["name"] == "setUpClass":
    <% vself = "cls" %>
    @classmethod
    def setUpClass(cls):
        super(${settings["project"]|camelcase}TestCase, cls).setUpClass()
    % else:
    <% vself = "self" %>
    def ${test["name"]|funcname}(self):
        % if not test["steps"]:
        pass
        % endif
    % endif
        % for key, value, arg1, arg2 in test["steps"]:
        % if key == "wait":
        ${vself}.cli.wait('${value}', timeout=${settings["command-timeout"]})
        % elif key == "wait_click":
        ${vself}.cli.wait_click('${value}', timeout=${settings["command-timeout"]})
        % elif key == "assertExists":
        ${vself}.assertExists('${value}', timeout=${settings["command-timeout"]})
        % elif key == "assertNotExists":
        ${vself}.assertNotExists('${value}', timeout=${settings["command-timeout"]})
        % elif key == "assertAttributeValue":
        attr_name = '${arg1|getarg}'
        attr_value = ${vself}.cli.getattr('${value}', attr_name)
        ${vself}.assertTrue(eval('${arg1}', {attr_name: attr_value}))
        % elif key == "setAttribute":
        ${vself}.cli.setattr('${value}', '${arg1}', ${arg2})
        % elif key == "sendKeycode":
        ${vself}.cli.send_keycode('${value}')
        % elif key == "sleep":
        time.sleep(${value})
        % endif
        % endfor
    % endfor
"""

FILE_API_VERSION = 3
local_filename = None


def threaded(f):
    @functools.wraps(f)
    def _threaded(*args, **kwargs):
        thread = threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return _threaded


def funcname(text):
    return text.lower().replace(" ", "_").strip()


def getarg(text):
    return re.match("^(\w+)", text).groups()[0]


class ApiWebSocket(WebSocket):
    t_process = None
    cli = None
    progress_count = 0
    progress_total = 0
    session = {
        "settings": {
            "project": "Test",
            "entrypoint": "main.py",
            "application-timeout": "10",
            "command-timeout": "5"
        },
        "env": {},
        "tests": [{
            "id": str(uuid4()),
            "name": "New test",
            "steps": []
        }]
    }

    def opened(self):
        super(ApiWebSocket, self).opened()
        self.load()

    def closed(self, code, reason=None):
        pass

    def received_message(self, message):
        msg = json.loads(message.data)
        try:
            getattr(self, "cmd_{}".format(msg["cmd"]))(msg["options"])
        except:
            traceback.print_exc()

    def send_object(self, obj):
        data = json.dumps(obj)
        self.send(data, False)

    def save(self):
        self.session["version_format"] = FILE_API_VERSION

        # check if the file changed
        if local_filename is not None:
            changed = False
            try:
                with open(local_filename) as fd:
                    data = json.loads(fd.read())
                changed = data != self.session
            except:
                changed = True
            self.send_object(["changed", changed])

        with open(SESSION_FN, "w") as fd:
            fd.write(json.dumps(self.session))

    def load(self):
        try:
            with open(SESSION_FN) as fd:
                session = json.loads(fd.read())
            session = upgrade_version(session)
            self.session.update(session)
        except:
            pass

    def get_test(self, test_id):
        for test in self.session["tests"]:
            if test["id"] == test_id:
                return test

    def get_test_by_name(self, name):
        for test in self.session["tests"]:
            if test["name"] == name:
                return test

    @property
    def is_running(self):
        return self.t_process is not None

    # command implementation

    def cmd_recover(self, options):
        if local_filename:
            self.send_object(["is_local", True])
        self.send_object(["settings", self.session["settings"]])
        self.send_object(["env", self.session["env"].items()])
        tests = [{
            "name": x["name"],
            "id": x["id"]
        } for x in self.session["tests"]]
        self.send_object(["tests", tests])
        if self.t_process is not None:
            self.send_object(["status", "running"])

    def cmd_save_local(self, options):
        try:
            assert local_filename is not None
            # save json source
            data = self.export("json")
            with open(local_filename, "w") as fd:
                fd.write(data)

            # auto export to python
            filename = local_filename.replace(".json", ".py")
            data = self.export("python")
            with open(filename, "w") as fd:
                fd.write(data)
            self.send_object(["save_local", "ok"])
            self.send_object(["changed", False])
        except Exception as e:
            traceback.print_exc()
            self.send_object(["save_local", "error", repr(e)])

    def cmd_sync_env(self, options):
        while self.session["env"]:
            self.session["env"].pop(self.session["env"].keys()[0])
        for key, value in options.get("env", {}).items():
            self.session["env"][key] = value
        self.save()

    def cmd_sync_settings(self, options):
        self.session["settings"] = options["settings"]
        self.save()

    def cmd_sync_test(self, options):
        uid = options["id"]
        for test in self.session["tests"]:
            if test["id"] == uid:
                test["name"] = options["name"]
                test["steps"] = options["steps"]
        self.save()

    def cmd_add_test(self, options):
        self.session["tests"].append({
            "id": str(uuid4()),
            "name": "New test",
            "steps": []
        })
        self.save()
        self.send_object(["tests", self.session["tests"]])

    def cmd_clone_test(self, options):
        for test in self.session["tests"]:
            if test["id"] != options["test_id"]:
                continue
            clone_test = test.copy()
            clone_test["id"] = str(uuid4())
            clone_test["name"] += " (1)"
            self.session["tests"].append(clone_test)
            break
        self.save()
        self.send_object(["tests", self.session["tests"]])

    def cmd_delete_test(self, options):
        for test in self.session["tests"][:]:
            if test["id"] == options["id"]:
                self.session["tests"].remove(test)
        if not self.session["tests"]:
            self.cmd_add_test(None)
        self.save()
        self.send_object(["tests", self.session["tests"]])

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

    def cmd_select_test(self, options):
        test = self.get_test(options["id"])
        self.send_object(["test", test])

    @threaded
    def cmd_pick(self, options):
        if not self.cli:
            return self.send_object(["pick", "error", "App is not started"])
        objs = self.cli.pick(all=True)
        return self.send_object(["pick", "success", objs])

    @threaded
    def cmd_execute(self, options):
        self.execute()

    def cmd_run_step(self, options):
        self.run_step(options["id"], options["index"])

    @threaded
    def cmd_run_steps(self, options):
        test = self.get_test(options["id"])
        if test is None:
            self.send_object(["alert", "Test not found"])
            return
        if not self.is_running:
            ev_start, ev_stop = self.execute()
            ev_start.wait()
            if ev_stop.is_set():
                return
        self.run_test(test)

    @threaded
    def cmd_run_tests(self, options):
        # restart always from scratch
        self.send_object(["progress", "started"])

        # precalculate the number of steps to run
        count = sum([len(x["steps"]) for x in self.session["tests"]])
        self.progress_count = 0
        self.progress_total = count

        try:
            ev_start, ev_stop = self.execute()
            ev_start.wait()
            if ev_stop.is_set():
                return
            setup = self.get_test_by_name("setUpClass")
            if setup:
                if not self.run_test(setup):
                    return
            setup = self.get_test_by_name("init")
            if setup:
                if not self.run_test(setup):
                    return
            for test in self.session["tests"]:
                if test["name"] in ("setUpClass", "init"):
                    continue
                if not self.run_test(test):
                    return
        finally:
            self.send_object(["progress", "finished"])

    def cmd_stop(self, options):
        if self.t_process:
            self.t_process.terminate()

    def cmd_export(self, options):
        try:
            dtype = options["type"]
            mimetype = {
                "python": "text/plain",
                "json": "application/json"
            }[dtype]
            ext = {"python": "py", "json": "json"}[dtype]
            key = funcname(self.session["settings"]["project"])
            filename = "test_ui_{}.{}".format(key, ext)
            export = self.export(options["type"])
            self.send_object(["export", export, mimetype, filename, dtype])
        except Exception as e:
            self.send_object(["export", "error", u"{}".format(e)])

    def export(self, kind):
        if kind == "python":
            return Template(TPL_EXPORT_UNITTEST).render(
                session=self.session, **self.session)
        elif kind == "json":
            self.session["version_format"] = FILE_API_VERSION
            return json.dumps(
                self.session, sort_keys=True, indent=4, separators=(',', ': '))

    def execute(self):
        ev_start = threading.Event()
        ev_stop = threading.Event()
        self._execute(ev_start=ev_start, ev_stop=ev_stop)
        return ev_start, ev_stop

    @threaded
    def _execute(self, ev_start, ev_stop):
        self.t_process = None
        try:
            self.start_process()
            ev_start.set()
            self.t_process.communicate()
            self.send_object(["status", "stopped", None])
        except Exception as e:
            try:
                self.t_process.terminate()
            except:
                pass
            try:
                self.send_object(["status", "stopped", u"{}".format(e)])
            except:
                pass
        finally:
            self.t_process = None
            ev_stop.set()

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
        entrypoint = self.session["settings"]["entrypoint"]
        cmd = ["python", "-m", "telenium.execute", entrypoint]
        cwd = dirname(entrypoint)
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

        self.send_object(["status", "running"])

    def run_test(self, test):
        test_id = test["id"]
        try:
            self.send_object(["test", test])
            self.send_object(["run_test", test_id, "running"])
            for index, step in enumerate(test["steps"]):
                if not self.run_step(test_id, index):
                    return
            return True
        except Exception as e:
            self.send_object(["run_test", test_id, "error", str(e)])
        else:
            self.send_object(["run_test", test_id, "finished"])

    def run_step(self, test_id, index):
        self.progress_count += 1
        self.send_object(
            ["progress", "update", self.progress_count, self.progress_total])
        try:
            self.send_object(["run_step", test_id, index, "running"])
            success = self._run_step(test_id, index)
            if success:
                self.send_object(["run_step", test_id, index, "success"])
                return True
            else:
                self.send_object(["run_step", test_id, index, "error"])
        except Exception as e:
            self.send_object(["run_step", test_id, index, "error", str(e)])

    def _run_step(self, test_id, index):
        test = self.get_test(test_id)
        if not test:
            raise Exception("Unknown test")
        cmd, selector, arg1, arg2 = test["steps"][index]
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
        elif cmd == "assertAttributeValue":
            attr_name = getarg(arg1)
            attr_value = self.cli.getattr(selector, attr_name)
            return bool(eval(arg1, {attr_name: attr_value}))
        elif cmd == "setAttribute":
            return self.cli.setattr(selector, arg1, eval(arg2))
        elif cmd == "sendKeycode":
            self.cli.send_keycode(selector)
            return True
        elif cmd == "sleep":
            sleep(float(selector))
            return True

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
    def __init__(self, host="0.0.0.0", port=8080, open_webbrowser=True):
        super(WebSocketServer, self).__init__()
        self.host = host
        self.port = port
        self.daemon = True
        self.open_webbrowser = open_webbrowser

    def run(self):
        cherrypy.config.update({
            "global": {
                "environment": "production"
            },
            "server.socket_port": self.port,
            "server.socket_host": self.host,
        })
        cherrypy.tree.mount(
            Root(),
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
                    "tools.staticdir.on":
                    True,
                    "tools.staticdir.dir":
                    join(realpath(dirname(__file__)), "static"),
                    "tools.staticdir.index":
                    "index.html"
                }
            })
        cherrypy.engine.start()
        url = "http://{}:{}/".format(self.host, self.port)
        print("Telenium {} ready at {}".format(telenium.__version__, url))
        if self.open_webbrowser:
            webbrowser.open(url)
        cherrypy.engine.block()

    def stop(self):
        cherrypy.engine.exit()
        cherrypy.server.stop()


def preload_session(filename):
    global local_filename
    local_filename = filename
    if not local_filename.endswith(".json"):
        print("You can load only telenium-json files.")
        sys.exit(1)
    if not os.path.exists(filename):
        print("Create new file at {}".format(local_filename))
        if os.path.exists(SESSION_FN):
            os.unlink(SESSION_FN)
    else:
        with open(filename) as fd:
            session = json.loads(fd.read())
        session = upgrade_version(session)
        with open(SESSION_FN, "w") as fd:
            fd.write(json.dumps(session))


def upgrade_version(session):
    # automatically upgrade to latest version
    version_format = session.get("version_format")
    if version_format is None or version_format == FILE_API_VERSION:
        return session
    session["version_format"] += 1
    version_format = session["version_format"]
    print("Upgrade to version {}".format(version_format))
    if version_format == 2:
        # arg added in steps, so steps must have 3 arguments not 2.
        for test in session["tests"]:
            for step in test["steps"]:
                if len(step) == 2:
                    step.append(None)
    elif version_format == 3:
        # arg added in steps, so steps must have 4 arguments not 3.
        for test in session["tests"]:
            for step in test["steps"]:
                if len(step) == 3:
                    step.append(None)
    return session


WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()


def run():

    parser = argparse.ArgumentParser(description="Telenium IDE")
    parser.add_argument(
        "filename",
        type=str,
        default=None,
        nargs="?",
        help="Telenium JSON file")
    parser.add_argument(
        "--new", action="store_true", help="Start a new session")
    parser.add_argument(
        "--port", type=int, default=8080, help="Telenium IDE port")
    parser.add_argument(
        "--notab",
        action="store_true",
        help="Prevent opening the IDE in the browser")
    args = parser.parse_args()
    if args.new:
        if os.path.exists(SESSION_FN):
            os.unlink(SESSION_FN)
    if args.filename:
        preload_session(args.filename)
    server = WebSocketServer(port=args.port, open_webbrowser=not args.notab)
    server.run()
    server.stop()


if __name__ == "__main__":
    run()
