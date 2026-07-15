# =============================================================================
# VetSystem — modules/pacientes.py
# Service + View: Gestión de Tutores y Pacientes
# =============================================================================

from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from sqlalchemy.orm import Session

from app_core import FONTS, PALETTE
from app_shell import BaseTable
from models import Paciente, Tutor

# =============================================================================
# SERVICE — Funciones de acceso a datos y validaciones
# =============================================================================


def get_all_tutores(session: Session) -> list[Tutor]:
    return session.query(Tutor).order_by(Tutor.apellido, Tutor.nombre).all()


def get_tutor_by_id(session: Session, tutor_id: int) -> Optional[Tutor]:
    return session.get(Tutor, tutor_id)


def search_tutores(session: Session, term: str) -> list[Tutor]:
    t = f"%{term}%"
    return (
        session.query(Tutor)
        .filter(
            (Tutor.nombre.ilike(t))
            | (Tutor.apellido.ilike(t))
            | (Tutor.dni.ilike(t))
            | (Tutor.telefono.ilike(t))
        )
        .order_by(Tutor.apellido)
        .all()
    )


def save_tutor(session: Session, data: dict, tutor_id: Optional[int] = None) -> Tutor:
    if tutor_id:
        tutor = session.get(Tutor, tutor_id)
        if not tutor:
            raise ValueError("Tutor no encontrado.")
    else:
        tutor = Tutor()
        session.add(tutor)

    tutor.nombre = data["nombre"].strip()
    tutor.apellido = data["apellido"].strip()
    tutor.dni = data.get("dni", "").strip() or None
    tutor.telefono = data.get("telefono", "").strip() or None
    tutor.email = data.get("email", "").strip() or None
    tutor.direccion = data.get("direccion", "").strip() or None

    session.commit()
    session.refresh(tutor)
    return tutor


def delete_tutor(session: Session, tutor_id: int) -> None:
    tutor = session.get(Tutor, tutor_id)
    if tutor:
        session.delete(tutor)
        session.commit()


def get_pacientes_by_tutor(session: Session, tutor_id: int) -> list[Paciente]:
    return (
        session.query(Paciente)
        .filter(Paciente.tutor_id == tutor_id, Paciente.activo == True)
        .order_by(Paciente.nombre)
        .all()
    )


def get_paciente_by_id(session: Session, pac_id: int) -> Optional[Paciente]:
    return session.get(Paciente, pac_id)


def save_paciente(
    session: Session, data: dict, pac_id: Optional[int] = None
) -> Paciente:
    if pac_id:
        pac = session.get(Paciente, pac_id)
        if not pac:
            raise ValueError("Paciente no encontrado.")
    else:
        pac = Paciente()
        session.add(pac)

    pac.nombre = data["nombre"].strip()
    pac.especie = data["especie"].strip()
    pac.raza = data.get("raza", "").strip() or None
    pac.sexo = data.get("sexo", "").strip() or None
    pac.color = data.get("color", "").strip() or None
    pac.microchip = data.get("microchip", "").strip() or None
    pac.notas = data.get("notas", "").strip() or None
    pac.tutor_id = data["tutor_id"]

    session.commit()
    session.refresh(pac)
    return pac


def delete_paciente(session: Session, pac_id: int) -> None:
    pac = session.get(Paciente, pac_id)
    if pac:
        pac.activo = False
        session.commit()


# =============================================================================
# VIEW — PacientesFrame
# =============================================================================

# Nota: Se usan referencias directas a CTkEntry (.get() / .delete() / .insert())
# en lugar de tk.StringVar, ya que CTkEntry no sincroniza textvariable
# correctamente en todas las versiones de CustomTkinter.


class PacientesFrame(ctk.CTkFrame):
    """
    Módulo de gestión de Tutores y Pacientes.
    Layout: panel izquierdo (lista) + panel derecho (formulario).
    """

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly

        self._selected_tutor_id: Optional[int] = None
        self._selected_pac_id: Optional[int] = None
        self._mode: str = "tutor"  # "tutor" | "paciente"

        # Dicts de widgets CTkEntry — se usan con .get() / .delete() / .insert()
        self._tutor_entries: dict[str, ctk.CTkEntry] = {}
        self._pac_entries: dict[str, ctk.CTkEntry] = {}

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
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="🐾 Pacientes y Tutores",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent) -> None:
        left = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # ── Búsqueda de tutores ──────────────────────────────────────────
        ctk.CTkLabel(left, text="Tutores", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        search_f = ctk.CTkFrame(left, fg_color="transparent")
        search_f.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        search_f.grid_columnconfigure(0, weight=1)

        # Búsqueda usa trace en variable (no se usa para guardar, solo para filtrar)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        self.search_entry = ctk.CTkEntry(
            search_f,
            placeholder_text="🔍 Buscar tutor…",
            height=34, font=FONTS["body"],
            border_color=PALETTE["border"], fg_color="#FFFFFF",
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        # Bind manual para búsqueda en tiempo real
        self.search_entry.bind("<KeyRelease>", lambda _: self._on_search())

        # ── Tabla de tutores ─────────────────────────────────────────────
        self.tutor_table = BaseTable(
            left,
            columns=[
                {"id": "id",       "text": "ID",        "width": 40,  "stretch": False},
                {"id": "apellido", "text": "Apellido",   "width": 120},
                {"id": "nombre",   "text": "Nombre",     "width": 100},
                {"id": "telefono", "text": "Teléfono",   "width": 90},
            ],
            on_select=self._on_tutor_select,
            height=12,
        )
        self.tutor_table.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 6))

        # ── Pacientes del tutor ──────────────────────────────────────────
        ctk.CTkLabel(left, text="Pacientes del tutor", font=FONTS["small"],
                     text_color=PALETTE["text_muted"]).grid(
            row=3, column=0, padx=12, sticky="w")

        self.pac_table = BaseTable(
            left,
            columns=[
                {"id": "id",      "text": "ID",      "width": 40, "stretch": False},
                {"id": "nombre",  "text": "Nombre",  "width": 100},
                {"id": "especie", "text": "Especie", "width": 80},
                {"id": "raza",    "text": "Raza",    "width": 80},
            ],
            on_select=self._on_pac_select,
            height=6,
        )
        self.pac_table.grid(row=4, column=0, sticky="nsew", padx=12, pady=(2, 12))

        left.grid_rowconfigure(2, weight=2)
        left.grid_rowconfigure(4, weight=1)

    def _build_right_panel(self, parent) -> None:
        right = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)

        # ── Tabs Tutor / Paciente ─────────────────────────────────────────
        tab_f = ctk.CTkFrame(right, fg_color="transparent")
        tab_f.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 0))

        self.btn_tab_tutor = ctk.CTkButton(
            tab_f, text="Tutor", font=FONTS["body_bold"],
            fg_color=PALETTE["primary"], text_color="#FFF",
            height=32, corner_radius=6,
            command=lambda: self._switch_mode("tutor"),
        )
        self.btn_tab_tutor.pack(side="left", padx=(0, 4))

        self.btn_tab_pac = ctk.CTkButton(
            tab_f, text="Paciente", font=FONTS["body_bold"],
            fg_color=PALETTE["border"], text_color=PALETTE["text"],
            height=32, corner_radius=6,
            command=lambda: self._switch_mode("paciente"),
        )
        self.btn_tab_pac.pack(side="left")

        # ── Formulario Tutor ──────────────────────────────────────────────
        self.form_tutor = ctk.CTkFrame(right, fg_color="transparent")
        self.form_tutor.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=8)
        self.form_tutor.grid_columnconfigure(0, weight=1)
        self.form_tutor.grid_columnconfigure(1, weight=1)

        tutor_fields = [
            # (label,        key,          row, col)
            ("Nombre *",    "t_nombre",    0,   0),
            ("Apellido *",  "t_apellido",  0,   1),
            ("DNI",         "t_dni",       1,   0),
            ("Teléfono",    "t_telefono",  1,   1),
            ("Email",       "t_email",     2,   0),
            ("Dirección",   "t_direccion", 2,   1),
        ]
        for label, key, r, c in tutor_fields:
            ctk.CTkLabel(
                self.form_tutor, text=label,
                font=FONTS["body_bold"], text_color=PALETTE["text"],
            ).grid(row=r * 2, column=c, sticky="w", pady=(8, 2),
                   padx=(0, 8 if c == 0 else 0))
            entry = ctk.CTkEntry(
                self.form_tutor, height=36,
                font=FONTS["body"],
                border_color=PALETTE["border"],
                fg_color="#FFFFFF",
            )
            entry.grid(row=r * 2 + 1, column=c, sticky="ew",
                       padx=(0, 8 if c == 0 else 0))
            self._tutor_entries[key] = entry

        # ── Formulario Paciente ───────────────────────────────────────────
        self.form_pac = ctk.CTkFrame(right, fg_color="transparent")
        self.form_pac.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=8)
        self.form_pac.grid_columnconfigure(0, weight=1)
        self.form_pac.grid_columnconfigure(1, weight=1)
        self.form_pac.grid_remove()

        pac_fields = [
            ("Nombre *",  "p_nombre",   0, 0),
            ("Especie *", "p_especie",  0, 1),
            ("Raza",      "p_raza",     1, 0),
            ("Color",     "p_color",    1, 1),
            ("Microchip", "p_microchip",2, 0),
        ]
        for label, key, r, c in pac_fields:
            ctk.CTkLabel(
                self.form_pac, text=label,
                font=FONTS["body_bold"], text_color=PALETTE["text"],
            ).grid(row=r * 2, column=c, sticky="w", pady=(8, 2),
                   padx=(0, 8 if c == 0 else 0))
            entry = ctk.CTkEntry(
                self.form_pac, height=36,
                font=FONTS["body"],
                border_color=PALETTE["border"],
                fg_color="#FFFFFF",
            )
            entry.grid(row=r * 2 + 1, column=c, sticky="ew",
                       padx=(0, 8 if c == 0 else 0))
            self._pac_entries[key] = entry

        # Sexo (CTkComboBox — se lee con .get())
        ctk.CTkLabel(self.form_pac, text="Sexo", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(
            row=6, column=0, sticky="w", pady=(8, 2))
        self.sexo_combo = ctk.CTkComboBox(
            self.form_pac,
            values=["", "Macho", "Hembra", "Desconocido"],
            height=36, font=FONTS["body"],
            border_color=PALETTE["border"],
        )
        self.sexo_combo.set("")
        self.sexo_combo.grid(row=7, column=0, sticky="ew")

        # Notas paciente
        ctk.CTkLabel(self.form_pac, text="Notas", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(
            row=6, column=1, sticky="w", pady=(8, 2))
        self.pac_notas = ctk.CTkTextbox(
            self.form_pac, height=60,
            font=FONTS["body"],
            border_color=PALETTE["border"],
            fg_color="#FFFFFF",
        )
        self.pac_notas.grid(row=7, column=1, sticky="ew")

        # ── Botones de acción ─────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 16))

        btn_cfg = {"height": 38, "corner_radius": 8, "font": FONTS["body_bold"]}

        ctk.CTkButton(
            btn_frame, text="➕ Nuevo",
            fg_color=PALETTE["success"], hover_color="#1E8449", text_color="#FFF",
            command=self._new_record, **btn_cfg,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"], text_color="#FFF",
            command=self._save_record, **btn_cfg,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="🗑️ Eliminar",
            fg_color=PALETTE["danger"], hover_color=PALETTE["danger_dark"], text_color="#FFF",
            command=self._delete_record, **btn_cfg,
        ).pack(side="left")

        right.grid_rowconfigure(1, weight=1)

    # ── Helpers internos de entry ────────────────────────────────────────────

    def _entry_get(self, entries: dict, key: str) -> str:
        """Lee el texto de un CTkEntry directamente (sin StringVar)."""
        e = entries.get(key)
        return e.get() if e else ""

    def _entry_set(self, entries: dict, key: str, value: str) -> None:
        """Escribe un valor en un CTkEntry directamente."""
        e = entries.get(key)
        if e:
            e.delete(0, "end")
            e.insert(0, value)

    def _entry_clear(self, entries: dict) -> None:
        """Limpia todos los CTkEntry del dict."""
        for e in entries.values():
            e.delete(0, "end")

    # ── Lógica de navegación entre tabs ─────────────────────────────────────

    def _switch_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "tutor":
            self.form_tutor.grid()
            self.form_pac.grid_remove()
            self.btn_tab_tutor.configure(fg_color=PALETTE["primary"], text_color="#FFF")
            self.btn_tab_pac.configure(fg_color=PALETTE["border"], text_color=PALETTE["text"])
            self._clear_tutor_form()
            self._selected_tutor_id = None
        else:
            if not self._selected_tutor_id:
                CTkMessagebox(title="Aviso", message="Primero seleccioná un tutor.", icon="warning")
                return
            self.form_tutor.grid_remove()
            self.form_pac.grid()
            self.btn_tab_tutor.configure(fg_color=PALETTE["border"], text_color=PALETTE["text"])
            self.btn_tab_pac.configure(fg_color=PALETTE["primary"], text_color="#FFF")
            self._clear_pac_form()
            self._selected_pac_id = None

    # ── Callbacks de selección ───────────────────────────────────────────────

    def _on_tutor_select(self) -> None:
        vals = self.tutor_table.selected_values()
        if not vals:
            return
        tid = int(vals[0])
        self._selected_tutor_id = tid
        tutor = get_tutor_by_id(self.session, tid)
        if tutor:
            self._entry_set(self._tutor_entries, "t_nombre",    tutor.nombre)
            self._entry_set(self._tutor_entries, "t_apellido",  tutor.apellido)
            self._entry_set(self._tutor_entries, "t_dni",       tutor.dni or "")
            self._entry_set(self._tutor_entries, "t_telefono",  tutor.telefono or "")
            self._entry_set(self._tutor_entries, "t_email",     tutor.email or "")
            self._entry_set(self._tutor_entries, "t_direccion", tutor.direccion or "")
        self._load_pacientes(tid)

    def _on_pac_select(self) -> None:
        vals = self.pac_table.selected_values()
        if not vals:
            return
        pid = int(vals[0])
        self._selected_pac_id = pid
        pac = get_paciente_by_id(self.session, pid)
        if pac:
            self._entry_set(self._pac_entries, "p_nombre",    pac.nombre)
            self._entry_set(self._pac_entries, "p_especie",   pac.especie)
            self._entry_set(self._pac_entries, "p_raza",      pac.raza or "")
            self._entry_set(self._pac_entries, "p_color",     pac.color or "")
            self._entry_set(self._pac_entries, "p_microchip", pac.microchip or "")
            self.sexo_combo.set(pac.sexo or "")
            self.pac_notas.delete("0.0", "end")
            if pac.notas:
                self.pac_notas.insert("0.0", pac.notas)
            self._switch_mode("paciente")

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def _new_record(self) -> None:
        if self._mode == "tutor":
            self._clear_tutor_form()
            self._selected_tutor_id = None
        else:
            self._clear_pac_form()
            self._selected_pac_id = None

    def _save_record(self) -> None:
        try:
            if self._mode == "tutor":
                # Leer directamente de los widgets CTkEntry
                nombre   = self._entry_get(self._tutor_entries, "t_nombre").strip()
                apellido = self._entry_get(self._tutor_entries, "t_apellido").strip()

                if not nombre or not apellido:
                    CTkMessagebox(
                        title="Error",
                        message="Nombre y Apellido son obligatorios.",
                        icon="cancel",
                    )
                    return

                data = {
                    "nombre":    nombre,
                    "apellido":  apellido,
                    "dni":       self._entry_get(self._tutor_entries, "t_dni"),
                    "telefono":  self._entry_get(self._tutor_entries, "t_telefono"),
                    "email":     self._entry_get(self._tutor_entries, "t_email"),
                    "direccion": self._entry_get(self._tutor_entries, "t_direccion"),
                }
                save_tutor(self.session, data, self._selected_tutor_id)
                CTkMessagebox(title="Éxito", message="Tutor guardado correctamente.", icon="check")
                self.refresh()

            else:  # modo paciente
                if not self._selected_tutor_id:
                    CTkMessagebox(title="Error", message="Seleccioná un tutor primero.", icon="cancel")
                    return

                nombre  = self._entry_get(self._pac_entries, "p_nombre").strip()
                especie = self._entry_get(self._pac_entries, "p_especie").strip()

                if not nombre or not especie:
                    CTkMessagebox(
                        title="Error",
                        message="Nombre y Especie son obligatorios.",
                        icon="cancel",
                    )
                    return

                data = {
                    "nombre":    nombre,
                    "especie":   especie,
                    "raza":      self._entry_get(self._pac_entries, "p_raza"),
                    "color":     self._entry_get(self._pac_entries, "p_color"),
                    "microchip": self._entry_get(self._pac_entries, "p_microchip"),
                    "sexo":      self.sexo_combo.get(),
                    "notas":     self.pac_notas.get("0.0", "end").strip(),
                    "tutor_id":  self._selected_tutor_id,
                }
                save_paciente(self.session, data, self._selected_pac_id)
                CTkMessagebox(title="Éxito", message="Paciente guardado correctamente.", icon="check")
                self._load_pacientes(self._selected_tutor_id)

        except Exception as exc:
            self.session.rollback()
            CTkMessagebox(title="Error al guardar", message=str(exc), icon="cancel")

    def _delete_record(self) -> None:
        if self._mode == "tutor":
            if not self._selected_tutor_id:
                return
            msg = CTkMessagebox(
                title="Eliminar",
                message="¿Eliminar este tutor y TODOS sus pacientes?",
                icon="warning",
                option_1="Cancelar",
                option_2="Eliminar",
            )
            if msg.get() == "Eliminar":
                delete_tutor(self.session, self._selected_tutor_id)
                self._selected_tutor_id = None
                self._clear_tutor_form()
                self.refresh()
        else:
            if not self._selected_pac_id:
                return
            msg = CTkMessagebox(
                title="Eliminar",
                message="¿Marcar este paciente como inactivo?",
                icon="warning",
                option_1="Cancelar",
                option_2="Eliminar",
            )
            if msg.get() == "Eliminar":
                delete_paciente(self.session, self._selected_pac_id)
                self._selected_pac_id = None
                self._clear_pac_form()
                self._load_pacientes(self._selected_tutor_id)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _on_search(self) -> None:
        term = self.search_entry.get().strip()
        if term:
            tutores = search_tutores(self.session, term)
        else:
            tutores = get_all_tutores(self.session)
        self._populate_tutores(tutores)

    def _load_pacientes(self, tutor_id: int) -> None:
        pacs = get_pacientes_by_tutor(self.session, tutor_id)
        self.pac_table.populate([
            (p.id, p.nombre, p.especie, p.raza or "")
            for p in pacs
        ])

    def _populate_tutores(self, tutores: list[Tutor]) -> None:
        self.tutor_table.populate([
            (t.id, t.apellido, t.nombre, t.telefono or "")
            for t in tutores
        ])

    def _clear_tutor_form(self) -> None:
        self._entry_clear(self._tutor_entries)

    def _clear_pac_form(self) -> None:
        self._entry_clear(self._pac_entries)
        self.sexo_combo.set("")
        self.pac_notas.delete("0.0", "end")

    def refresh(self) -> None:
        self.session.expire_all()
        tutores = get_all_tutores(self.session)
        self._populate_tutores(tutores)
        self.pac_table.clear()
