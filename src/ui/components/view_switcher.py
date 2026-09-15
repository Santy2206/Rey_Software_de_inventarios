"""
Switch entre modo escritorio y modo navegador.

Reutilizable para StatusHeader / PageHeader / Dashboard.
"""

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import flet as ft

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_WEB_HOST = "127.0.0.1"
_WEB_PORT = 8550
_WEB_URL = f"http://{_WEB_HOST}:{_WEB_PORT}"


def _pythonw_exe() -> str:
    scripts = _PROJECT_ROOT / ".venv" / "Scripts"
    for name in ("pythonw.exe", "python.exe"):
        candidate = scripts / name
        if candidate.exists():
            return str(candidate)

    current = Path(sys.executable)
    sibling = current.with_name("pythonw.exe")
    if sibling.exists():
        return str(sibling)
    return str(current)


def _port_is_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_web_ready(timeout_s: float = 12.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_is_open(_WEB_HOST, _WEB_PORT):
            return True
        time.sleep(0.25)
    return False


def _wait_process_alive(process: subprocess.Popen, seconds: float = 3.5) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        time.sleep(0.2)
    return process.poll() is None


def _launch_app(mode: str) -> subprocess.Popen:
    main_script = _PROJECT_ROOT / "main.py"
    log_file = _PROJECT_ROOT / f".tmp_launch_{mode}.log"

    args = [_pythonw_exe(), str(main_script)]
    if mode == "web":
        args.append("--web")
    else:
        args.append("--desktop")

    env = os.environ.copy()
    env["REY_APP_MODE"] = mode
    env.setdefault("PYTHONUNBUFFERED", "1")

    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    log_handle = open(log_file, "w", encoding="utf-8")
    try:
        return subprocess.Popen(
            args,
            cwd=str(_PROJECT_ROOT),
            env=env,
            startupinfo=startupinfo,
            creationflags=creationflags,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            close_fds=False if os.name == "nt" else True,
        )
    finally:
        try:
            log_handle.close()
        except Exception:
            pass


def _read_log(mode: str) -> str:
    log_file = _PROJECT_ROOT / f".tmp_launch_{mode}.log"
    try:
        return log_file.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _get_foreground_hwnd():
    if os.name != "nt":
        return None
    try:
        import ctypes
        return ctypes.windll.user32.GetForegroundWindow()
    except Exception:
        return None


def _window_title(hwnd) -> str:
    if not hwnd:
        return ""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def _window_class(hwnd) -> str:
    if not hwnd:
        return ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
        return buf.value or ""
    except Exception:
        return ""


def _is_browser_hwnd(hwnd) -> bool:
    class_name = _window_class(hwnd)
    markers = (
        "Chrome_WidgetWin",
        "MozillaWindowClass",
        "ApplicationFrameWindow",
    )
    return any(m in class_name for m in markers) or "Chrome" in class_name or "Mozilla" in class_name


def _focus_hwnd(hwnd) -> bool:
    if not hwnd or os.name != "nt":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        SW_SHOW = 5
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def _close_tab_in_hwnd(hwnd) -> bool:
    if not hwnd or os.name != "nt":
        return False
    if not _is_browser_hwnd(hwnd):
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_W = 0x57
        KEYEVENTF_KEYUP = 0x0002

        if not _focus_hwnd(hwnd):
            return False
        time.sleep(0.12)

        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)

        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_W, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(VK_W, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.15)
        return True
    except Exception:
        return False


def _focus_desktop_window(title_contains: str = "REY Inventarios") -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
    )
    IsWindowVisible = user32.IsWindowVisible
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetClassNameW = user32.GetClassNameW
    SetForegroundWindow = user32.SetForegroundWindow
    ShowWindow = user32.ShowWindow
    IsIconic = user32.IsIconic

    SW_RESTORE = 9
    SW_SHOW = 5

    matches = []

    def _callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        length = GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value or ""
        if title_contains.lower() not in title.lower():
            return True

        class_buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value or ""

        browser_markers = (
            "Chrome_WidgetWin",
            "MozillaWindowClass",
            "ApplicationFrameWindow",
        )
        if any(m in class_name for m in browser_markers):
            return True
        if "Chrome" in class_name or "Mozilla" in class_name:
            return True

        matches.append((hwnd, title, class_name))
        return True

    EnumWindows(EnumWindowsProc(_callback), 0)
    if not matches:
        return False

    hwnd = matches[0][0]
    if IsIconic(hwnd):
        ShowWindow(hwnd, SW_RESTORE)
    else:
        ShowWindow(hwnd, SW_SHOW)
    SetForegroundWindow(hwnd)
    return True


class ViewSwitcher:
    """Permite cambiar entre modo escritorio y navegador."""

    def __init__(self):
        self._page = None
        self._cambiando = False

    def set_page(self, page: ft.Page):
        self._page = page

    def switch(self):
        """Ejecuta el cambio de modo según el entorno actual."""
        if not self._page:
            return
        if self._cambiando:
            return

        self._cambiando = True
        source_hwnd = _get_foreground_hwnd() if self._page.web else None
        mode = "desktop" if self._page.web else "web"

        titulo = "Abriendo escritorio..." if mode == "desktop" else "Abriendo navegador..."
        cuerpo = (
            "Abriendo la app de escritorio y cerrando esta pestaña..."
            if mode == "desktop"
            else "Abriendo el navegador con la misma sesión..."
        )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(titulo),
            content=ft.Text(cuerpo),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self._cerrar_dialogo(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        self._page.show_dialog(dlg)

        def _worker():
            try:
                if mode == "web":
                    # Escritorio -> Navegador
                    already = _port_is_open(_WEB_HOST, _WEB_PORT)
                    if not already:
                        process = _launch_app(mode)
                        ready = _wait_web_ready(timeout_s=15)
                        if not ready:
                            raise RuntimeError(
                                _read_log(mode)
                                or "Timeout esperando el servidor web en :8550."
                            )
                    webbrowser.open(_WEB_URL, new=0, autoraise=True)
                    self._page.run_task(self._cerrar_proceso, dlg)
                    return

                # Navegador -> Escritorio
                already_desktop = _focus_desktop_window("REY Inventarios")
                if not already_desktop:
                    process = _launch_app(mode)
                    alive = _wait_process_alive(process, seconds=3.5)
                    if not alive:
                        raise RuntimeError(
                            _read_log(mode)
                            or "La aplicación de escritorio se cerró al iniciar."
                        )
                    time.sleep(1.0)

                if source_hwnd:
                    _close_tab_in_hwnd(source_hwnd)

                for _ in range(8):
                    if _focus_desktop_window("REY Inventarios"):
                        break
                    time.sleep(0.25)

                try:
                    dlg.open = False
                    self._page.update()
                except Exception:
                    pass
            except Exception as ex:
                try:
                    dlg.title = ft.Text("No se pudo cambiar de modo")
                    dlg.content = ft.Text(str(ex))
                    dlg.open = True
                    self._page.update()
                except Exception:
                    pass
            finally:
                self._cambiando = False

        threading.Thread(target=_worker, daemon=True).start()

    def _cerrar_dialogo(self, dlg):
        try:
            dlg.open = False
            self._page.update()
        except Exception:
            pass
        self._cambiando = False

    async def _cerrar_proceso(self, dlg):
        try:
            dlg.open = False
            self._page.update()
        except Exception:
            pass
        time.sleep(0.5)
        try:
            await self._page.window.close()
        except Exception:
            pass
        threading.Timer(0.8, lambda: os._exit(0)).start()
