# coding=utf-8

import sys
import os
import re
from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
import threading
import pyjsonrpc
import traceback
from telenium.xpath import XpathParser
from kivy.input.motionevent import MotionEvent
from kivy.input.provider import MotionEventProvider
from kivy.compat import unichr
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
        from kivy.core.window import Window
        root = Window
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
    def app_ready(self):
        app = App.get_running_app()
        if app is None:
            return False
        if app.root is None:
            return False
        return True

    @pyjsonrpc.rpcmethod
    def select(self, selector, with_bounds=False):
        if not with_bounds:
            return map(self.path_to, self.selectAll(selector))

        results = []
        for widget in self.selectAll(selector):
            left, bottom = widget.to_window(widget.x, widget.y)
            right, top = widget.to_window(widget.x + widget.width, widget.y + widget.height)
            bounds = (left, bottom, right, top)
            path = self.path_to(widget)
            results.append((path, bounds))
        return results

    @pyjsonrpc.rpcmethod
    def highlight(self, selector):
        if not selector:
            results = []
        else:
            try:
                results = self.select(selector, with_bounds=True)
            except:
                self._highlight([])
                raise
        self._highlight(results)
        return results

    @kivythread
    def _highlight(self, results):
        from kivy.graphics import Color, Rectangle, Canvas
        from kivy.core.window import Window
        if not hasattr(self, "_canvas"):
            self._canvas = Canvas()

        Window.canvas.remove(self._canvas)
        Window.canvas.add(self._canvas)

        self._canvas.clear()
        with self._canvas:
            Color(1, 0, 0, 0.5)
            for widget, bounds in results:
                left, bottom, right, top = bounds
                Rectangle(pos=(left, bottom), size=(right-left, top-bottom))

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
            traceback.print_exc()
            return False
        return True

    @pyjsonrpc.rpcmethod
    def pick(self, all=False):
        from kivy.core.window import Window
        widgets = []
        ev = threading.Event()

        def on_touch_down(touch):
            root = App.get_running_app().root
            for widget in Window.children:
                if all:
                    widgets.extend(list(collide_at(root, touch.x, touch.y)))
                else:
                    widget = pick(root, touch.x, touch.y)
                    widgets.append(widget)
            ev.set()
            return True

        orig_on_touch_down = Window.on_touch_down
        Window.on_touch_down = on_touch_down
        ev.wait()
        Window.on_touch_down = orig_on_touch_down
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

    @pyjsonrpc.rpcmethod
    def send_keycode(self, keycodes):
        # very hard to get it right, not fully tested and fail proof.
        # just the basics.
        from kivy.core.window import Keyboard
        keys = keycodes.split("+")
        scancode = 0
        key = None
        sym = ""
        modifiers = []
        for el in keys:
            if re.match("^[A-Z]", el):
                lower_el = el.lower()
                # modifier detected ? add it
                if lower_el in ("ctrl", "meta", "alt", "shift"):
                    modifiers.append(lower_el)
                    continue
                # not a modifier, convert to scancode
                sym = lower_el
                key = Keyboard.keycodes.get(lower_el, 0)
            else:
                # may fail, so nothing would be done.
                try:
                    key = int(el)
                    sym = unichr(key)
                except:
                    traceback.print_exc()
                    return False
        self._send_keycode(key, scancode, sym, modifiers)
        return True

    @kivythread
    def _send_keycode(self, key, scancode, sym, modifiers):
        from kivy.core.window import Window
        print("Telenium: send key key={!r} scancode={} sym={!r} modifiers={}".format(
            key, scancode, sym, modifiers
        ))
        if not Window.dispatch("on_key_down", key, scancode, sym, modifiers):
            Window.dispatch("on_keyboard", key, scancode, sym, modifiers)
        Window.dispatch("on_key_up", key, scancode)
        return True


def register_input_provider():
    global telenium_input
    telenium_input = TeleniumInputProvider("telenium", None)
    from kivy.base import EventLoop
    EventLoop.add_input_provider(telenium_input)


def run_telenium():
    Logger.info("TeleniumClient: Started at 0.0.0.0:9901")
    register_input_provider()
    client = pyjsonrpc.ThreadingHttpServer(server_address=("0.0.0.0", 9901),
                                           RequestHandlerClass=TeleniumClient)
    client.serve_forever()


def start(win, ctx):
    Logger.info("TeleniumClient: Start")
    ctx.thread = threading.Thread(target=run_telenium)
    ctx.thread.daemon = True
    ctx.thread.start()


def stop(win, ctx):
    pass
