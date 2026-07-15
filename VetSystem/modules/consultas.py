# =============================================================================
# VetSystem — modules/consultas.py
# Service + View: Consultas Clínicas y Maniobras
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
from models import Consulta, ConsultaManiobra, Maniobra, Paciente, Usuario

# =============================================================================
# SERVICE
# =============================================================================


def get_all_pacientes_activos(session: Session) -> list[Paciente]:
    return (
        session.query(Paciente)
        .filter(Paciente.activo == True)
        .order_by(Paciente.nombre)
        .all()
    )


def get_consultas_by_paciente(session: Session, pac_id: int) -> list[Consulta]:
    return (
        session.query(Consulta)
        .filter(Consulta.paciente_id == pac_id)
        .order_by(Consulta.fecha.desc())
        .all()
    )


def get_consulta_by_id(session: Session, cid: int) -> Optional[Consulta]:
    return session.get(Consulta, cid)


def get_all_veterinarios(session: Session) -> list[Usuario]:
    return (
        session.query(Usuario)
        .filter(Usuario.activo == True)
        .order_by(Usuario.nombre_completo)
        .all()
    )


def get_all_maniobras(session: Session) -> list[Maniobra]:
    return (
        session.query(Maniobra)
        .filter(Maniobra.activo == True)
        .order_by(Maniobra.nombre)
        .all()
    )


def save_consulta(
    session: Session,
    data: dict,
    maniobras_ids: list[int],
    consulta_id: Optional[int] = None,
) -> Consulta:
    if consulta_id:
        c = session.get(Consulta, consulta_id)
        if not c:
            raise ValueError("Consulta no encontrada.")
    else:
        c = Consulta()
        session.add(c)

    c.fecha = data["fecha"]
    c.motivo = data.get("motivo", "").strip() or None
    c.anamnesis = data.get("anamnesis", "").strip() or None
    c.examen_fisico = data.get("examen_fisico", "").strip() or None
    c.diagnostico = data.get("diagnostico", "").strip() or None
    c.tratamiento = data.get("tratamiento", "").strip() or None
    c.observaciones = data.get("observaciones", "").strip() or None
    c.peso_kg = float(data["peso_kg"]) if data.get("peso_kg") else None
    c.temperatura = float(data["temperatura"]) if data.get("temperatura") else None
    c.paciente_id = int(data["paciente_id"])
    c.veterinario_id = int(data["veterinario_id"])

    # Limpiar maniobras anteriores
    for link in list(c.maniobras_link):
        session.delete(link)
    session.flush()

    # Agregar nuevas maniobras
    for mid in maniobras_ids:
        maniobra = session.get(Maniobra, mid)
        if maniobra:
            link = ConsultaManiobra(
                consulta=c,
                maniobra_id=mid,
                precio_aplicado=maniobra.precio,
            )
            session.add(link)

    session.commit()
    session.refresh(c)
    return c


def delete_consulta(session: Session, cid: int) -> None:
    c = session.get(Consulta, cid)
    if c:
        session.delete(c)
        session.commit()


def save_maniobra(session: Session, data: dict, mid: Optional[int] = None) -> Maniobra:
    if mid:
        m = session.get(Maniobra, mid)
        if not m:
            raise ValueError("Maniobra no encontrada.")
    else:
        m = Maniobra()
        session.add(m)

    m.nombre = data["nombre"].strip()
    m.descripcion = data.get("descripcion", "").strip() or None
    m.precio = float(data.get("precio", 0) or 0)
    session.commit()
    session.refresh(m)
    return m


# =============================================================================
# VIEW — ConsultasFrame
# =============================================================================


class ConsultasFrame(ctk.CTkFrame):
    """Módulo de consultas clínicas y maniobras."""

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly
        self._selected_pac_id: Optional[int] = None
        self._selected_consulta_id: Optional[int] = None
        self._pac_map: dict[str, int] = {}
        self._vet_map: dict[str, int] = {}
        self._maniobras_all: list[Maniobra] = []
        self._maniobra_checks: dict[int, tk.BooleanVar] = {}

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

        ctk.CTkLabel(hdr, text="🩺 Consultas Clínicas",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=2)

        self._build_left(body)
        self._build_center(body)
        self._build_right(body)

    def _build_left(self, parent) -> None:
        """Panel izquierdo: selector de paciente + historial de consultas."""
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(12, 4), pady=12)
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Paciente", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        self.pac_var = tk.StringVar()
        self.pac_combo = ctk.CTkComboBox(
            frame, variable=self.pac_var, values=[],
            height=36, font=FONTS["body"], border_color=PALETTE["border"],
            command=lambda _: self._on_pac_change(),
        )
        self.pac_combo.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        ctk.CTkLabel(frame, text="Historial", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=2, column=0, padx=12, sticky="w")

        self.hist_table = BaseTable(
            frame,
            columns=[
                {"id": "id",    "text": "ID",    "width": 40,  "stretch": False},
                {"id": "fecha", "text": "Fecha", "width": 110},
                {"id": "motivo","text": "Motivo","width": 120},
            ],
            on_select=self._on_consulta_select,
            height=20,
        )
        self.hist_table.grid(row=3, column=0, sticky="nsew", padx=12, pady=(2, 12))

    def _build_center(self, parent) -> None:
        """Panel central: formulario de consulta."""
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=12)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Datos de Consulta", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        labels_vars = [
            ("Fecha (YYYY-MM-DD HH:MM) *", "fecha"),
            ("Motivo", "motivo"),
            ("Peso (kg)", "peso"),
            ("Temperatura (°C)", "temp"),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        row = 1
        for label, key in labels_vars:
            ctk.CTkLabel(frame, text=label, font=FONTS["body_bold"],
                         text_color=PALETTE["text"]).grid(row=row, column=0, padx=12, sticky="w", pady=(6, 2))
            var = tk.StringVar()
            self._vars[key] = var
            ctk.CTkEntry(frame, textvariable=var, height=36, font=FONTS["body"],
                         border_color=PALETTE["border"], fg_color="#FFFFFF").grid(
                row=row+1, column=0, sticky="ew", padx=12, pady=(0, 2))
            row += 2

        # Veterinario
        ctk.CTkLabel(frame, text="Veterinario *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=row, column=0, padx=12, sticky="w", pady=(6, 2))
        self.vet_var = tk.StringVar()
        self.vet_combo = ctk.CTkComboBox(frame, variable=self.vet_var, values=[],
                                          height=36, font=FONTS["body"],
                                          border_color=PALETTE["border"])
        self.vet_combo.grid(row=row+1, column=0, sticky="ew", padx=12, pady=(0, 4))
        row += 2

        # TextBoxes clínicos
        clinical_fields = [
            ("Anamnesis", "anamnesis"),
            ("Examen Físico", "examen_fisico"),
            ("Diagnóstico", "diagnostico"),
            ("Tratamiento", "tratamiento"),
            ("Observaciones", "observaciones"),
        ]
        self._text_widgets: dict[str, ctk.CTkTextbox] = {}
        for label, key in clinical_fields:
            ctk.CTkLabel(frame, text=label, font=FONTS["body_bold"],
                         text_color=PALETTE["text"]).grid(row=row, column=0, padx=12, sticky="w", pady=(6, 2))
            tb = ctk.CTkTextbox(frame, height=55, font=FONTS["body"],
                                border_color=PALETTE["border"], fg_color="#FFFFFF")
            tb.grid(row=row+1, column=0, sticky="ew", padx=12, pady=(0, 2))
            self._text_widgets[key] = tb
            row += 2

        # Botones
        btn_f = ctk.CTkFrame(frame, fg_color="transparent")
        btn_f.grid(row=row, column=0, sticky="ew", padx=12, pady=(8, 16))
        btn_cfg = {"height": 38, "corner_radius": 8, "font": FONTS["body_bold"]}

        ctk.CTkButton(btn_f, text="➕ Nueva", fg_color=PALETTE["success"],
                      hover_color="#1E8449", text_color="#FFF",
                      command=self._new, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="💾 Guardar", fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"], text_color="#FFF",
                      command=self._save, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="🗑️ Eliminar", fg_color=PALETTE["danger"],
                      hover_color=PALETTE["danger_dark"], text_color="#FFF",
                      command=self._delete, **btn_cfg).pack(side="left")

        frame.grid_rowconfigure(row - 1, weight=1)

    def _build_right(self, parent) -> None:
        """Panel derecho: checklist de maniobras."""
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=2, sticky="nsew", padx=(4, 12), pady=12)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Maniobras Realizadas", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        # Scroll frame para los checkboxes
        self.maniobras_scroll = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", label_text=""
        )
        self.maniobras_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        frame.grid_rowconfigure(1, weight=1)

        # Gestión de maniobras
        sep = ctk.CTkFrame(frame, height=1, fg_color=PALETTE["border"])
        sep.grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        ctk.CTkLabel(frame, text="Nueva Maniobra", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=3, column=0, padx=12, pady=(8, 4), sticky="w")

        ctk.CTkLabel(frame, text="Nombre *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=4, column=0, padx=12, sticky="w")
        self.new_man_nombre = ctk.CTkEntry(frame, height=34, font=FONTS["body"],
                                            border_color=PALETTE["border"], fg_color="#FFFFFF")
        self.new_man_nombre.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 4))

        ctk.CTkLabel(frame, text="Precio", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=6, column=0, padx=12, sticky="w")
        self.new_man_precio = ctk.CTkEntry(frame, height=34, font=FONTS["body"],
                                            border_color=PALETTE["border"], fg_color="#FFFFFF")
        self.new_man_precio.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 8))

        ctk.CTkButton(frame, text="➕ Agregar Maniobra",
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"],
                      text_color="#FFF", height=36, corner_radius=8, font=FONTS["body_bold"],
                      command=self._add_maniobra).grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 12))

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_pac_change(self) -> None:
        key = self.pac_var.get()
        if key in self._pac_map:
            self._selected_pac_id = self._pac_map[key]
            self._load_historial()
        self._new()

    def _on_consulta_select(self) -> None:
        vals = self.hist_table.selected_values()
        if not vals:
            return
        cid = int(vals[0])
        self._selected_consulta_id = cid
        c = get_consulta_by_id(self.session, cid)
        if not c:
            return

        self._vars["fecha"].set(c.fecha.strftime("%Y-%m-%d %H:%M"))
        self._vars["motivo"].set(c.motivo or "")
        self._vars["peso"].set(str(c.peso_kg) if c.peso_kg else "")
        self._vars["temp"].set(str(c.temperatura) if c.temperatura else "")

        vet_key = next((k for k, v in self._vet_map.items() if v == c.veterinario_id), "")
        self.vet_var.set(vet_key)

        for key, tb in self._text_widgets.items():
            tb.delete("0.0", "end")
            val = getattr(c, key, None)
            if val:
                tb.insert("0.0", val)

        # Maniobras seleccionadas
        applied_ids = {link.maniobra_id for link in c.maniobras_link}
        for mid, var in self._maniobra_checks.items():
            var.set(mid in applied_ids)

    def _new(self) -> None:
        self._selected_consulta_id = None
        self._vars["fecha"].set(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        for key in ("motivo", "peso", "temp"):
            self._vars[key].set("")
        for tb in self._text_widgets.values():
            tb.delete("0.0", "end")
        for var in self._maniobra_checks.values():
            var.set(False)

    def _save(self) -> None:
        if not self._selected_pac_id:
            CTkMessagebox(title="Error", message="Seleccioná un paciente.", icon="cancel")
            return
        vet_key = self.vet_var.get()
        if not vet_key or vet_key not in self._vet_map:
            CTkMessagebox(title="Error", message="Seleccioná un veterinario.", icon="cancel")
            return
        try:
            fecha = datetime.datetime.strptime(self._vars["fecha"].get().strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            CTkMessagebox(title="Error", message="Formato de fecha inválido.", icon="cancel")
            return

        data = {
            "fecha": fecha,
            "motivo": self._vars["motivo"].get(),
            "peso_kg": self._vars["peso"].get(),
            "temperatura": self._vars["temp"].get(),
            "paciente_id": self._selected_pac_id,
            "veterinario_id": self._vet_map[vet_key],
        }
        for key, tb in self._text_widgets.items():
            data[key] = tb.get("0.0", "end").strip()

        maniobras_ids = [mid for mid, var in self._maniobra_checks.items() if var.get()]

        try:
            save_consulta(self.session, data, maniobras_ids, self._selected_consulta_id)
            CTkMessagebox(title="Éxito", message="Consulta guardada.", icon="check")
            self._load_historial()
        except Exception as exc:
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    def _delete(self) -> None:
        if not self._selected_consulta_id:
            return
        msg = CTkMessagebox(title="Eliminar", message="¿Eliminar esta consulta?",
                             icon="warning", option_1="Cancelar", option_2="Eliminar")
        if msg.get() == "Eliminar":
            delete_consulta(self.session, self._selected_consulta_id)
            self._selected_consulta_id = None
            self._new()
            self._load_historial()

    def _add_maniobra(self) -> None:
        nombre = self.new_man_nombre.get().strip()
        precio_str = self.new_man_precio.get().strip()
        if not nombre:
            CTkMessagebox(title="Error", message="El nombre de la maniobra es obligatorio.", icon="cancel")
            return
        try:
            precio = float(precio_str) if precio_str else 0.0
            save_maniobra(self.session, {"nombre": nombre, "precio": precio})
            self.new_man_nombre.delete(0, "end")
            self.new_man_precio.delete(0, "end")
            self._refresh_maniobras()
            CTkMessagebox(title="Éxito", message="Maniobra agregada.", icon="check")
        except Exception as exc:
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _load_historial(self) -> None:
        if not self._selected_pac_id:
            return
        consultas = get_consultas_by_paciente(self.session, self._selected_pac_id)
        self.hist_table.populate([
            (c.id, c.fecha.strftime("%Y-%m-%d"), c.motivo or "")
            for c in consultas
        ])

    def _refresh_combos(self) -> None:
        pacs = get_all_pacientes_activos(self.session)
        self._pac_map = {f"{p.nombre} — {p.tutor.apellido} (#{p.id})": p.id for p in pacs}
        self.pac_combo.configure(values=list(self._pac_map.keys()))

        vets = get_all_veterinarios(self.session)
        self._vet_map = {v.nombre_completo: v.id for v in vets}
        self.vet_combo.configure(values=list(self._vet_map.keys()))

    def _refresh_maniobras(self) -> None:
        """Reconstruye los checkboxes de maniobras en el panel derecho."""
        for widget in self.maniobras_scroll.winfo_children():
            widget.destroy()
        self._maniobra_checks.clear()

        self._maniobras_all = get_all_maniobras(self.session)
        for m in self._maniobras_all:
            var = tk.BooleanVar(value=False)
            self._maniobra_checks[m.id] = var
            ctk.CTkCheckBox(
                self.maniobras_scroll,
                text=f"{m.nombre}  (${m.precio:.2f})",
                variable=var,
                font=FONTS["body"],
                text_color=PALETTE["text"],
                checkmark_color="#FFFFFF",
                fg_color=PALETTE["primary"],
            ).pack(anchor="w", pady=2)

    def refresh(self) -> None:
        self.session.expire_all()
        self._refresh_combos()
        self._refresh_maniobras()
        self._new()
