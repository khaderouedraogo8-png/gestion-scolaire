"""Rendu PDF via WeasyPrint (import différé — GTK requis à l'exécution)."""
import os
import sys

def _gtk_dll_directories() -> list[str]:
    """Retourne les dossiers GTK/Pango, MSYS2 prioritaire."""
    custom = [d.strip() for d in os.getenv("WEASYPRINT_DLL_DIRECTORIES", "").split(";") if d.strip()]
    defaults = [r"C:\msys64\mingw64\bin"]
    if not os.path.isdir(defaults[0]):
        defaults = [
            r"C:\Program Files\GTK3-Runtime Win64\bin",
            r"C:\Program Files\Gtk-Runtime\bin",
        ]
    seen = set()
    result = []
    for directory in custom + defaults:
        if directory not in seen and os.path.isdir(directory):
            seen.add(directory)
            result.append(directory)
    return result


def _register_gtk_dll_dirs() -> None:
    """Enregistre les dossiers GTK pour Python 3.8+ sur Windows."""
    if not hasattr(os, "add_dll_directory") or getattr(sys, "frozen", False):
        return
    for directory in _gtk_dll_directories():
        with __import__("contextlib").suppress(OSError, FileNotFoundError):
            os.add_dll_directory(directory)
    # Prioriser MSYS2 dans PATH pour éviter le Pango obsolète de Gtk-Runtime
    msys = r"C:\msys64\mingw64\bin"
    if os.path.isdir(msys) and msys not in os.environ.get("PATH", ""):
        os.environ["PATH"] = msys + os.pathsep + os.environ.get("PATH", "")


def html_to_pdf(html: str, filepath: str) -> None:
    """Convertit du HTML en PDF. Nécessite GTK/Pango sur Windows."""
    _register_gtk_dll_dirs()
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint requiert GTK/Pango. Sur Windows : "
            "winget install GtkD.GtkPlusRuntime.x64 puis définir "
            "WEASYPRINT_DLL_DIRECTORIES=C:\\Program Files\\Gtk-Runtime\\bin"
        ) from exc
    HTML(string=html).write_pdf(filepath)
