import sys
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

    def selectFirst(self, selector, root=None):
        if root is None:
            root = App.get_running_app().root
        parser = XpathParser()
        matches = parser.parse(selector).execute(root)
        if matches:
            return matches[0]

    def getattr(self, selector, key):
        widget = self.selectFirst(selector)
        if widget:
            return getattr(widget, key)

    def path_to(self, widget):
        root = App.get_running_app().root
        if widget.parent is root:
            return "/{}".format(widget.__class__.__name__)
        return "{}/{}[{}]".format(
            self.path_to(widget.parent),
            widget.__class__.__name__,
            widget.parent.children.index(widget))

    @pyjsonrpc.rpcmethod
    @kivythread
    def setattr(self, selector, key, value):
        widget = self.selectFirst(selector)
        if widget:
            setattr(widget, key, value)
            return True

    @pyjsonrpc.rpcmethod
    @kivythread
    def element(self, selector):
        if self.selectFirst(selector):
            return True

    @pyjsonrpc.rpcmethod
    def pick(self):
        widget = [None]
        ev = threading.Event()
        def on_touch_down(win, touch):
            app = App.get_running_app().root
            widget[0] = pick(app, touch.x, touch.y)
            ev.set()
            return True
        from kivy.core.window import Window
        Window.bind(on_touch_down=on_touch_down)
        ev.wait()
        Window.unbind(on_touch_down=on_touch_down)
        if widget[0]:
            return self.path_to(widget[0])

    @pyjsonrpc.rpcmethod
    @kivythread
    def click_on(self, selector):
        w = self.selectFirst(selector)
        if w:
            from kivy.core.window import Window
            cx, cy = w.center
            sx = cx / float(Window.width)
            sy = cy / float(Window.height)
            me = TeleniumMotionEvent("telenium", id=next(nextid), args=[sx, sy])
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
    client = pyjsonrpc.ThreadingHttpServer(
        server_address = ("localhost", 9901),
        RequestHandlerClass = TeleniumClient
    )
    client.serve_forever()


def start(win, ctx):
    Logger.info("TeleniumClient: Start")
    ctx.thread = threading.Thread(target=run_telenium)
    ctx.thread.daemon = True
    ctx.thread.start()


def stop(win, ctx):
    pass
