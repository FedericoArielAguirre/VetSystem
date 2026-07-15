# =============================================================================
# VetSystem — modules/reportes.py
# Queries agregadas + View de Reportes
# =============================================================================

from __future__ import annotations

import datetime
import tkinter as tk

import customtkinter as ctk
from sqlalchemy import func
from sqlalchemy.orm import Session

from app_core import FONTS, PALETTE
from app_shell import BaseTable
from models import (
    ArticuloInventario,
    Categoria,
    Consulta,
    Factura,
    ItemFactura,
    Paciente,
    Tutor,
    Turno,
    Usuario,
)

# =============================================================================
# SERVICE — Queries agregadas
# =============================================================================


def ingresos_por_periodo(
    session: Session, desde: datetime.date, hasta: datetime.date
) -> list[tuple]:
    """Retorna (fecha, numero, cliente, total) de facturas en el período."""
    d = datetime.datetime.combine(desde, datetime.time.min)
    h = datetime.datetime.combine(hasta, datetime.time.max)
    facturas = (
        session.query(Factura)
        .filter(Factura.fecha >= d, Factura.fecha <= h)
        .order_by(Factura.fecha)
        .all()
    )
    result = []
    for f in facturas:
        result.append((
            f.fecha.strftime("%Y-%m-%d"),
            f.numero,
            f.tutor.nombre_completo if f.tutor else "",
            f"${f.total:,.2f}",
            f.metodo_pago or "",
        ))
    return result


def total_facturado_periodo(
    session: Session, desde: datetime.date, hasta: datetime.date
) -> float:
    d = datetime.datetime.combine(desde, datetime.time.min)
    h = datetime.datetime.combine(hasta, datetime.time.max)
    result = (
        session.query(func.sum(Factura.total))
        .filter(Factura.fecha >= d, Factura.fecha <= h)
        .scalar()
    )
    return result or 0.0


def pacientes_por_especie(session: Session) -> list[tuple]:
    """Retorna (especie, cantidad) agrupado."""
    rows = (
        session.query(Paciente.especie, func.count(Paciente.id).label("total"))
        .filter(Paciente.activo == True)
        .group_by(Paciente.especie)
        .order_by(func.count(Paciente.id).desc())
        .all()
    )
    return [(r.especie, r.total) for r in rows]


def turnos_por_estado(session: Session) -> list[tuple]:
    rows = (
        session.query(Turno.estado, func.count(Turno.id).label("total"))
        .group_by(Turno.estado)
        .all()
    )
    return [(r.estado, r.total) for r in rows]


def articulos_mas_vendidos(session: Session, top: int = 10) -> list[tuple]:
    rows = (
        session.query(
            ArticuloInventario.nombre,
            func.sum(ItemFactura.cantidad).label("total_vendido"),
            func.sum(ItemFactura.subtotal).label("total_ingresos"),
        )
        .join(ItemFactura, ItemFactura.articulo_id == ArticuloInventario.id)
        .group_by(ArticuloInventario.id)
        .order_by(func.sum(ItemFactura.cantidad).desc())
        .limit(top)
        .all()
    )
    return [(r.nombre, r.total_vendido, f"${r.total_ingresos:,.2f}") for r in rows]


def resumen_general(session: Session) -> dict:
    tutores = session.query(func.count(Tutor.id)).scalar() or 0
    pacientes = session.query(func.count(Paciente.id)).filter(Paciente.activo == True).scalar() or 0
    turnos_hoy = (
        session.query(func.count(Turno.id))
        .filter(
            Turno.fecha_hora >= datetime.datetime.combine(datetime.date.today(), datetime.time.min),
            Turno.fecha_hora <= datetime.datetime.combine(datetime.date.today(), datetime.time.max),
        )
        .scalar()
        or 0
    )
    facturas_total = session.query(func.count(Factura.id)).scalar() or 0
    ingresos_hoy = total_facturado_periodo(
        session, datetime.date.today(), datetime.date.today()
    )
    return {
        "tutores": tutores,
        "pacientes": pacientes,
        "turnos_hoy": turnos_hoy,
        "facturas": facturas_total,
        "ingresos_hoy": ingresos_hoy,
    }


# =============================================================================
# VIEW — ReportesFrame
# =============================================================================


class ReportesFrame(ctk.CTkFrame):
    """Módulo de reportes y estadísticas."""

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly

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

        ctk.CTkLabel(hdr, text="📊 Reportes",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._build_kpi_row(body)
        self._build_tabs(body)

    def _build_kpi_row(self, parent) -> None:
        """Fila superior de KPIs."""
        kpi_row = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self._kpi_labels: dict[str, ctk.CTkLabel] = {}
        kpis = [
            ("👥 Tutores",       "tutores",      PALETTE["primary"]),
            ("🐾 Pacientes",     "pacientes",    "#27AE60"),
            ("📅 Turnos Hoy",    "turnos_hoy",   "#8E44AD"),
            ("🧾 Facturas",      "facturas",     "#E67E22"),
            ("💰 Ingresos Hoy",  "ingresos_hoy", "#16A085"),
        ]
        for i, (label, key, color) in enumerate(kpis):
            card = ctk.CTkFrame(kpi_row, fg_color=PALETTE["bg_card"], corner_radius=12)
            card.pack(side="left", expand=True, fill="x", padx=6)

            ctk.CTkLabel(card, text=label, font=FONTS["small"],
                         text_color=PALETTE["text_muted"]).pack(padx=16, pady=(12, 2))
            lbl = ctk.CTkLabel(card, text="—", font=("Segoe UI Semibold", 20),
                               text_color=color)
            lbl.pack(padx=16, pady=(0, 12))
            self._kpi_labels[key] = lbl

    def _build_tabs(self, parent) -> None:
        """Área con pestañas de reportes."""
        tabs_frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        tabs_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        tabs_frame.grid_rowconfigure(1, weight=1)
        tabs_frame.grid_columnconfigure(0, weight=1)

        # Selector de tab
        tab_bar = ctk.CTkFrame(tabs_frame, fg_color="transparent")
        tab_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self._tab_names = [
            "Ingresos por Período",
            "Pacientes por Especie",
            "Turnos por Estado",
            "Artículos más Vendidos",
        ]
        self._active_tab = tk.StringVar(value=self._tab_names[0])
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        for name in self._tab_names:
            btn = ctk.CTkButton(
                tab_bar, text=name, height=34, font=FONTS["body"],
                corner_radius=8,
                fg_color=PALETTE["primary"] if name == self._tab_names[0] else PALETTE["border"],
                text_color="#FFF" if name == self._tab_names[0] else PALETTE["text"],
                hover_color=PALETTE["primary_dark"],
                command=lambda n=name: self._switch_tab(n),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_buttons[name] = btn

        # Área de contenido del tab
        self._tab_area = ctk.CTkFrame(tabs_frame, fg_color="transparent")
        self._tab_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._tab_area.grid_rowconfigure(1, weight=1)
        self._tab_area.grid_columnconfigure(0, weight=1)

        # ── Tab 1: Ingresos por período ──────────────────────────────────
        self._build_tab_ingresos()
        self._build_tab_especies()
        self._build_tab_turnos_estado()
        self._build_tab_articulos()

        self._switch_tab(self._tab_names[0])

    def _build_tab_ingresos(self) -> None:
        frame = ctk.CTkFrame(self._tab_area, fg_color="transparent")
        self._tab_frames = {"Ingresos por Período": frame}

        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(ctrl, text="Desde:", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).pack(side="left", padx=(0, 4))
        self.desde_var = tk.StringVar(
            value=(datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        )
        ctk.CTkEntry(ctrl, textvariable=self.desde_var, width=120, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").pack(side="left", padx=(0, 12))

        ctk.CTkLabel(ctrl, text="Hasta:", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).pack(side="left", padx=(0, 4))
        self.hasta_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        ctk.CTkEntry(ctrl, textvariable=self.hasta_var, width=120, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").pack(side="left", padx=(0, 12))

        ctk.CTkButton(ctrl, text="🔍 Consultar", height=34, font=FONTS["body"],
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"],
                      text_color="#FFF", corner_radius=8,
                      command=self._load_ingresos).pack(side="left")

        self.lbl_total_periodo = ctk.CTkLabel(ctrl, text="",
                                               font=("Segoe UI Semibold", 14),
                                               text_color=PALETTE["success"])
        self.lbl_total_periodo.pack(side="right", padx=8)

        self.ingr_table = BaseTable(
            frame,
            columns=[
                {"id": "fecha",  "text": "Fecha",   "width": 100},
                {"id": "numero", "text": "Número",  "width": 110},
                {"id": "cliente","text": "Cliente",  "width": 140},
                {"id": "total",  "text": "Total",   "width": 90, "anchor": "e"},
                {"id": "metodo", "text": "Método",  "width": 100},
            ],
        )
        self.ingr_table.grid(row=1, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

    def _build_tab_especies(self) -> None:
        frame = ctk.CTkFrame(self._tab_area, fg_color="transparent")
        self._tab_frames["Pacientes por Especie"] = frame

        self.esp_table = BaseTable(
            frame,
            columns=[
                {"id": "especie",   "text": "Especie",  "width": 200},
                {"id": "cantidad",  "text": "Cantidad", "width": 100, "anchor": "center"},
            ],
        )
        self.esp_table.pack(fill="both", expand=True)

    def _build_tab_turnos_estado(self) -> None:
        frame = ctk.CTkFrame(self._tab_area, fg_color="transparent")
        self._tab_frames["Turnos por Estado"] = frame

        self.tur_table = BaseTable(
            frame,
            columns=[
                {"id": "estado",   "text": "Estado",   "width": 150},
                {"id": "cantidad", "text": "Cantidad",  "width": 100, "anchor": "center"},
            ],
        )
        self.tur_table.pack(fill="both", expand=True)

    def _build_tab_articulos(self) -> None:
        frame = ctk.CTkFrame(self._tab_area, fg_color="transparent")
        self._tab_frames["Artículos más Vendidos"] = frame

        self.art_table = BaseTable(
            frame,
            columns=[
                {"id": "nombre",    "text": "Artículo",       "width": 200},
                {"id": "vendido",   "text": "Unidades Vend.", "width": 120, "anchor": "center"},
                {"id": "ingresos",  "text": "Ingresos",      "width": 110, "anchor": "e"},
            ],
        )
        self.art_table.pack(fill="both", expand=True)

    # ── Tab switching ────────────────────────────────────────────────────────

    def _switch_tab(self, name: str) -> None:
        for n, btn in self._tab_buttons.items():
            if n == name:
                btn.configure(fg_color=PALETTE["primary"], text_color="#FFF")
            else:
                btn.configure(fg_color=PALETTE["border"], text_color=PALETTE["text"])

        for n, frame in self._tab_frames.items():
            frame.grid_remove()

        frame = self._tab_frames.get(name)
        if frame:
            frame.grid(row=1, column=0, sticky="nsew")
            self._active_tab.set(name)
            self._load_tab_data(name)

    def _load_tab_data(self, name: str) -> None:
        if name == "Ingresos por Período":
            self._load_ingresos()
        elif name == "Pacientes por Especie":
            self.esp_table.populate(pacientes_por_especie(self.session))
        elif name == "Turnos por Estado":
            self.tur_table.populate(turnos_por_estado(self.session))
        elif name == "Artículos más Vendidos":
            self.art_table.populate(articulos_mas_vendidos(self.session))

    def _load_ingresos(self) -> None:
        try:
            desde = datetime.datetime.strptime(self.desde_var.get().strip(), "%Y-%m-%d").date()
            hasta = datetime.datetime.strptime(self.hasta_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            return
        rows = ingresos_por_periodo(self.session, desde, hasta)
        self.ingr_table.populate(rows)
        total = total_facturado_periodo(self.session, desde, hasta)
        self.lbl_total_periodo.configure(text=f"Total del período: ${total:,.2f}")

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self.session.expire_all()
        resumen = resumen_general(self.session)
        self._kpi_labels["tutores"].configure(text=str(resumen["tutores"]))
        self._kpi_labels["pacientes"].configure(text=str(resumen["pacientes"]))
        self._kpi_labels["turnos_hoy"].configure(text=str(resumen["turnos_hoy"]))
        self._kpi_labels["facturas"].configure(text=str(resumen["facturas"]))
        self._kpi_labels["ingresos_hoy"].configure(text=f"${resumen['ingresos_hoy']:,.2f}")
        # Cargar el tab activo
        self._load_tab_data(self._active_tab.get())
