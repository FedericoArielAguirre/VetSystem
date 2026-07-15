# =============================================================================
# VetSystem — app_shell.py
# LoginWindow + MainWindow (sidebar dinámico) + widgets base reutilizables
# =============================================================================

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from app_core import (
    FONTS,
    PALETTE,
    SIDEBAR_ICONS,
    SessionLocal,
    authenticate_user,
    get_user_permissions,
    init_db,
)
from models import Usuario

# Forzar modo claro
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# =============================================================================
# WIDGETS BASE REUTILIZABLES
# =============================================================================

class BaseTable(tk.Frame):
    """
    Wrapper de ttk.Treeview con estilo corporativo.
    Incluye scrollbars, encabezados estilizados y filas alternas.
    """

    def __init__(
        self,
        parent,
        columns: list[dict],  # [{"id": str, "text": str, "width": int, "anchor": str}]
        on_select: Optional[Callable] = None,
        height: int = 18,
        **kwargs,
    ):
        super().__init__(parent, bg=PALETTE["bg_card"], **kwargs)
        self._on_select = on_select
        self._columns = [c["id"] for c in columns]

        # ── Estilo global del Treeview ──────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "VetTree.Treeview",
            background=PALETTE["bg_card"],
            foreground=PALETTE["text"],
            rowheight=28,
            fieldbackground=PALETTE["bg_card"],
            borderwidth=0,
            font=FONTS["body"],
        )
        style.configure(
            "VetTree.Treeview.Heading",
            background=PALETTE["header_bg"],
            foreground=PALETTE["text"],
            font=FONTS["body_bold"],
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "VetTree.Treeview",
            background=[("selected", PALETTE["primary"])],
            foreground=[("selected", "#FFFFFF")],
        )
        style.layout("VetTree.Treeview", [("VetTree.Treeview.treearea", {"sticky": "nswe"})])

        # ── Treeview ────────────────────────────────────────────────────────
        col_ids = [c["id"] for c in columns]
        self.tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            style="VetTree.Treeview",
            height=height,
            selectmode="browse",
        )

        for col in columns:
            self.tree.heading(col["id"], text=col["text"])
            self.tree.column(
                col["id"],
                width=col.get("width", 120),
                anchor=col.get("anchor", "w"),
                stretch=col.get("stretch", True),
            )

        self.tree.tag_configure("alt", background=PALETTE["row_alt"])

        # ── Scrollbars ──────────────────────────────────────────────────────
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select())

    # ── API pública ─────────────────────────────────────────────────────────

    def populate(self, rows: list[tuple]) -> None:
        """Limpia e inserta filas. Alterna color de fila."""
        self.clear()
        for i, row in enumerate(rows):
            tag = "alt" if i % 2 == 1 else ""
            self.tree.insert("", "end", values=row, tags=(tag,))

    def clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def selected_values(self) -> Optional[tuple]:
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0], "values")
        return None

    def selected_iid(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None


# =============================================================================
# LOGIN WINDOW
# =============================================================================

class LoginWindow(ctk.CTk):
    """Ventana de inicio de sesión."""

    def __init__(self):
        super().__init__()
        self.title("VetSystem — Iniciar sesión")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["bg"])

        # Centrar en pantalla
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"420x520+{x}+{y}")

        self._build_ui()

    def _build_ui(self) -> None:
        # ── Logo / título ───────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=PALETTE["primary"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="🐾 VetSystem",
            font=("Segoe UI Semibold", 26),
            text_color="#FFFFFF",
        ).pack(pady=30)

        ctk.CTkLabel(
            header,
            text="Sistema de Gestión Veterinaria",
            font=FONTS["small"],
            text_color="#BDC3C7",
        ).pack(pady=(0, 20))

        # ── Formulario ──────────────────────────────────────────────────────
        form = ctk.CTkFrame(self, fg_color=PALETTE["bg_card"], corner_radius=12)
        form.pack(fill="both", expand=True, padx=30, pady=24)

        ctk.CTkLabel(form, text="Usuario", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).pack(anchor="w", padx=20, pady=(20, 2))
        self.entry_user = ctk.CTkEntry(
            form, placeholder_text="Ingresa tu usuario",
            height=40, font=FONTS["body"],
            border_color=PALETTE["border"], fg_color="#FFFFFF",
        )
        self.entry_user.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text="Contraseña", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).pack(anchor="w", padx=20, pady=(14, 2))
        self.entry_pass = ctk.CTkEntry(
            form, placeholder_text="Ingresa tu contraseña",
            show="•", height=40, font=FONTS["body"],
            border_color=PALETTE["border"], fg_color="#FFFFFF",
        )
        self.entry_pass.pack(fill="x", padx=20)

        # ── Error label ─────────────────────────────────────────────────────
        self.lbl_error = ctk.CTkLabel(
            form, text="", font=FONTS["small"],
            text_color=PALETTE["danger"],
        )
        self.lbl_error.pack(pady=(8, 0))

        # ── Botón ingresar ──────────────────────────────────────────────────
        self.btn_login = ctk.CTkButton(
            form,
            text="Ingresar",
            height=44,
            font=FONTS["body_bold"],
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_dark"],
            corner_radius=8,
            command=self._do_login,
        )
        self.btn_login.pack(fill="x", padx=20, pady=(18, 0))

        ctk.CTkLabel(
            form,
            text="v1.0 — © 2025 VetSystem",
            font=FONTS["small"],
            text_color=PALETTE["text_muted"],
        ).pack(side="bottom", pady=12)

        # Bind Enter key
        self.bind("<Return>", lambda e: self._do_login())
        self.entry_user.focus()

    def _do_login(self) -> None:
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()

        if not username or not password:
            self.lbl_error.configure(text="Por favor completá ambos campos.")
            return

        self.btn_login.configure(state="disabled", text="Verificando…")
        self.update()

        session = SessionLocal()
        user = authenticate_user(session, username, password)

        if user:
            self.btn_login.configure(state="normal", text="Ingresar")
            self.withdraw()
            app = MainWindow(session=session, user=user, login_window=self)
            app.mainloop()
        else:
            session.close()
            self.btn_login.configure(state="normal", text="Ingresar")
            self.lbl_error.configure(text="❌ Usuario o contraseña incorrectos.")
            self.entry_pass.delete(0, "end")


# =============================================================================
# MAIN WINDOW
# =============================================================================

class MainWindow(ctk.CTk):
    """
    Ventana principal con sidebar dinámico por rol y área de contenido
    intercambiable.
    """

    def __init__(self, session, user: Usuario, login_window: LoginWindow):
        super().__init__()
        self.session = session
        self.user = user
        self.login_window = login_window
        self.permissions = get_user_permissions(user.rol.nombre)
        self._frames: dict[str, ctk.CTkFrame] = {}
        self._current_module: Optional[str] = None

        self.title(f"VetSystem — {user.nombre_completo}")
        self.geometry("1280x760")
        self.minsize(960, 600)
        self.configure(fg_color=PALETTE["bg"])

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1280) // 2
        y = (self.winfo_screenheight() - 760) // 2
        self.geometry(f"1280x760+{x}+{y}")

        self._build_layout()
        self._build_sidebar()
        self._load_modules()

        # Mostrar primer módulo accesible
        first = next(iter(self.permissions), None)
        if first:
            self._navigate(first)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        """Divide la ventana en sidebar (izq) y área de contenido (der)."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self, width=210, corner_radius=0,
            fg_color=PALETTE["sidebar_bg"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(20, weight=1)  # empuja logout al fondo

        # Área de contenido
        self.content_area = ctk.CTkFrame(
            self, corner_radius=0, fg_color=PALETTE["bg"]
        )
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

    def _build_sidebar(self) -> None:
        """Construye el sidebar con logo, módulos habilitados y botón de cierre."""
        # ── Logo ────────────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(16, 8))

        ctk.CTkLabel(
            logo_frame, text="🐾",
            font=("Segoe UI", 28),
            text_color=PALETTE["sidebar_fg"],
        ).pack(side="left", padx=(8, 4))

        ctk.CTkLabel(
            logo_frame, text="VetSystem",
            font=("Segoe UI Semibold", 18),
            text_color=PALETTE["sidebar_fg"],
        ).pack(side="left")

        # ── Separador ───────────────────────────────────────────────────────
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color="#3D5166")
        sep.grid(row=1, column=0, sticky="ew", padx=12, pady=4)

        # ── Info usuario ────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.sidebar,
            text=f"{self.user.nombre_completo}",
            font=("Segoe UI Semibold", 12),
            text_color=PALETTE["sidebar_fg"],
            wraplength=180,
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(6, 0))

        ctk.CTkLabel(
            self.sidebar,
            text=f"Rol: {self.user.rol.nombre.capitalize()}",
            font=FONTS["small"],
            text_color="#7F8C8D",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 8))

        sep2 = ctk.CTkFrame(self.sidebar, height=1, fg_color="#3D5166")
        sep2.grid(row=4, column=0, sticky="ew", padx=12, pady=4)

        # ── Botones de módulos ───────────────────────────────────────────────
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        row_idx = 5
        for module_name in _MODULE_ORDER:
            if module_name not in self.permissions:
                continue
            btn = ctk.CTkButton(
                self.sidebar,
                text=SIDEBAR_ICONS.get(module_name, module_name),
                font=FONTS["sidebar"],
                height=40,
                anchor="w",
                fg_color="transparent",
                text_color=PALETTE["sidebar_fg"],
                hover_color=PALETTE["sidebar_sel"],
                corner_radius=8,
                command=lambda m=module_name: self._navigate(m),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=2)
            self._nav_buttons[module_name] = btn
            row_idx += 1

        # ── Logout ──────────────────────────────────────────────────────────
        ctk.CTkButton(
            self.sidebar,
            text="🚪 Cerrar Sesión",
            font=FONTS["sidebar"],
            height=40,
            anchor="w",
            fg_color="transparent",
            text_color="#E74C3C",
            hover_color="#3D5166",
            corner_radius=8,
            command=self._logout,
        ).grid(row=21, column=0, sticky="ew", padx=8, pady=(0, 12))

    def _load_modules(self) -> None:
        """Importa y registra los frames de cada módulo habilitado."""
        # Importaciones diferidas para evitar dependencias circulares
        from modules.pacientes import PacientesFrame
        from modules.turnos import TurnosFrame
        from modules.consultas import ConsultasFrame
        from modules.inventario import InventarioFrame
        from modules.facturacion import FacturacionFrame
        from modules.reportes import ReportesFrame
        from modules.configuracion import ConfiguracionFrame

        _MODULE_CLASSES = {
            "Pacientes":     PacientesFrame,
            "Turnos":        TurnosFrame,
            "Consultas":     ConsultasFrame,
            "Inventario":    InventarioFrame,
            "Facturación":   FacturacionFrame,
            "Reportes":      ReportesFrame,
            "Configuración": ConfiguracionFrame,
        }

        readonly_modules = {
            name for name, perms in self.permissions.items() if perms.get("readonly")
        }

        for module_name, FrameClass in _MODULE_CLASSES.items():
            if module_name not in self.permissions:
                continue
            try:
                readonly = module_name in readonly_modules
                frame = FrameClass(
                    self.content_area,
                    session=self.session,
                    user=self.user,
                    readonly=readonly,
                )
                frame.grid(row=0, column=0, sticky="nsew")
                self._frames[module_name] = frame
            except Exception as exc:
                print(f"[WARN] No se pudo cargar módulo '{module_name}': {exc}")

    # ── Navegación ──────────────────────────────────────────────────────────

    def _navigate(self, module_name: str) -> None:
        """Muestra el frame del módulo seleccionado."""
        if module_name not in self._frames:
            return

        # Actualizar visual del botón activo
        for name, btn in self._nav_buttons.items():
            if name == module_name:
                btn.configure(fg_color=PALETTE["sidebar_sel"])
            else:
                btn.configure(fg_color="transparent")

        # Traer al frente
        self._frames[module_name].tkraise()
        self._current_module = module_name

        # Refrescar si el frame tiene método refresh
        frame = self._frames[module_name]
        if hasattr(frame, "refresh"):
            frame.refresh()

    # ── Cierre y logout ─────────────────────────────────────────────────────

    def _logout(self) -> None:
        msg = CTkMessagebox(
            title="Cerrar sesión",
            message="¿Estás seguro de que querés cerrar la sesión?",
            icon="question",
            option_1="Cancelar",
            option_2="Sí, salir",
        )
        if msg.get() == "Sí, salir":
            self._close_app(reopen_login=True)

    def _on_close(self) -> None:
        self._close_app(reopen_login=False)

    def _close_app(self, reopen_login: bool = False) -> None:
        try:
            self.session.close()
        except Exception:
            pass
        self.destroy()
        if reopen_login:
            self.login_window.deiconify()
            self.login_window.entry_user.delete(0, "end")
            self.login_window.entry_pass.delete(0, "end")
            self.login_window.lbl_error.configure(text="")
            self.login_window.entry_user.focus()


# ---------------------------------------------------------------------------
# Orden de módulos en el sidebar
# ---------------------------------------------------------------------------

_MODULE_ORDER = [
    "Pacientes",
    "Turnos",
    "Consultas",
    "Inventario",
    "Facturación",
    "Reportes",
    "Configuración",
]
