import tkinter as tk
import urllib.request
import threading

SIZE = 70
CHECK_EVERY_MS = 5000
TIMEOUT_SECONDS = 2

GREEN = "#27c93f"
RED = "#ff3b30"
GRAY = "#808080"
TRANSPARENT = "magenta"

root = tk.Tk()

root.overrideredirect(True)
root.attributes("-topmost", True)
root.configure(bg=TRANSPARENT)
root.wm_attributes("-transparentcolor", TRANSPARENT)
root.geometry(f"{SIZE}x{SIZE}+100+100")

canvas = tk.Canvas(
    root,
    width=SIZE,
    height=SIZE,
    bg=TRANSPARENT,
    highlightthickness=0
)
canvas.pack()

circle = canvas.create_oval(
    5, 5,
    SIZE - 5, SIZE - 5,
    fill=GRAY,
    outline="#202020",
    width=3
)


def internet_is_up():
    try:
        with urllib.request.urlopen(
            "https://www.google.com/generate_204",
            timeout=TIMEOUT_SECONDS
        ):
            return True
    except:
        return False


def check_internet():
    def worker():
        online = internet_is_up()

        root.after(
            0,
            lambda: canvas.itemconfig(
                circle,
                fill=GREEN if online else RED
            )
        )

        root.after(CHECK_EVERY_MS, check_internet)

    threading.Thread(target=worker, daemon=True).start()


drag_x = 0
drag_y = 0


def start_drag(event):
    global drag_x, drag_y
    drag_x = event.x
    drag_y = event.y


def drag(event):
    x = root.winfo_pointerx() - drag_x
    y = root.winfo_pointery() - drag_y
    root.geometry(f"+{x}+{y}")


canvas.bind("<ButtonPress-1>", start_drag)
canvas.bind("<B1-Motion>", drag)

menu = tk.Menu(root, tearoff=0)
menu.add_command(label="Check now", command=check_internet)
menu.add_separator()
menu.add_command(label="Exit", command=root.destroy)


def show_menu(event):
    menu.tk_popup(event.x_root, event.y_root)


canvas.bind("<Button-3>", show_menu)

check_internet()
root.mainloop()
