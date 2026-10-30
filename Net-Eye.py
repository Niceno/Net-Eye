import urllib.request
import threading
import functools
import ctypes
from ctypes import wintypes
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------
# Settings -- unchanged from the original
# ----------------------------------------------------------------------

SIZE            =   70
CHECK_EVERY_MS  = 5000
TIMEOUT_SECONDS =    2
ARC_STEP_MS     =  150   # Delay between arcs while a check is animating
ANIMATE_EVERY   =    6   # Animate every n-th check (1 = every check)

GREEN = "#27c93f"
RED   = "#ff3b30"
GRAY  = "#808080"

# Wi-Fi icon settings (all dimensions are in pixels at 100 % display
# scaling; they grow with Windows scaling, e.g. by 10 % at 110 %).
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
WM_DPICHANGED  = 0x02E0

SWP_NOZORDER   = 0x0004
SWP_NOACTIVATE = 0x0010

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

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
ANIM_TIMER_ID = 2

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


# Full 64-bit prototypes for every Win32 call used below. Without these,
# ctypes assumes 32-bit int arguments and results, truncating handles.
UINT_PTR = ctypes.c_size_t

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype  = wintypes.HMODULE

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype  = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype  = ctypes.c_int
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype  = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND,
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    wintypes.COLORREF,
    ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.PostMessageW.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.SendMessageW.restype = LRESULT

user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype  = wintypes.HMENU
user32.AppendMenuW.argtypes = [
    wintypes.HMENU, wintypes.UINT, UINT_PTR, wintypes.LPCWSTR
]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.BOOL
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype  = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype  = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype  = wintypes.BOOL
user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype  = wintypes.BOOL

user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype  = wintypes.HANDLE
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype  = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype  = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype  = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext.restype  = wintypes.BOOL
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.GetDpiForWindow.restype  = wintypes.UINT

user32.SetTimer.argtypes = [
    wintypes.HWND, UINT_PTR, wintypes.UINT, ctypes.c_void_p
]
user32.SetTimer.restype = UINT_PTR
user32.KillTimer.argtypes = [wintypes.HWND, UINT_PTR]
user32.KillTimer.restype  = wintypes.BOOL

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype  = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype  = LRESULT
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype  = None

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype  = wintypes.HDC
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype  = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype  = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype  = wintypes.BOOL


# ----------------------------------------------------------------------
# NEW: draw the circle with real alpha, so the edge blends with whatever
# is behind it. Pillow draws it 4x larger and downsamples it smoothly.
# ----------------------------------------------------------------------

SCALE = 4

# Display scaling of the monitor the window is on (1.0 = 100 %, 96 DPI).
# All sizes above are given at 100 % and multiplied by this when drawing.
dpi_scale = 1.0

# Last drawn colour and number of arcs, so the circle can be redrawn
# on DPI change and the animation knows which colour to keep.
current_look = (GRAY, 3)


def window_size():
    return round(SIZE * dpi_scale)


def draw_wifi_icon(draw, arcs=3):
    """Draw a centred, scalable Wi-Fi icon at supersampled resolution.

    arcs is how many arcs to draw (0-3), counted from the innermost one;
    the dot is always drawn.
    """
    s = dpi_scale * SCALE
    cx = window_size() * SCALE / 2 + WIFI_X_OFFSET * s
    cy = window_size() * SCALE / 2 + WIFI_Y_OFFSET * s
    stroke = max(1, round(WIFI_STROKE * s))
    dot_r = WIFI_DOT_RADIUS * s

    # Pillow draws arc strokes inward from their bounding radii.
    # Anchor the innermost arc to the dot, keeping the clear gap fixed
    # when WIFI_DOT_RADIUS changes. Each outer arc adds a fixed step.
    inner_r = (WIFI_DOT_RADIUS + WIFI_DOT_GAP + WIFI_STROKE) * s
    for index in range(arcs):
        r = inner_r + index * WIFI_ARC_SPACING * s
        draw.arc((round(cx-r), round(cy-r), round(cx+r), round(cy+r)),
                 start=225, end=315, fill=WIFI_COLOR, width=stroke)

    draw.ellipse((round(cx-dot_r), round(cy-dot_r),
                  round(cx+dot_r), round(cy+dot_r)), fill=WIFI_COLOR)

# Only a handful of distinct images exist (colour x arcs x DPI), so each
# is rendered once; animation frames then cost almost nothing. The dpi
# argument is not used directly, it only keeps the cache per DPI.
@functools.lru_cache(maxsize=None)
def make_circle(color, arcs, dpi):
    size = window_size()
    big_size = size * SCALE
    image = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    s = dpi_scale * SCALE
    margin = round(5 * s)

    draw.ellipse(
        (margin, margin, big_size - margin, big_size - margin),
        fill=color,
        outline="#202020",
        width=round(3 * s),
    )

    draw_wifi_icon(draw, arcs=arcs)

    image = image.resize((size, size), Image.Resampling.LANCZOS)

    # UpdateLayeredWindow expects premultiplied BGRA pixels.
    pixels = bytearray(image.tobytes("raw", "BGRA"))

    for i in range(0, len(pixels), 4):
        alpha = pixels[i + 3]
        pixels[i] = pixels[i] * alpha // 255
        pixels[i + 1] = pixels[i + 1] * alpha // 255
        pixels[i + 2] = pixels[i + 2] * alpha // 255

    return bytes(pixels)


def draw_circle(hwnd, color, arcs=3):
    global current_look
    current_look = (color, arcs)

    pixels = make_circle(color, arcs, dpi_scale)
    width = window_size()

    screen_dc = user32.GetDC(None)
    memory_dc = gdi32.CreateCompatibleDC(screen_dc)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -width      # top-down bitmap
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
    size = wintypes.SIZE(width, width)

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
        ) as response:
            # Captive portals answer with their login page (200), not 204.
            return response.status == 204
    except OSError:
        return False


hwnd = None
check_lock = threading.Lock()

# Animation state, only touched from the Windows message loop thread.
animating      = False
pending_result = None   # None while the check runs, then True / False
check_count    = 0


def check_internet(animate=False):
    """Start a check; animate it if asked to, or if it is every n-th one."""
    global check_count

    # Skip this check if the previous one is still running (e.g. slow DNS).
    # An explicit request still animates, waiting for the running check.
    if not check_lock.acquire(blocking=False):
        if animate:
            start_animation()
        return

    if animate or check_count % ANIMATE_EVERY == 0:
        start_animation()
    check_count += 1

    def worker():
        try:
            online = internet_is_up()
        finally:
            check_lock.release()

        # Tell the Windows message loop to redraw the circle.
        user32.PostMessageW(
            hwnd,
            WM_APP_STATUS,
            1 if online else 0,
            0,
        )

    threading.Thread(target=worker, daemon=True).start()


# ----------------------------------------------------------------------
# Check animation: the arcs are drawn one by one, smallest first, in the
# circle's current colour. The sweep repeats until the check result is in,
# then the circle shows all arcs on green, or just the dot on red.
# ----------------------------------------------------------------------

def start_animation():
    global animating, pending_result
    pending_result = None
    if animating:
        return
    animating = True
    draw_circle(hwnd, current_look[0], arcs=0)
    user32.SetTimer(hwnd, ANIM_TIMER_ID, ARC_STEP_MS, None)


def animation_step():
    global animating
    color, arcs = current_look

    if arcs < 3:
        draw_circle(hwnd, color, arcs=arcs + 1)
    elif pending_result is None:
        draw_circle(hwnd, color, arcs=0)      # still checking: sweep again
    else:
        user32.KillTimer(hwnd, ANIM_TIMER_ID)
        animating = False
        show_result(pending_result)


def show_result(online):
    if online:
        draw_circle(hwnd, GREEN, arcs=3)
    else:
        draw_circle(hwnd, RED, arcs=0)


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
        check_internet(animate=True)
    elif command == ID_EXIT:
        user32.DestroyWindow(hwnd)


@WNDPROC
def window_proc(window, message, wparam, lparam):
    global dpi_scale, pending_result

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
        elif wparam == ANIM_TIMER_ID:
            animation_step()
        return 0

    if message == WM_APP_STATUS:
        # A running animation picks this up when its sweep completes.
        # A silent check shows its result right away, except that coming
        # back online builds the arcs up with one sweep.
        online = bool(wparam)
        if animating:
            pending_result = online
        elif online and current_look[0] != GREEN:
            start_animation()
            pending_result = online
        else:
            show_result(online)
        return 0

    if message == WM_DPICHANGED:
        # Moved to a monitor with different scaling: resize and redraw.
        dpi_scale = (wparam & 0xFFFF) / 96
        suggested = wintypes.RECT.from_address(lparam)
        user32.SetWindowPos(
            window,
            None,
            suggested.left,
            suggested.top,
            window_size(),
            window_size(),
            SWP_NOZORDER | SWP_NOACTIVATE,
        )
        draw_circle(window, *current_look)
        return 0

    if message == WM_DESTROY:
        user32.KillTimer(window, TIMER_ID)
        user32.KillTimer(window, ANIM_TIMER_ID)
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

# Handle display scaling ourselves, so Windows does not blur the window
# by stretching it. Must happen before the window is created.
user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)

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

dpi_scale = user32.GetDpiForWindow(hwnd) / 96

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
