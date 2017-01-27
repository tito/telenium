# coding=utf-8

import sys
import os
from os.path import join, dirname
sys.path += [join(dirname(__file__), "..", "libs")]

from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
import threading
import pyjsonrpc
from telenium.xpath import XpathParser
from kivy.input.motionevent import MotionEvent
from kivy.input.provider import MotionEventProvider
from itertools import count

nextid = count()
telenium_input = None


def kivythread(f):
    def f2(*args, **kwargs):
        ev = threading.Event()
        ev_value = threading.Event()

        def custom_call(dt):
            if f(*args, **kwargs):
                ev_value.set()
            ev.set()

        Clock.schedule_once(custom_call, 0)
        ev.wait()
        return ev_value.is_set()

    return f2


def pick(widget, x, y):
    ret = None
    # try to filter widgets that are not visible (invalid inspect target)
    if (hasattr(widget, 'visible') and not widget.visible):
        return ret
    if widget.collide_point(x, y):
        ret = widget
        x2, y2 = widget.to_local(x, y)
        # reverse the loop - look at children on top first
        for child in reversed(widget.children):
            ret = pick(child, x2, y2) or ret
    return ret


def collide_at(widget, x, y):
    if widget.collide_point(x, y):
        x2, y2 = widget.to_local(x, y)
        have_results = False
        for child in reversed(widget.children):
            for ret in collide_at(child, x2, y2):
                yield ret
                have_results = True
        if not have_results:
            yield widget


class TeleniumMotionEvent(MotionEvent):
    def depack(self, args):
        self.is_touch = True
        self.sx, self.sy = args[:2]
        super(TeleniumMotionEvent, self).depack(args)


class TeleniumInputProvider(MotionEventProvider):
    events = []

    def update(self, dispatch_fn):
        while self.events:
            event = self.events.pop(0)
            dispatch_fn(*event)


class TeleniumClient(pyjsonrpc.HttpRequestHandler):
    @pyjsonrpc.rpcmethod
    def ping(self):
        return True

    @pyjsonrpc.rpcmethod
    def get_token(self):
        return os.environ.get("TELENIUM_TOKEN")

    def selectAll(self, selector, root=None):
        if root is None:
            root = App.get_running_app().root.parent
        parser = XpathParser()
        matches = parser.parse(selector).execute(root)
        return matches or []

    def selectFirst(self, selector, root=None):
        matches = self.selectAll(selector, root=root)
        if matches:
            return matches[0]

    def getattr(self, selector, key):
        widget = self.selectFirst(selector)
        if widget:
            return getattr(widget, key)

    def path_to(self, widget):
        root = App.get_running_app().root
        if widget.parent is root or widget.parent == widget or not widget.parent:
            return "/{}".format(widget.__class__.__name__)
        return "{}/{}[{}]".format(
            self.path_to(widget.parent), widget.__class__.__name__,
            widget.parent.children.index(widget))

    @pyjsonrpc.rpcmethod
    @kivythread
    def app_quit(self):
        App.get_running_app().stop()
        return True

    @pyjsonrpc.rpcmethod
    def select(self, selector):
        return map(self.path_to, self.selectAll(selector))

    @pyjsonrpc.rpcmethod
    def getattr(self, selector, key):
        widget = self.selectFirst(selector)
        try:
            return getattr(widget, key)
        except:
            return

    @pyjsonrpc.rpcmethod
    @kivythread
    def setattr(self, selector, key, value):
        ret = False
        for widget in self.selectAll(selector):
            setattr(widget, key, value)
            ret = True
        return ret

    @pyjsonrpc.rpcmethod
    @kivythread
    def element(self, selector):
        if self.selectFirst(selector):
            return True

    @pyjsonrpc.rpcmethod
    @kivythread
    def execute(self, cmd):
        app = App.get_running_app()
        idmap = {"app": app}
        try:
            exec cmd in idmap, idmap
        except:
            import traceback
            traceback.print_exc()
            return False
        return True

    @pyjsonrpc.rpcmethod
    def pick(self, all=False):
        widgets = []
        ev = threading.Event()

        def on_touch_down(touch):
            root = App.get_running_app().root
            if all:
                widgets[:] = list(collide_at(root, touch.x, touch.y))
            else:
                widget = pick(root, touch.x, touch.y)
                widgets.append(widget)
            ev.set()
            return True

        from kivy.core.window import Window
        # Window.bind(on_touch_down=on_touch_down)
        orig_on_touch_down = Window.on_touch_down
        Window.on_touch_down = on_touch_down
        ev.wait()
        Window.on_touch_down = orig_on_touch_down
        # Window.unbind(on_touch_down=on_touch_down)
        if widgets:
            if all:
                ret = map(self.path_to, widgets)
            else:
                ret = self.path_to(widgets[0])
            return ret

    @pyjsonrpc.rpcmethod
    @kivythread
    def click_on(self, selector):
        w = self.selectFirst(selector)
        if w:
            from kivy.core.window import Window
            cx, cy = w.to_window(w.center_x, w.center_y)
            sx = cx / float(Window.width)
            sy = cy / float(Window.height)
            me = TeleniumMotionEvent("telenium",
                                     id=next(nextid),
                                     args=[sx, sy])
            telenium_input.events.append(("begin", me))
            telenium_input.events.append(("end", me))
            return True


def register_input_provider():
    global telenium_input
    telenium_input = TeleniumInputProvider("telenium", None)
    from kivy.base import EventLoop
    EventLoop.add_input_provider(telenium_input)


def run_telenium():
    Logger.info("TeleniumClient: Started at localhost:9901")
    register_input_provider()
    client = pyjsonrpc.ThreadingHttpServer(server_address=("localhost", 9901),
                                           RequestHandlerClass=TeleniumClient)
    client.serve_forever()


def start(win, ctx):
    Logger.info("TeleniumClient: Start")
    ctx.thread = threading.Thread(target=run_telenium)
    ctx.thread.daemon = True
    ctx.thread.start()


def stop(win, ctx):
    pass
