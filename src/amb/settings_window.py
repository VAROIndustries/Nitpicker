"""Per-monitor settings window (brightness offset + contrast). Not unit-tested (UI)."""


def open_settings(rows, on_save):
    """Show a settings window.

    rows: list of dicts {key, label, offset, contrast, contrast_supported}
    on_save: callable receiving list of {key, offset, contrast} where contrast is
             an int 0-100 or None (leave the monitor's contrast untouched).
    """
    import tkinter as tk

    root = tk.Tk()
    root.title("Per-monitor settings")
    root.attributes("-topmost", True)

    tk.Label(root, text="Brightness offset is added to the master level.\n"
                        "Contrast is an absolute value; leave 'Set' unchecked to not touch it.",
             justify="left", fg="#555").grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 6),
                                             sticky="w")

    widgets = []
    for i, r in enumerate(rows):
        base = i * 2 + 1
        tk.Label(root, text=r["label"], font=("Segoe UI", 10, "bold")).grid(
            row=base, column=0, columnspan=4, padx=10, pady=(8, 0), sticky="w")

        tk.Label(root, text="Offset").grid(row=base + 1, column=0, padx=(20, 4), sticky="w")
        off_var = tk.IntVar(value=int(r.get("offset") or 0))
        tk.Scale(root, from_=-50, to=50, orient="horizontal", length=200,
                 variable=off_var).grid(row=base + 1, column=1, sticky="w")

        con_enabled = tk.BooleanVar(value=r.get("contrast") is not None)
        con_var = tk.IntVar(value=int(r["contrast"]) if r.get("contrast") is not None else 75)
        supported = r.get("contrast_supported", False)

        con_scale = tk.Scale(root, from_=0, to=100, orient="horizontal", length=200,
                             variable=con_var, state="normal" if (supported and con_enabled.get())
                             else "disabled")

        def _make_toggle(scale, enabled, ok):
            def _t():
                scale.config(state="normal" if (ok and enabled.get()) else "disabled")
            return _t

        con_chk = tk.Checkbutton(root, text="Set contrast", variable=con_enabled,
                                 state="normal" if supported else "disabled",
                                 command=_make_toggle(con_scale, con_enabled, supported))
        con_chk.grid(row=base + 1, column=2, padx=(16, 4), sticky="w")
        con_scale.grid(row=base + 1, column=3, sticky="w")

        widgets.append((r["key"], off_var, con_enabled, con_var, supported))

    def _save():
        results = []
        for key, off_var, con_enabled, con_var, supported in widgets:
            contrast = con_var.get() if (supported and con_enabled.get()) else None
            results.append({"key": key, "offset": off_var.get(), "contrast": contrast})
        on_save(results)
        root.destroy()

    btns = tk.Frame(root)
    btns.grid(row=len(rows) * 2 + 1, column=0, columnspan=4, pady=12)
    tk.Button(btns, text="Save & Apply", command=_save, width=14).pack(side="left", padx=6)
    tk.Button(btns, text="Cancel", command=root.destroy, width=10).pack(side="left", padx=6)

    root.mainloop()
