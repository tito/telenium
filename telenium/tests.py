# coding=utf-8

import unittest
import subprocess
import os
from telenium.client import TeleniumHttpClient
from time import time, sleep
from uuid import uuid4


class TeleniumTestCase(unittest.TestCase):
    """Telenium unittest TestCase, that can be run with any runner like pytest.
    """

    #: Telenium url to connect to
    telenium_url = "http://localhost:9901/jsonrpc"

    #: Timeout of the process to start, in seconds
    process_start_timeout = 5

    #: Environment variables that can be passed to the process
    cmd_env = {}

    #: Entrypoint of the process
    cmd_entrypoint = ["main.py"]

    #: Command to start the process (cmd_entrypoint is appended to this)
    cmd_process = ["python", "-m", "telenium.execute"]

    _telenium_init = False

    @classmethod
    def start_process(cls):
        host = os.environ.get("TELENIUM_HOST", "localhost")
        if "TELENIUM_HOST" in os.environ:
            url = "http://{}:{}/jsonrpc".format(
                os.environ.get("TELENIUM_HOST", "localhost"),
                int(os.environ.get("TELENIUM_PORT", "9901")))
        else:
            url = cls.telenium_url

        cls.telenium_token = str(uuid4())
        cls.cli = TeleniumHttpClient(url=url, timeout=5)

        # prior test, close any possible previous telenium application
        # to ensure this one might be executed correctly.
        try:
            cls.cli.app_quit()
            sleep(2)
        except:
            pass

        # prepare the environment of the application to start
        env = os.environ.copy()
        env["TELENIUM_TOKEN"] = cls.telenium_token
        for key, value in cls.cmd_env.items():
            env[key] = str(value)
        cmd = cls.cmd_process + cls.cmd_entrypoint

        # start the application
        if os.environ.get("TELENIUM_TARGET", None) == "android":
            cls.start_android_process(env=env)
        else:
            cls.start_desktop_process(cmd=cmd, env=env)

        # wait for telenium server to be online
        start = time()
        while True:
            try:
                cls.cli.ping()
                break
            except Exception:
                if time() - start > cls.process_start_timeout:
                    raise Exception("timeout")
                sleep(1)

        # ensure the telenium we are connected are the same as the one we
        # launched here
        if cls.cli.get_token() != cls.telenium_token:
            raise Exception("Connected to another telenium server")

    @classmethod
    def start_desktop_process(cls, cmd, env):
        cwd = os.path.dirname(cls.cmd_entrypoint[0])
        cls.process = subprocess.Popen(cmd, env=env, cwd=cwd)

    @classmethod
    def start_android_process(cls, env):
        import subprocess
        import json
        package = os.environ.get("TELENIUM_ANDROID_PACKAGE", None)
        entry = os.environ.get("TELENIUM_ANDROID_ENTRY",
                               "org.kivy.android.PythonActivity")
        telenium_env = cls.cmd_env.copy()
        telenium_env["TELENIUM_TOKEN"] = env["TELENIUM_TOKEN"]
        cmd = [
            "adb", "shell", "am", "start", "-n",
            "{}/{}".format(package, entry), "-a", entry
        ]

        filename = "/tmp/telenium_env.json"
        with open(filename, "w") as fd:
            fd.write(json.dumps(telenium_env))
        cmd_env = ["adb", "push", filename, "/sdcard/telenium_env.json"]
        print("Execute: {}".format(cmd_env))
        subprocess.Popen(cmd_env).communicate()
        print("Execute: {}".format(cmd))
        cls.process = subprocess.Popen(cmd)
        print cls.process.communicate()

    @classmethod
    def stop_process(cls):
        cls.cli.app_quit()
        cls.process.wait()

    @classmethod
    def setUpClass(cls):
        TeleniumTestCase._telenium_init = False
        cls.start_process()
        super(TeleniumTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        TeleniumTestCase._telenium_init = False
        cls.stop_process()
        super(TeleniumTestCase, cls).tearDownClass()

    def setUp(self):
        if not TeleniumTestCase._telenium_init:
            if hasattr(self, "init"):
                self.init()
            TeleniumTestCase._telenium_init = True

    def assertExists(self, selector, timeout=-1):
        self.assertTrue(self.cli.wait(selector, timeout=timeout))

    def assertNotExists(self, selector, timeout=-1):
        start = time()
        while True:
            matches = self.cli.select(selector)
            if not matches:
                return True
            if timeout == -1:
                raise AssertionError("selector matched elements")
            if timeout > 0 and time() - start > timeout:
                raise Exception("Timeout")
            sleep(0.1)
