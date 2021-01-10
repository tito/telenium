# coding=utf-8

__version__ = "0.5.0"


def install():
    """Install the kivy telenium module into the kivy instance
    """
    from .mods.telenium_client import install as mod_install
    return mod_install()


def connect(host="localhost", port=9901, timeout=5):
    from .client import TeleniumHttpClient
    """Connect to a remote telenium kivy module
    """
    return TeleniumHttpClient(f"http://{host}:{port}/jsonrpc", timeout=timeout)
