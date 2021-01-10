# Telenium

Telenium provide a framework to remote tests or automation Kivy-based application:

- Selector support using XPATH-like syntax (`//BoxLayout[0]/Button[@text~="Close"]`)
- Create selector by touching the UI
- Query or set attribute on any widgets
- Execute remote code
- `unittests` support
- Integrate as a Kivy modules
- Web IDE
- Python 2 and 3 (since version 0.4, using json-rpc)

![Telenium IDE](https://cloud.githubusercontent.com/assets/37904/22790912/f44b8166-eee7-11e6-9a78-120f78bde220.png)

![Telenium IDE export](https://cloud.githubusercontent.com/assets/37904/22791059/70fb6988-eee8-11e6-91f4-0b87af33b5b6.png)

# Installation

```
pip install telenium
```

# Run the Telenium IDE

It will start a webserver on http://127.0.0.1:8080/ and automatically open a new
tab in your favorite webbrowser. You'll be able to configure where your main.py
is, and start writing tests directly:

```
telenium
```

You can also edit telenium-json:

```
telenium tests/test-ui-myfeature.json
```

# Run the application with telenium module

If you don't use the IDE, in order to remote control your application,
you need the Telenium client installed within your application.

## Method 1: Run your application with telenium client

Telenium can execute your application and manually add telenium_client to it.
Just do:

```python
python -m telenium.execute main.py
```

## Method 2: Import and install telenium client in your application

Telenium client can be imported and installed at the start of your application:

If telenium is fully available:
```python
from telenium import install
install()
```

If you only included `telenium_client.py` module:
```python
from telenium_client import install
install()
```

## Method 3: Add telenium_client as a Kivy modules into your application

Just copy/paste `mods/telenium_client.py` in your application, then before
running your application, initialize it:

```python
from os.path import dirname
from kivy.modules import Modules
from kivy.config import Config
Modules.add_path(dirname(__file__))
Config.set("modules", "telenium_client", "")
```

You also need to add `python-jsonrpc` in your dependencies (`pip install python-jsonrpc`)

# Remote automation

You can easily create a script that will connect to your telenium client, and do stuff.

```python
import telenium
cli = telenium.connect()

# wait until the SaveCSVButton instance is in the widget tree.
cli.wait_click("//SaveCSVButton")
# wait that one label have Export to CSV text
cli.wait("//Label[@text~=\"Export to CSV\"]", timeout=2)
# make a screenshot !
result = cli.screenshot()
print(result["filename"])
print(result["data"])
```

# Connect to a telenium-ready application

We have a command line client to play with. After the application is started,
you can connect with::

    $ python -m telenium.client localhost

Then play with it. `cli` is the telenium client where you can invoke remote
commands. See the `Telenium commands` to see what you can do:

```python
>>> id = cli.pick() # then click somewhere on the UI
>>> cli.click_at(id)
True
>>> cli.setattr("//Label", "color", (0, 1, 0, 1))
True
```

If a command returns True, it means it has been successful, otherwise it
returns None.

# Create unit tests

Telenium have a module you can use that ease unit tests: it launch the app
and execute tests. For now, it has been tested and coded to work only
locally using subprocess.

Additionnal methods:
- `assertExists(selector, timeout=-1)` and
  `assertNotExists(selector, timeout=-1)` to check if a selector exists or not
  in the app. They both have a `timeout` parameter that, if it reach, will fail
  the test.
- `cli.wait_click(selector, timeout=-1)`: easy way to wait a selector to match,
  then click on the first widget.

Here is a real example that launch an app (default is "main.py"):

- It first go in the menu to click where it need to save a CSV (`SaveButton`, `CascadeSaveButton` then `SaveCSVButton`)
- Then wait at maximum 2s the popup to show with a label "Export to CSV"
- Then click on the "Close" button in the popup
- Then ensure the popup is closed by checking the label is gone.

Example:

```python
from telenium.tests import TeleniumTestCase

class UITestCase(TeleniumTestCase):
    cmd_entrypoint = ["main.py"]

    def test_export_csv(self):
        self.cli.wait_click("//SaveButton")
        self.cli.wait_click("//CascadeSaveButton")
        self.cli.wait_click("//SaveCSVButton")
        self.assertExists("//Label[@text~=\"Export to CSV\"]", timeout=2)
        self.cli.wait_click("//FitButton[@text=\"Close\"]", timeout=2)
        self.assertNotExists("//Label[@text~=\"Export to CSV\"]", timeout=2)
```

Each new TeleniumTestCase will close and start the application, so you always
run from a clean app. If you always need to do something before starting the
test, you can overload the `init`. This will be executed once before any
tests in the class starts:

```python
class UITestCase(TeleniumTestCase):
    def init(self):
        self.cli.wait_click("//PresetSelectionItem[@text!~=\"ttyUSB0 on mintel\"]",
                           timeout=10)
        self.cli.wait_click("//Button[@text=\"Connect\"]")
        self.cli.wait("//BottomLabel[@text=\"Done\"]", timeout=10)
```

You can also change few parameters to change/add things in your application for
unit testing if needed:

```python
class UITestCase(TeleniumTestCase):
    process_start_timeout = 5
    cmd_env = {"I_AM_RUNNING_TEST": 1}
```

# Telenium commands

## `version()`

Return the current API version. You can use it to know which methods are
available.

```python
>>> cli.version()
1
```

## `select(selector)`

Return unique selectors for all widgets that matches the `selector`.

```python
>>> cli.select("//Label")
[u"/WindowSDL/GridLayout/Label[0]", u"/WindowSDL/GridLayout/Label[1]"]
```

## `getattr(selector, key)`

Return the value of an attribute on the first widget found by the `selector`.

```python
>>> cli.getattr("//Label", "text")
u"Hello world"
```

## `setattr(selector, key, value)`

Set an attribute named by `key` to `value` for all widgets that matches the
`selector`.

```python
>>> cli.setattr("//Label", "text", "Plop")
True
```

## `element(selector)`

Return `True` if at least one widget match the `selector`.

```python
>>> cli.element("//Label")
True
>>> cli.element("//InvalidButton")
False
```

## `execute(code)`

Execute python code in the application. Only the "app" symbol that point to the
current running application is available. Return True if the code executed, or
False if the code failed. Exception will be print withing the application logs.

```python
>>> cli.execute("app.call_one_app_method")
True
```

## `pick(all=False)`

Return either the first widget selector you touch on the screen (`all=False`,
the default), either it return the list of all the wigdets that are traversed
where you touch the screen.

```python
>>> cli.pick()
u'/WindowSDL/Button[0]'
>>> cli.pick(all=True)
[u'/WindowSDL/Button[0]',u'/WindowSDL']
```

## `click_on(selector)`

Simulate a touch down/up on the first widget that match the `selector`. Return
True if it worked.

```python
>>> cli.click_on("//Button[0]")
True
```

## `screenshot(filename=None)` (>= 0.5.0)

Take a screenshot of the current application in a PNG format.
Data will be saved into filename if passed, or you can have data in the result.

```python
>>> cli.screenshot("hello.png")
{"filename": "hello.png", "data": "base64 utf-8 encoded data..."}
```

## `evaluate(expr)` (>= 0.5.0)

Evaluate an expression, and return the result. Only serializable result can be
fetched, if an object is sent back, you'll receive None.

```python
>>> cli.evaluate("len(app.my_list)")
123
```

## `evaluate_and_store(key, expr)` (>= 0.5.0)

Evaluate an expression, and store the result in a id-map, used by `execute` and `evaluate` method.

```python
>>> cli.evaluate_and_store("root", "app.root.children[0]")
True
>>> cli.execute("root.do_something()")
```

## `select_and_store(key, selector)` (>= 0.5.0)

Select the first widget returned by a selector, and store the result in a id-map, used by `execute` and `evaluate` method.

```python
>>> cli.select_and_store("btn", "//Button[@title~='Login']")
True
>>> cli.execute("btn.disabled = True")
```


# Telenium selector syntax (XPATH)

Cheat sheet about telenium XPATH-based selector implementation.

- Select any widget that match the widget class in the hierarchy: `//CLASS`
- Select a widget that match the tree: `/CLASS`
- Select a widget with attributes `/CLASS[<ATTR SELECTOR>,...]`
- Index selector if there is multiple match: `/CLASS[INDEX]`
- Attribute exists: `@attr`
- Attribute equal to a value: `@attr=VALUE`
- Attribute not equal to a value: `@attr!=VALUE`
- Attribute contain a value: `@attr~=VALUE`
- Attribute does not contain a value: `@attr!~=VALUE`
- Value can be a string, but must be escaped within double quote only.

Some examples:

```
# Select all the boxlayout in the app
//BoxLayout

# Take the first boxlayout
//BoxLayout[0]

# Get the Button as a direct descendant of the BoxLayout
//BoxLayout[0]/Button

# Or get the 5th Button that are anywhere under the BoxLayout (may or may
# not a direct descandant)
//BoxLayout[0]//Button

# Select the button that is written "Close"
//BoxLayout[0]//Button[@text="Close"]

# Select the button that contain "Close"
//BoxLayout[0]//Button[@text~="Close"]
```

# Real life examples

## Automate screenshots of an app

I was having an app where content is displayed randomly. But the client want to review all the texts and position of every content. Easy peasy::

```python
from telenium import connect
prefix = "screenshots/myapp-"

cli = connect()
cli.wait("//MyAppContainer")
cli.select_and_store("root", "//MyAppContainer")

animals_count = cli.evaluate("len(root.animals)")
for index in range(animals_count):
    # get one animal
    cli.evaluate_and_store("animal", f"root.animals[{index}]")
    animal_id = cli.evaluate("animal['id']")
    animal_name = cli.evaluate("animal['title_en']")
    # focus the animal
    cli.execute("root.focus_animal(animal)")
    cli.sleep(3)
    # take a screenshot
    cli.screenshot(f"{prefix}{animal_id}-{animal_name}.png")
    cli.sleep(3)
```

## Automate login and go directly to the right screen

If you code, close your app, restart, login, do many action before reaching the screen you are currently working on, you could automate the first part.

```python
from telenium import connect
cli = connect()
cli.wait('//IntroUI')
cli.execute("app.username = 'username'")
cli.execute("app.userpwd = 'fake'")
cli.click_on('//LoginButton')
cli.wait('//IntroUI')
cli.click_on('//StartButton')
cli.wait('//GameUI')
```