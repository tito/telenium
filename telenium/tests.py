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

    @classmethod
    def start_process(cls):
        cls.telenium_token = str(uuid4())
        cls.cli = TeleniumHttpClient(url=cls.telenium_url, timeout=5)

        # prior test, close any possible previous telenium application
        # to ensure this one might be executed correctly.
        try:
            cls.cli.app_quit()
        except:
            pass

        # prepare the environment of the application to start
        env = os.environ.copy()
        env["TELENIUM_TOKEN"] = cls.telenium_token
        for key, value in cls.cmd_env.items():
            env[key] = str(value)
        cmd = cls.cmd_process + cls.cmd_entrypoint

        # start the application
        cwd = os.path.dirname(cls.cmd_entrypoint[0])
        cls.process = subprocess.Popen(cmd, env=env, cwd=cwd)

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
    def stop_process(cls):
        cls.cli.app_quit()
        cls.process.wait()

    @classmethod
    def setUpClass(cls):
        cls.start_process()
        super(TeleniumTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.stop_process()
        super(TeleniumTestCase, cls).tearDownClass()

    def setUp(self):
        if not hasattr(TeleniumTestCase, "_telenium_init"):
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
