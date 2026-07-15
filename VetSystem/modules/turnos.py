# =============================================================================
# VetSystem — modules/turnos.py
# Service + View: Agenda / Turnos
# =============================================================================

from __future__ import annotations

import datetime
import tkinter as tk
from typing import Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from sqlalchemy.orm import Session

from app_core import FONTS, PALETTE
from app_shell import BaseTable
from models import Paciente, Tutor, Turno, Usuario

# =============================================================================
# SERVICE
# =============================================================================

ESTADOS = ["Pendiente", "Completado", "Cancelado"]


def get_turnos_by_fecha(session: Session, fecha: datetime.date) -> list[Turno]:
    inicio = datetime.datetime.combine(fecha, datetime.time.min)
    fin = datetime.datetime.combine(fecha, datetime.time.max)
    return (
        session.query(Turno)
        .filter(Turno.fecha_hora >= inicio, Turno.fecha_hora <= fin)
        .order_by(Turno.fecha_hora)
        .all()
    )


def get_all_turnos(session: Session, days_ahead: int = 7) -> list[Turno]:
    desde = datetime.datetime.now() - datetime.timedelta(days=1)
    hasta = datetime.datetime.now() + datetime.timedelta(days=days_ahead)
    return (
        session.query(Turno)
        .filter(Turno.fecha_hora >= desde, Turno.fecha_hora <= hasta)
        .order_by(Turno.fecha_hora)
        .all()
    )


def get_turno_by_id(session: Session, turno_id: int) -> Optional[Turno]:
    return session.get(Turno, turno_id)


def get_all_pacientes(session: Session) -> list[Paciente]:
    return (
        session.query(Paciente)
        .filter(Paciente.activo == True)
        .order_by(Paciente.nombre)
        .all()
    )


def get_all_veterinarios(session: Session) -> list[Usuario]:
    return (
        session.query(Usuario)
        .join(Usuario.rol)
        .filter(Usuario.activo == True)
        .order_by(Usuario.nombre_completo)
        .all()
    )


def save_turno(session: Session, data: dict, turno_id: Optional[int] = None) -> Turno:
    if turno_id:
        turno = session.get(Turno, turno_id)
        if not turno:
            raise ValueError("Turno no encontrado.")
    else:
        turno = Turno()
        session.add(turno)

    turno.fecha_hora = data["fecha_hora"]
    turno.motivo = data.get("motivo", "").strip() or None
    turno.estado = data.get("estado", "Pendiente")
    turno.notas = data.get("notas", "").strip() or None
    turno.duracion_min = int(data.get("duracion_min", 30))
    turno.paciente_id = int(data["paciente_id"])
    turno.veterinario_id = int(data["veterinario_id"])

    session.commit()
    session.refresh(turno)
    return turno


def delete_turno(session: Session, turno_id: int) -> None:
    turno = session.get(Turno, turno_id)
    if turno:
        session.delete(turno)
        session.commit()


def change_estado(session: Session, turno_id: int, estado: str) -> None:
    turno = session.get(Turno, turno_id)
    if turno:
        turno.estado = estado
        session.commit()


# =============================================================================
# VIEW — TurnosFrame
# =============================================================================


class TurnosFrame(ctk.CTkFrame):
    """Módulo de agenda / turnos."""

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly
        self._selected_id: Optional[int] = None

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
        hdr.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(hdr, text="📅 Agenda / Turnos",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

        # Filtro por fecha
        ctk.CTkLabel(hdr, text="Fecha:", font=FONTS["body"],
                     text_color=PALETTE["text"]).grid(row=0, column=1, padx=(20, 4))
        self.fecha_entry = ctk.CTkEntry(hdr, width=120, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF")
        self.fecha_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.fecha_entry.grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(hdr, text="🔍 Filtrar", height=34, width=90,
                      font=FONTS["body"], fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"],
                      command=self._filter_by_date).grid(row=0, column=3, padx=(0, 8), sticky="w")

        ctk.CTkButton(hdr, text="Todos (7d)", height=34, width=90,
                      font=FONTS["body"], fg_color=PALETTE["border"],
                      text_color=PALETTE["text"],
                      command=self.refresh).grid(row=0, column=4, padx=(0, 20))

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

        ctk.CTkLabel(frame, text="Turnos", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        self.table = BaseTable(
            frame,
            columns=[
                {"id": "id",       "text": "ID",      "width": 40,  "stretch": False},
                {"id": "fecha",    "text": "Fecha/Hora","width": 130},
                {"id": "paciente", "text": "Paciente", "width": 110},
                {"id": "vet",      "text": "Veterinario","width": 110},
                {"id": "motivo",   "text": "Motivo",   "width": 130},
                {"id": "estado",   "text": "Estado",   "width": 90},
            ],
            on_select=self._on_select,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_form(self, parent) -> None:
        self.form_frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        self.form_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        self.form_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.form_frame, text="Detalle del Turno", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        # Paciente
        ctk.CTkLabel(self.form_frame, text="Paciente *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=1, column=0, padx=12, sticky="w")
        self.pac_combo = ctk.CTkComboBox(self.form_frame,
                                          values=[], height=36, font=FONTS["body"],
                                          border_color=PALETTE["border"])
        self.pac_combo.set("")
        self.pac_combo.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Veterinario
        ctk.CTkLabel(self.form_frame, text="Veterinario *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=3, column=0, padx=12, sticky="w")
        self.vet_combo = ctk.CTkComboBox(self.form_frame,
                                          values=[], height=36, font=FONTS["body"],
                                          border_color=PALETTE["border"])
        self.vet_combo.set("")
        self.vet_combo.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Fecha y hora
        ctk.CTkLabel(self.form_frame, text="Fecha y Hora (YYYY-MM-DD HH:MM) *",
                     font=FONTS["body_bold"], text_color=PALETTE["text"]).grid(
            row=5, column=0, padx=12, sticky="w")
        self.fh_entry = ctk.CTkEntry(self.form_frame, height=36,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF")
        self.fh_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.fh_entry.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Duración
        ctk.CTkLabel(self.form_frame, text="Duración (min)", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=7, column=0, padx=12, sticky="w")
        self.dur_entry = ctk.CTkEntry(self.form_frame, height=36,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF")
        self.dur_entry.insert(0, "30")
        self.dur_entry.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Motivo
        ctk.CTkLabel(self.form_frame, text="Motivo", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=9, column=0, padx=12, sticky="w")
        self.motivo_entry = ctk.CTkEntry(self.form_frame, height=36,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF")
        self.motivo_entry.grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Estado
        ctk.CTkLabel(self.form_frame, text="Estado", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=11, column=0, padx=12, sticky="w")
        self.estado_combo = ctk.CTkComboBox(self.form_frame,
                        values=ESTADOS, height=36, font=FONTS["body"],
                        border_color=PALETTE["border"])
        self.estado_combo.set("Pendiente")
        self.estado_combo.grid(row=12, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Notas
        ctk.CTkLabel(self.form_frame, text="Notas", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=13, column=0, padx=12, sticky="w")
        self.notas_box = ctk.CTkTextbox(self.form_frame, height=70,
                                         font=FONTS["body"], border_color=PALETTE["border"],
                                         fg_color="#FFFFFF")
        self.notas_box.grid(row=14, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Botones
        btn_f = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        btn_f.grid(row=15, column=0, sticky="ew", padx=12, pady=(4, 16))
        btn_cfg = {"height": 38, "corner_radius": 8, "font": FONTS["body_bold"]}

        ctk.CTkButton(btn_f, text="➕ Nuevo", fg_color=PALETTE["success"],
                      hover_color="#1E8449", text_color="#FFF",
                      command=self._new, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="💾 Guardar", fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"], text_color="#FFF",
                      command=self._save, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="🗑️ Eliminar", fg_color=PALETTE["danger"],
                      hover_color=PALETTE["danger_dark"], text_color="#FFF",
                      command=self._delete, **btn_cfg).pack(side="left")

        self.form_frame.grid_rowconfigure(16, weight=1)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _refresh_combos(self) -> None:
        pacs = get_all_pacientes(self.session)
        self._pac_map = {f"{p.nombre} (#{p.id})": p.id for p in pacs}
        self.pac_combo.configure(values=list(self._pac_map.keys()))

        vets = get_all_veterinarios(self.session)
        self._vet_map = {f"{v.nombre_completo}": v.id for v in vets}
        self.vet_combo.configure(values=list(self._vet_map.keys()))

    def _on_select(self) -> None:
        vals = self.table.selected_values()
        if not vals:
            return
        tid = int(vals[0])
        self._selected_id = tid
        turno = get_turno_by_id(self.session, tid)
        if not turno:
            return

        # Buscar en combos
        pac_key = next((k for k, v in self._pac_map.items() if v == turno.paciente_id), "")
        vet_key = next((k for k, v in self._vet_map.items() if v == turno.veterinario_id), "")
        self.pac_combo.set(pac_key)
        self.vet_combo.set(vet_key)
        self.fh_entry.delete(0, "end")
        self.fh_entry.insert(0, turno.fecha_hora.strftime("%Y-%m-%d %H:%M"))
        self.dur_entry.delete(0, "end")
        self.dur_entry.insert(0, str(turno.duracion_min))
        self.motivo_entry.delete(0, "end")
        self.motivo_entry.insert(0, turno.motivo or "")
        self.estado_combo.set(turno.estado)
        self.notas_box.delete("0.0", "end")
        if turno.notas:
            self.notas_box.insert("0.0", turno.notas)

    def _new(self) -> None:
        self._selected_id = None
        self.pac_combo.set("")
        self.vet_combo.set("")
        self.fh_entry.delete(0, "end")
        self.fh_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.dur_entry.delete(0, "end")
        self.dur_entry.insert(0, "30")
        self.motivo_entry.delete(0, "end")
        self.estado_combo.set("Pendiente")
        self.notas_box.delete("0.0", "end")

    def _save(self) -> None:
        try:
            pac_key = self.pac_combo.get()
            vet_key = self.vet_combo.get()
            if not pac_key or pac_key not in self._pac_map:
                CTkMessagebox(title="Error", message="Selecciona un paciente valido.", icon="cancel")
                return
            if not vet_key or vet_key not in self._vet_map:
                CTkMessagebox(title="Error", message="Selecciona un veterinario valido.", icon="cancel")
                return

            fh = datetime.datetime.strptime(self.fh_entry.get().strip(), "%Y-%m-%d %H:%M")
            data = {
                "paciente_id":    self._pac_map[pac_key],
                "veterinario_id": self._vet_map[vet_key],
                "fecha_hora":     fh,
                "duracion_min":   self.dur_entry.get() or 30,
                "motivo":         self.motivo_entry.get(),
                "estado":         self.estado_combo.get(),
                "notas":          self.notas_box.get("0.0", "end").strip(),
            }
            save_turno(self.session, data, self._selected_id)
            CTkMessagebox(title="Exito", message="Turno guardado.", icon="check")
            self.refresh()
        except ValueError as exc:
            CTkMessagebox(title="Error", message=f"Fecha invalida: {exc}", icon="cancel")
        except Exception as exc:
            self.session.rollback()
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    def _delete(self) -> None:
        if not self._selected_id:
            return
        msg = CTkMessagebox(title="Eliminar", message="¿Eliminar este turno?",
                             icon="warning", option_1="Cancelar", option_2="Eliminar")
        if msg.get() == "Eliminar":
            delete_turno(self.session, self._selected_id)
            self._selected_id = None
            self.refresh()

    def _filter_by_date(self) -> None:
        try:
            fecha = datetime.datetime.strptime(self.fecha_entry.get().strip(), "%Y-%m-%d").date()
            turnos = get_turnos_by_fecha(self.session, fecha)
            self._populate(turnos)
        except ValueError:
            CTkMessagebox(title="Error", message="Formato de fecha invalido (YYYY-MM-DD).", icon="cancel")

    def _populate(self, turnos: list[Turno]) -> None:
        self.table.populate([
            (
                t.id,
                t.fecha_hora.strftime("%Y-%m-%d %H:%M"),
                t.paciente.nombre if t.paciente else "",
                t.veterinario.nombre_completo if t.veterinario else "",
                t.motivo or "",
                t.estado,
            )
            for t in turnos
        ])

    def refresh(self) -> None:
        self.session.expire_all()
        self._refresh_combos()
        turnos = get_all_turnos(self.session)
        self._populate(turnos)
