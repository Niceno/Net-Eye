import urllib.request
import threading
import ctypes
from ctypes import wintypes
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------
# Settings -- unchanged from the original
# ----------------------------------------------------------------------

SIZE            =   70
CHECK_EVERY_MS  = 5000
TIMEOUT_SECONDS =    2

GREEN = "#27c93f"
RED   = "#ff3b30"
GRAY  = "#808080"

# Wi-Fi icon settings (all dimensions are in final on-screen pixels).
WIFI_SIZE         = 40   # Overall Wi-Fi symbol width
WIFI_X_OFFSET     =  0   # Shift right (+) or left (-) from circle centre
WIFI_Y_OFFSET     = 10   # Shift down (+) or up (-) from circle centre
WIFI_STROKE       =  4   # Thickness of the Wi-Fi arcs
WIFI_DOT_RADIUS   =  4   # Radius of the centre dot (pixels)
WIFI_DOT_GAP      =  3   # Clear gap between dot edge and innermost arc
WIFI_ARC_SPACING  =  7   # Radial spacing between adjacent arcs
WIFI_COLOR        = "#000000"

# ----------------------------------------------------------------------
# NEW: a few Win32 definitions needed for a true alpha-transparent window
# ----------------------------------------------------------------------

user32   = ctypes.windll.user32
gdi32    = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

WS_EX_LAYERED    = 0x00080000
WS_EX_TOPMOST    = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP         = 0x80000000

WM_DESTROY     = 0x0002
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONUP   = 0x0205
WM_TIMER       = 0x0113
WM_COMMAND     = 0x0111
WM_APP_STATUS  = 0x8001

WM_NCLBUTTONDOWN = 0x00A1
HTCAPTION        = 2

MF_STRING       = 0x0000
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD   = 0x0100

ULW_ALPHA      = 0x00000002
AC_SRC_OVER    = 0x00
AC_SRC_ALPHA   = 0x01
BI_RGB         = 0
DIB_RGB_COLORS = 0

ID_CHECK_NOW = 1
ID_EXIT      = 2
TIMER_ID     = 1

IDC_ARROW = 32512

LRESULT = ctypes.c_ssize_t

# Correct 64-bit prototype for the default Windows message handler
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM
]
user32.DefWindowProcW.restype = LRESULT


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", RGBQUAD * 1),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


# ----------------------------------------------------------------------
# NEW: draw the circle with real alpha, so the edge blends with whatever
# is behind it. Pillow draws it 4x larger and downsamples it smoothly.
# ----------------------------------------------------------------------

SCALE = 4

def draw_wifi_icon(draw, disconnected=False):
    """Draw a centred, scalable Wi-Fi icon at supersampled resolution."""
    cx = (SIZE / 2 + WIFI_X_OFFSET) * SCALE
    cy = (SIZE / 2 + WIFI_Y_OFFSET) * SCALE
    stroke = max(1, round(WIFI_STROKE * SCALE))
    dot_r = WIFI_DOT_RADIUS * SCALE

    # Pillow draws arc strokes inward from their bounding radii.
    # Anchor the innermost arc to the dot, keeping the clear gap fixed
    # when WIFI_DOT_RADIUS changes. Each outer arc adds a fixed step.
    inner_r = (WIFI_DOT_RADIUS + WIFI_DOT_GAP + WIFI_STROKE) * SCALE
    for index in (2, 1, 0):
        r = inner_r + index * WIFI_ARC_SPACING * SCALE
        draw.arc((round(cx-r), round(cy-r), round(cx+r), round(cy+r)),
                 start=225, end=315, fill=WIFI_COLOR, width=stroke)

    draw.ellipse((round(cx-dot_r), round(cy-dot_r),
                  round(cx+dot_r), round(cy+dot_r)), fill=WIFI_COLOR)

def make_circle(color, disconnected=False):
    big_size = SIZE * SCALE
    image = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = 5 * SCALE

    draw.ellipse(
        (margin, margin, big_size - margin, big_size - margin),
        fill=color,
        outline="#202020",
        width=3 * SCALE,
    )

    draw_wifi_icon(draw, disconnected=disconnected)

    image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

    # UpdateLayeredWindow expects premultiplied BGRA pixels.
    pixels = bytearray(image.tobytes("raw", "BGRA"))

    for i in range(0, len(pixels), 4):
        alpha = pixels[i + 3]
        pixels[i] = pixels[i] * alpha // 255
        pixels[i + 1] = pixels[i + 1] * alpha // 255
        pixels[i + 2] = pixels[i + 2] * alpha // 255

    return bytes(pixels)


def draw_circle(hwnd, color, disconnected=False):
    pixels = make_circle(color, disconnected=disconnected)

    screen_dc = user32.GetDC(None)
    memory_dc = gdi32.CreateCompatibleDC(screen_dc)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = SIZE
    bmi.bmiHeader.biHeight = -SIZE       # top-down bitmap
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB

    bits = ctypes.c_void_p()

    bitmap = gdi32.CreateDIBSection(
        memory_dc,
        ctypes.byref(bmi),
        DIB_RGB_COLORS,
        ctypes.byref(bits),
        None,
        0,
    )

    ctypes.memmove(bits, pixels, len(pixels))

    old_bitmap = gdi32.SelectObject(memory_dc, bitmap)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    destination = wintypes.POINT(rect.left, rect.top)
    source = wintypes.POINT(0, 0)
    size = wintypes.SIZE(SIZE, SIZE)

    blend = BLENDFUNCTION(
        AC_SRC_OVER,
        0,
        255,
        AC_SRC_ALPHA,
    )

    user32.UpdateLayeredWindow(
        hwnd,
        screen_dc,
        ctypes.byref(destination),
        ctypes.byref(size),
        memory_dc,
        ctypes.byref(source),
        0,
        ctypes.byref(blend),
        ULW_ALPHA,
    )

    gdi32.SelectObject(memory_dc, old_bitmap)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory_dc)
    user32.ReleaseDC(None, screen_dc)


# ----------------------------------------------------------------------
# Internet check -- essentially unchanged
# ----------------------------------------------------------------------

def internet_is_up():
    try:
        with urllib.request.urlopen(
            "https://www.google.com/generate_204",
            timeout=TIMEOUT_SECONDS,
        ):
            return True
    except:
        return False


hwnd = None


def check_internet():
    def worker():
        online = internet_is_up()

        # Tell the Windows message loop to redraw the circle.
        user32.PostMessageW(
            hwnd,
            WM_APP_STATUS,
            1 if online else 0,
            0,
        )

    threading.Thread(target=worker, daemon=True).start()


# ----------------------------------------------------------------------
# NEW: native Windows mouse/menu handling replaces the Tkinter bindings.
# ----------------------------------------------------------------------

def show_menu(hwnd):
    menu = user32.CreatePopupMenu()

    user32.AppendMenuW(menu, MF_STRING, ID_CHECK_NOW, "Check now")
    user32.AppendMenuW(menu, MF_STRING, ID_EXIT, "Exit")

    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))

    user32.SetForegroundWindow(hwnd)

    command = user32.TrackPopupMenu(
        menu,
        TPM_RIGHTBUTTON | TPM_RETURNCMD,
        point.x,
        point.y,
        0,
        hwnd,
        None,
    )

    user32.DestroyMenu(menu)

    if command == ID_CHECK_NOW:
        check_internet()
    elif command == ID_EXIT:
        user32.DestroyWindow(hwnd)


@WNDPROC
def window_proc(window, message, wparam, lparam):
    if message == WM_LBUTTONDOWN:
        # Same behaviour as the old Tkinter drag code.
        user32.ReleaseCapture()
        user32.SendMessageW(window, WM_NCLBUTTONDOWN, HTCAPTION, 0)
        return 0

    if message == WM_RBUTTONUP:
        show_menu(window)
        return 0

    if message == WM_TIMER:
        if wparam == TIMER_ID:
            check_internet()
        return 0

    if message == WM_APP_STATUS:
        draw_circle(window, GREEN if wparam else RED, disconnected=not bool(wparam))
        return 0

    if message == WM_DESTROY:
        user32.KillTimer(window, TIMER_ID)
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(window, message, wparam, lparam)


# ----------------------------------------------------------------------
# NEW: create the tiny layered window instead of a Tkinter window.
# ----------------------------------------------------------------------

hinstance = kernel32.GetModuleHandleW(None)
class_name = "NetEyeWindow"

window_class = WNDCLASSW()
window_class.lpfnWndProc = window_proc
window_class.hInstance = hinstance
window_class.hCursor = user32.LoadCursorW(
    None,
    ctypes.c_void_p(IDC_ARROW)
)
window_class.lpszClassName = class_name

user32.RegisterClassW(ctypes.byref(window_class))

hwnd = user32.CreateWindowExW(
    WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
    class_name,
    "NetEye",
    WS_POPUP,
    100,
    100,
    SIZE,
    SIZE,
    None,
    None,
    hinstance,
    None,
)

# Start gray, exactly as before.
draw_circle(hwnd, GRAY)

user32.ShowWindow(hwnd, 5)
user32.SetTimer(hwnd, TIMER_ID, CHECK_EVERY_MS, None)

# First check immediately.
check_internet()

# Windows message loop.
message = wintypes.MSG()

while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
    user32.TranslateMessage(ctypes.byref(message))
    user32.DispatchMessageW(ctypes.byref(message))
