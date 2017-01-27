# Telenium

Telenium provide a framework to remote tests or control Kivy-based application:

- selector support using XPath
- create selector by touching the ui
- query or set attribute on any widgets
- execute remote code
- unittests support
- integrate as a Kivy modules

# Run the application with telenium module

In order to remote control your application, you need the Telenium client
installed within your application.

## Method 1: Run your application with telenium client

Telenium can execute your application and manually add telenium_client to it.
Just do::

```python
python -m telenium.execute main.py
```

## Method 2: Add telenium_client as a Kivy modules into your application

Just copy/paste `mods/telenium_client.py` in your application, then before
running your application, initialize it:

```python
from os.path import dirname
from kivy.modules import Modules
from kivy.config import Config
Modules.add_path(dirname(__file__))
Config.set("modules", "telenium_client", "")
```

You also need to add `pyjsonrpc` in your dependencies (`pip install pyjsonrpc`)

# Connect to a telenium-ready application

We have a command line client to play with. After the application is started,
you can connect with::

    $ python -m telenium.client

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

2 new methods have been implemented: `assertExists` and `assertNotExists` to
check if a selector exists or not in the app. They both have a `timeout`
parameter that, if it reach, will fail the test.

Here is a real example that launch an app (default is "main.py"):

- It first go in the menu to click where it need to save a CSV (`SaveButton`, `CascadeSaveButton` then `SaveCSVButton`)
- Then wait at maximum 2s the popup to show with a label "Export to CSV"
- Then click on the "Close" button in the popup
- Then ensure the popup is closed by checking the label is gone.

Example:

```python
from telenium.tests import TeleniumTestCase

class UITestCase(TeleniumTestCase):
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
test, you can overload the `setUpClass`. This will be executed once before any
tests in the class starts:

```python
class UITestCase(TeleniumTestCase):
    @classmethod
    def setUpClass(cls):
        super(UITestCase, cls).setUpClass()
        cls.cli.wait_click("//PresetSelectionItem[@text!~=\"ttyUSB0 on mintel\"]",
                           timeout=10)
        cls.cli.wait_click("//Button[@text=\"Connect\"]")
        cls.cli.wait("//BottomLabel[@text=\"Done\"]", timeout=10)
```

You can also change few parameters to change/add things in your application for
unit testing if needed:

```python
class UITestCase(TeleniumTestCase):
    process_start_timeout = 5
    cmd_env = {"I_AM_RUNNING_TEST": 1}
```

# Telenium commands

## `select(selector)`

Return unique selectors for all widgets that matches the `selector`.

```python
>>> cli.select("//Label")
[u"/WindowSDL/GridLayout/Label[0]", u"/WindowSDL/GridLayout/Label[1]"]
```

## `getattr(selector, key)`

Return the value of an attribute on the first widget found by the `selector`.

```python
>>> cli.getattr("//Label")
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
