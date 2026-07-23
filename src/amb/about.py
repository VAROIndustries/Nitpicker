"""About dialog: version info and links to varo.industries. Not unit-tested (UI)."""
import webbrowser

from amb import __version__

TOOL_URL = "https://varo.industries/tools/nitpicker"
GITHUB_URL = "https://github.com/VAROIndustries/Nitpicker"


def show_about():
    import tkinter as tk

    root = tk.Tk()
    root.title("About Nitpicker")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    pad = tk.Frame(root, padx=24, pady=18)
    pad.pack()

    tk.Label(pad, text="Nitpicker", font=("Segoe UI", 16, "bold")).pack()
    tk.Label(pad, text=f"Version {__version__}", fg="#555").pack(pady=(2, 0))
    tk.Label(pad, text="One brightness knob for every monitor.",
             fg="#333").pack(pady=(6, 12))

    def _link(parent, text, url):
        lbl = tk.Label(parent, text=text, fg="#1a6ec8", cursor="hand2",
                       font=("Segoe UI", 9, "underline"))
        lbl.pack()
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        return lbl

    _link(pad, "varo.industries/tools/nitpicker", TOOL_URL)
    _link(pad, "github.com/VAROIndustries/Nitpicker", GITHUB_URL)

    tk.Label(pad, text="© 2026 VARØ Industries", fg="#888").pack(pady=(12, 10))
    tk.Button(pad, text="Close", width=10, command=root.destroy).pack()

    root.mainloop()
