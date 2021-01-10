# coding=utf-8

VERSION = 2

import sys
import os
import re
import threading
import traceback
from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from jsonrpc import JSONRPCResponseManager, dispatcher
from telenium.xpath import XpathParser
from kivy.input.motionevent import MotionEvent
from kivy.input.provider import MotionEventProvider
from kivy.compat import unichr
from itertools import count
from time import time

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


def pick_widget(widget, x, y):
    ret = None
    # try to filter widgets that are not visible (invalid inspect target)
    if (hasattr(widget, 'visible') and not widget.visible):
        return ret
    if widget.collide_point(x, y):
        ret = widget
        x2, y2 = widget.to_local(x, y)
        # reverse the loop - look at children on top first
        for child in reversed(widget.children):
            ret = pick_widget(child, x2, y2) or ret
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


def selectAll(selector, root=None):
    if root is None:
        root = App.get_running_app().root.parent
    parser = XpathParser()
    matches = parser.parse(selector)
    matches = matches.execute(root)
    return matches or []


def selectFirst(selector, root=None):
    matches = selectAll(selector, root=root)
    if matches:
        return matches[0]


def rpc_getattr(selector, key):
    widget = selectFirst(selector)
    if widget:
        return getattr(widget, key)


def path_to(widget):
    from kivy.core.window import Window
    root = Window
    if widget.parent is root or widget.parent == widget or not widget.parent:
        return "/{}".format(widget.__class__.__name__)
    return "{}/{}[{}]".format(
        path_to(widget.parent), widget.__class__.__name__,
        widget.parent.children.index(widget))


def rpc_ping():
    return True


def rpc_version():
    return VERSION


def rpc_get_token():
    return os.environ.get("TELENIUM_TOKEN")


@kivythread
def rpc_app_quit():
    App.get_running_app().stop()
    return True


def rpc_app_ready():
    app = App.get_running_app()
    if app is None:
        return False
    if app.root is None:
        return False
    return True


def rpc_select(selector, with_bounds=False):
    if not with_bounds:
        return list(map(path_to, selectAll(selector)))

    results = []
    for widget in selectAll(selector):
        left, bottom = widget.to_window(widget.x, widget.y)
        right, top = widget.to_window(widget.x + widget.width, widget.y + widget.height)
        bounds = (left, bottom, right, top)
        path = path_to(widget)
        results.append((path, bounds))
    return results


def rpc_highlight(selector):
    if not selector:
        results = []
    else:
        try:
            results = rpc_select(selector, with_bounds=True)
        except:
            _highlight([])
            raise
    _highlight(results)
    return results


@kivythread
def _highlight(results):
    from kivy.graphics import Color, Rectangle, Canvas
    from kivy.core.window import Window
    if not hasattr(Window, "_telenium_canvas"):
        Window._telenium_canvas = Canvas()
    _canvas = Window._telenium_canvas

    Window.canvas.remove(_canvas)
    Window.canvas.add(_canvas)

    _canvas.clear()
    with _canvas:
        Color(1, 0, 0, 0.5)
        for widget, bounds in results:
            left, bottom, right, top = bounds
            Rectangle(pos=(left, bottom), size=(right-left, top-bottom))


@kivythread
def rpc_setattr(selector, key, value):
    ret = False
    for widget in selectAll(selector):
        setattr(widget, key, value)
        ret = True
    return ret


@kivythread
def rpc_element(selector):
    if selectFirst(selector):
        return True


idmap = {}

@kivythread
def rpc_execute(cmd):
    app = App.get_running_app()
    idmap["app"] = app
    print("execute", cmd)
    try:
        exec(cmd, idmap, idmap)
    except Exception:
        traceback.print_exc()
        return False
    return True


def rpc_evaluate(cmd):
    ev = threading.Event()
    result = []
    _rpc_evaluate(cmd, ev, result)
    ev.wait()
    return result[0]


@kivythread
def _rpc_evaluate(cmd, ev, result):
    app = App.get_running_app()
    idmap["app"] = app
    res = None
    try:
        res = eval(cmd, idmap, idmap)
        result.append(res)
    finally:
        if not result:
            result.append(None)
        ev.set()


def rpc_evaluate_and_store(key, cmd):
    ev = threading.Event()
    result = []
    _rpc_evaluate(cmd, ev, result)
    ev.wait()
    idmap[key] = result[0]
    return True


def rpc_select_and_store(key, selector):
    idmap[key] = result = selectFirst(selector)
    return result is not None


def rpc_pick(all=False):
    from kivy.core.window import Window
    widgets = []
    ev = threading.Event()

    def on_touch_down(touch):
        root = App.get_running_app().root
        for widget in Window.children:
            if all:
                widgets.extend(list(collide_at(root, touch.x, touch.y)))
            else:
                widget = pick_widget(root, touch.x, touch.y)
                widgets.append(widget)
        ev.set()
        return True

    orig_on_touch_down = Window.on_touch_down
    Window.on_touch_down = on_touch_down
    ev.wait()
    Window.on_touch_down = orig_on_touch_down
    if widgets:
        if all:
            ret = list(map(path_to, widgets))
        else:
            ret = path_to(widgets[0])
        return ret


@kivythread
def rpc_click_on(selector):
    w = selectFirst(selector)
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


@kivythread
def rpc_drag(selector, target, duration):
    from kivy.base import EventLoop
    w1 = selectFirst(selector)
    w2 = selectFirst(target)
    duration = float(duration)
    if w1 and w2:
        from kivy.core.window import Window
        cx1, cy1 = w1.to_window(w1.center_x, w1.center_y)
        sx1 = cx1 / float(Window.width)
        sy1 = cy1 / float(Window.height)

        me = TeleniumMotionEvent("telenium",
                                 id=next(nextid),
                                 args=[sx1, sy1])

        telenium_input.events.append(("begin", me))
        if not duration:
            telenium_input.events.append(("end", me))

        else:
            d = 0
            while d < duration:
                t = time()
                EventLoop.idle()
                dt = time() - t
                # need to compute that ever frame, it could have moved
                cx2, cy2 = w2.to_window(w2.center_x, w2.center_y)
                sx2 = cx2 / float(Window.width)
                sy2 = cy2 / float(Window.height)

                dsx = dt * (sx2 - me.sx) / (duration - d)
                dsy = dt * (sy2 - me.sy) / (duration - d)

                me.sx += dsx
                me.sy += dsy

                telenium_input.events.append(("update", me))
                d += dt

        telenium_input.events.append(("end", me))
        return True


def rpc_send_keycode(keycodes):
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
    _send_keycode(key, scancode, sym, modifiers)
    return True


@kivythread
def _send_keycode(key, scancode, sym, modifiers):
    from kivy.core.window import Window
    print("Telenium: send key key={!r} scancode={} sym={!r} modifiers={}".format(
        key, scancode, sym, modifiers
    ))
    if not Window.dispatch("on_key_down", key, scancode, sym, modifiers):
        Window.dispatch("on_keyboard", key, scancode, sym, modifiers)
    Window.dispatch("on_key_up", key, scancode)
    return True


def rpc_screenshot():
    ev = threading.Event()
    result = []
    _rpc_screenshot(ev, result)
    ev.wait()
    return result[0]


@kivythread
def _rpc_screenshot(ev, result):
    import base64
    filename = None
    data = None
    try:
        from kivy.core.window import Window
        filename = Window.screenshot()
        with open(filename, "rb") as fd:
            data = fd.read()
        os.unlink(filename)
        return True
    finally:
        result.append({
            "filename": filename,
            "data": base64.b64encode(data).decode("utf-8")
        })
        ev.set()


def register_input_provider():
    global telenium_input
    telenium_input = TeleniumInputProvider("telenium", None)
    from kivy.base import EventLoop
    EventLoop.add_input_provider(telenium_input)


@Request.application
def application(request):
    print("application request", request.data)
    try:
        response = JSONRPCResponseManager.handle(
            request.data, dispatcher)
        print("application response", response)
        print("application response", response.json)
    except Exception as e:
        print("application exception", e)
        raise
    return Response(response.json, mimetype='application/json')


def run_telenium():
    Logger.info("TeleniumClient: Started at 0.0.0.0:9901")
    register_input_provider()

    dispatcher.add_method(rpc_version, "version")
    dispatcher.add_method(rpc_ping, "ping")
    dispatcher.add_method(rpc_get_token, "get_token")
    dispatcher.add_method(rpc_app_quit, "app_quit")
    dispatcher.add_method(rpc_app_ready, "app_ready")
    dispatcher.add_method(rpc_select, "select")
    dispatcher.add_method(rpc_highlight, "highlight")
    dispatcher.add_method(rpc_getattr, "getattr")
    dispatcher.add_method(rpc_setattr, "setattr")
    dispatcher.add_method(rpc_element, "element")
    dispatcher.add_method(rpc_execute, "execute")
    dispatcher.add_method(rpc_evaluate, "evaluate")
    dispatcher.add_method(rpc_evaluate_and_store, "evaluate_and_store")
    dispatcher.add_method(rpc_select_and_store, "select_and_store")
    dispatcher.add_method(rpc_pick, "pick")
    dispatcher.add_method(rpc_click_on, "click_on")
    dispatcher.add_method(rpc_drag, "drag")
    dispatcher.add_method(rpc_send_keycode, "send_keycode")
    dispatcher.add_method(rpc_screenshot, "screenshot")

    run_simple("0.0.0.0", 9901, application)


def install():
    thread = threading.Thread(target=run_telenium)
    thread.daemon = True
    thread.start()


def start(win, ctx):
    Logger.info("TeleniumClient: Start")
    ctx.thread = threading.Thread(target=run_telenium)
    ctx.thread.daemon = True
    ctx.thread.start()


def stop(win, ctx):
    pass
