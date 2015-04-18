# Telenium

Telenium automates Kivy-based application.

WIP, too early for documenting anything.


## Development

Start your application with:

    python -m telenium.execute /path/to/your/app.py

Connect to it:

    python -m telenium.client

And play:

    >>> id = cli.pick() # then click somewhere on the UI
    >>> cli.click_at(id)
    True
    >>> cli.setattr("//Label", "color", (0, 1, 0, 1))
    True

If a command returns True, it means it has been successful, otherwise it
returns None.
