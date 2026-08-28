"""uktools.progress - a scrollable live-log panel for long computations.

AequilibraE's skims and assignments emit a stream of progress bars; in a
terminal they overwrite in place, but in a notebook they stack and mangle.
`progress_box` gives them a proper home: a fixed-height box that captures
everything the wrapped code prints or displays (stdout, stderr, warnings,
tqdm bars), scrolls, and stays pinned to the bottom as new output arrives -
scroll up freely to read history, new output re-pins the view.

    with progress_box("Equilibrium assignment"):
        assig.execute()

Nesting note: AequilibraE picks notebook-style progress bars automatically
when ipywidgets is available, and those render as live widgets inside the
box. Set the environment variable AEQ_SHOW_PROGRESS=FALSE to silence its
bars entirely instead.
"""


class progress_box:
    """Context manager: render all output of the wrapped block inside a
    scrollable, bottom-pinned panel.

    :param title:  optional bold caption above the panel
    :param height: CSS max-height of the panel (default "260px")
    """

    def __init__(self, title=None, height="260px"):
        self.title = title
        self.height = height
        self._out = None

    def __enter__(self):
        try:
            import ipywidgets as W
            from IPython.display import display
        except ImportError:
            return self  # headless / no widgets: plain passthrough
        self._out = W.Output()
        # column-reverse pins the scroll position to the end of the content
        # (the chat-log trick): new output keeps the panel at the bottom,
        # scrolling up to read history still works.
        panel = W.Box([self._out],
                      layout=W.Layout(max_height=self.height, overflow="auto",
                                      display="flex", flex_flow="column-reverse",
                                      border="1px solid #d1d5db", width="100%",
                                      padding="4px"))
        rows = [panel]
        if self.title:
            rows.insert(0, W.HTML(f"<b>{self.title}</b>"))
        display(W.VBox(rows))
        self._out.__enter__()
        return self

    def __exit__(self, *exc):
        if self._out is not None:
            self._out.__exit__(*exc)
        return False
