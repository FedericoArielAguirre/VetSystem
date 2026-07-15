# =============================================================================
# VetSystem — modules/configuracion.py
# Service + View: Gestión de Usuarios y Configuración del Sistema
# =============================================================================

from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from sqlalchemy.orm import Session

from app_core import FONTS, PALETTE, hash_password
from app_shell import BaseTable
from models import Rol, Usuario

# =============================================================================
# SERVICE
# =============================================================================


def get_all_usuarios(session: Session) -> list[Usuario]:
    return session.query(Usuario).order_by(Usuario.nombre_completo).all()


def get_all_roles(session: Session) -> list[Rol]:
    return session.query(Rol).order_by(Rol.nombre).all()


def get_usuario_by_id(session: Session, uid: int) -> Optional[Usuario]:
    return session.get(Usuario, uid)


def save_usuario(
    session: Session, data: dict, uid: Optional[int] = None
) -> Usuario:
    if uid:
        user = session.get(Usuario, uid)
        if not user:
            raise ValueError("Usuario no encontrado.")
    else:
        user = Usuario()
        session.add(user)

    user.username = data["username"].strip()
    user.nombre_completo = data["nombre_completo"].strip()
    user.email = data.get("email", "").strip() or None
    user.rol_id = int(data["rol_id"])
    user.activo = data.get("activo", True)

    if data.get("password"):
        user.password_hash = hash_password(data["password"].strip())

    session.commit()
    session.refresh(user)
    return user


def delete_usuario(session: Session, uid: int) -> None:
    user = session.get(Usuario, uid)
    if user:
        user.activo = False
        session.commit()


# =============================================================================
# VIEW — ConfiguracionFrame
# =============================================================================


class ConfiguracionFrame(ctk.CTkFrame):
    """Módulo de configuración: gestión de usuarios del sistema."""

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.current_user = user
        self.readonly = readonly
        self._selected_uid: Optional[int] = None
        self._rol_map: dict[str, int] = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self.refresh()

    # ── Header ──────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=PALETTE["bg_card"], corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)

        ctk.CTkLabel(hdr, text="⚙️ Configuración — Usuarios",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        self._build_list(body)
        self._build_form(body)

    def _build_list(self, parent) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Usuarios del Sistema", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        self.table = BaseTable(
            frame,
            columns=[
                {"id": "id",       "text": "ID",      "width": 40,  "stretch": False},
                {"id": "username", "text": "Usuario",  "width": 120},
                {"id": "nombre",   "text": "Nombre",   "width": 160},
                {"id": "rol",      "text": "Rol",      "width": 100},
                {"id": "activo",   "text": "Activo",   "width": 60, "anchor": "center"},
            ],
            on_select=self._on_select,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_form(self, parent) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Datos del Usuario", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        fields = [
            ("Nombre de Usuario *", "username"),
            ("Nombre Completo *",   "nombre_completo"),
            ("Email",               "email"),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        row = 1
        for label, key in fields:
            ctk.CTkLabel(frame, text=label, font=FONTS["body_bold"],
                         text_color=PALETTE["text"]).grid(row=row, column=0, padx=12, sticky="w", pady=(8, 2))
            var = tk.StringVar()
            self._vars[key] = var
            ctk.CTkEntry(frame, textvariable=var, height=36, font=FONTS["body"],
                         border_color=PALETTE["border"], fg_color="#FFFFFF").grid(
                row=row+1, column=0, sticky="ew", padx=12, pady=(0, 2))
            row += 2

        # Contraseña
        ctk.CTkLabel(frame, text="Contraseña (dejar vacío para no cambiar)",
                     font=FONTS["body_bold"], text_color=PALETTE["text"]).grid(
            row=row, column=0, padx=12, sticky="w", pady=(8, 2))
        self.pass_var = tk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.pass_var, show="•", height=36,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").grid(row=row+1, column=0, sticky="ew", padx=12)
        row += 2

        # Rol
        ctk.CTkLabel(frame, text="Rol *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=row, column=0, padx=12, sticky="w", pady=(8, 2))
        self.rol_var = tk.StringVar()
        self.rol_combo = ctk.CTkComboBox(frame, variable=self.rol_var, values=[],
                                          height=36, font=FONTS["body"],
                                          border_color=PALETTE["border"])
        self.rol_combo.grid(row=row+1, column=0, sticky="ew", padx=12, pady=(0, 2))
        row += 2

        # Activo
        self.activo_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Usuario activo", variable=self.activo_var,
                        font=FONTS["body"], text_color=PALETTE["text"],
                        fg_color=PALETTE["primary"], checkmark_color="#FFFFFF").grid(
            row=row, column=0, padx=12, pady=(12, 4), sticky="w")
        row += 1

        # Botones
        btn_f = ctk.CTkFrame(frame, fg_color="transparent")
        btn_f.grid(row=row, column=0, sticky="ew", padx=12, pady=(8, 16))
        btn_cfg = {"height": 38, "corner_radius": 8, "font": FONTS["body_bold"]}

        ctk.CTkButton(btn_f, text="➕ Nuevo", fg_color=PALETTE["success"],
                      hover_color="#1E8449", text_color="#FFF",
                      command=self._new, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="💾 Guardar", fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"], text_color="#FFF",
                      command=self._save, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="🔒 Desactivar", fg_color=PALETTE["danger"],
                      hover_color=PALETTE["danger_dark"], text_color="#FFF",
                      command=self._delete, **btn_cfg).pack(side="left")

        frame.grid_rowconfigure(row + 1, weight=1)

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_select(self) -> None:
        vals = self.table.selected_values()
        if not vals:
            return
        uid = int(vals[0])
        self._selected_uid = uid
        user = get_usuario_by_id(self.session, uid)
        if not user:
            return
        self._vars["username"].set(user.username)
        self._vars["nombre_completo"].set(user.nombre_completo)
        self._vars["email"].set(user.email or "")
        self.pass_var.set("")
        rol_key = next((k for k, v in self._rol_map.items() if v == user.rol_id), "")
        self.rol_var.set(rol_key)
        self.activo_var.set(user.activo)

    def _new(self) -> None:
        self._selected_uid = None
        for var in self._vars.values():
            var.set("")
        self.pass_var.set("")
        self.rol_var.set("")
        self.activo_var.set(True)

    def _save(self) -> None:
        username = self._vars["username"].get().strip()
        nombre = self._vars["nombre_completo"].get().strip()
        if not username or not nombre:
            CTkMessagebox(title="Error", message="Usuario y Nombre son obligatorios.", icon="cancel")
            return
        rol_key = self.rol_var.get()
        if not rol_key or rol_key not in self._rol_map:
            CTkMessagebox(title="Error", message="Seleccioná un rol válido.", icon="cancel")
            return

        data = {
            "username":       username,
            "nombre_completo": nombre,
            "email":          self._vars["email"].get(),
            "rol_id":         self._rol_map[rol_key],
            "activo":         self.activo_var.get(),
            "password":       self.pass_var.get(),
        }

        if not self._selected_uid and not data["password"]:
            CTkMessagebox(title="Error", message="La contraseña es obligatoria para nuevos usuarios.", icon="cancel")
            return

        try:
            save_usuario(self.session, data, self._selected_uid)
            CTkMessagebox(title="Éxito", message="Usuario guardado.", icon="check")
            self.refresh()
        except Exception as exc:
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    def _delete(self) -> None:
        if not self._selected_uid:
            return
        if self._selected_uid == self.current_user.id:
            CTkMessagebox(title="Error", message="No podés desactivar tu propio usuario.", icon="cancel")
            return
        msg = CTkMessagebox(title="Desactivar", message="¿Desactivar este usuario?",
                             icon="warning", option_1="Cancelar", option_2="Desactivar")
        if msg.get() == "Desactivar":
            delete_usuario(self.session, self._selected_uid)
            self._selected_uid = None
            self.refresh()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self.session.expire_all()
        roles = get_all_roles(self.session)
        self._rol_map = {r.nombre.capitalize(): r.id for r in roles}
        self.rol_combo.configure(values=list(self._rol_map.keys()))

        usuarios = get_all_usuarios(self.session)
        self.table.populate([
            (
                u.id,
                u.username,
                u.nombre_completo,
                u.rol.nombre.capitalize() if u.rol else "",
                "✅" if u.activo else "❌",
            )
            for u in usuarios
        ])
