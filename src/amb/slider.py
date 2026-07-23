def ask_master(initial: int):
    import tkinter as tk
    result = {"value": None}
    root = tk.Tk()
    root.title("Master Brightness")
    root.attributes("-topmost", True)
    var = tk.IntVar(value=initial)

    def commit():
        result["value"] = var.get()
        root.destroy()

    tk.Scale(root, from_=0, to=100, orient="horizontal", length=300,
             variable=var).pack(padx=12, pady=8)
    tk.Button(root, text="Apply", command=commit).pack(pady=(0, 10))
    root.mainloop()
    return result["value"]
