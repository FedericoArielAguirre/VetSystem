# =============================================================================
# VetSystem — modules/facturacion.py
# Service + View: Facturación con descuento automático de stock
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
from models import ArticuloInventario, Consulta, Factura, ItemFactura, Paciente, Tutor

# =============================================================================
# SERVICE
# =============================================================================


def _next_numero(session: Session) -> str:
    """Genera el próximo número de factura correlativo."""
    last = (
        session.query(Factura)
        .order_by(Factura.id.desc())
        .first()
    )
    next_id = (last.id + 1) if last else 1
    return f"FAC-{next_id:06d}"


def get_all_tutores(session: Session) -> list[Tutor]:
    return session.query(Tutor).order_by(Tutor.apellido).all()


def get_articulos_activos(session: Session) -> list[ArticuloInventario]:
    return (
        session.query(ArticuloInventario)
        .filter(ArticuloInventario.activo == True)
        .order_by(ArticuloInventario.nombre)
        .all()
    )


def get_consultas_sin_factura(session: Session, tutor_id: Optional[int] = None) -> list[Consulta]:
    """Consultas que no tienen un ItemFactura asociado."""
    subq = session.query(ItemFactura.consulta_id).filter(
        ItemFactura.consulta_id.isnot(None)
    ).subquery()
    q = (
        session.query(Consulta)
        .filter(Consulta.id.notin_(subq))
        .order_by(Consulta.fecha.desc())
        .limit(100)
    )
    return q.all()


def get_all_facturas(session: Session) -> list[Factura]:
    return (
        session.query(Factura)
        .order_by(Factura.fecha.desc())
        .limit(200)
        .all()
    )


def get_factura_by_id(session: Session, fid: int) -> Optional[Factura]:
    return session.get(Factura, fid)


def create_factura(
    session: Session,
    tutor_id: int,
    items: list[dict],  # [{"tipo": "articulo"|"consulta"|"manual", "ref_id": int|None, "desc": str, "qty": int, "precio": float}]
    descuento: float = 0.0,
    metodo_pago: str = "Efectivo",
    notas: str = "",
) -> Factura:
    """
    Crea la factura, sus ítems, descuenta stock de artículos y retorna la Factura.
    """
    if not items:
        raise ValueError("La factura debe tener al menos un ítem.")

    factura = Factura(
        numero=_next_numero(session),
        tutor_id=tutor_id,
        descuento=descuento,
        metodo_pago=metodo_pago or "Efectivo",
        notas=notas.strip() or None,
        pagado=True,
    )
    session.add(factura)
    session.flush()  # obtener factura.id

    subtotal = 0.0
    for item_data in items:
        qty = max(1, int(item_data.get("qty", 1)))
        precio = float(item_data.get("precio", 0))
        sub = round(qty * precio, 2)
        subtotal += sub

        item = ItemFactura(
            factura_id=factura.id,
            descripcion=item_data["desc"],
            cantidad=qty,
            precio_unitario=precio,
            subtotal=sub,
        )

        tipo = item_data.get("tipo", "manual")
        if tipo == "articulo" and item_data.get("ref_id"):
            art = session.get(ArticuloInventario, item_data["ref_id"])
            if art:
                if art.stock < qty:
                    raise ValueError(
                        f"Stock insuficiente para '{art.nombre}'. "
                        f"Disponible: {art.stock}, solicitado: {qty}."
                    )
                art.stock -= qty
                item.articulo_id = art.id

        elif tipo == "consulta" and item_data.get("ref_id"):
            item.consulta_id = item_data["ref_id"]

        session.add(item)

    factura.subtotal = round(subtotal, 2)
    factura.total = round(subtotal - descuento, 2)
    session.commit()
    session.refresh(factura)
    return factura


def delete_factura(session: Session, fid: int) -> None:
    f = session.get(Factura, fid)
    if f:
        session.delete(f)
        session.commit()


# =============================================================================
# VIEW — FacturacionFrame
# =============================================================================


class FacturacionFrame(ctk.CTkFrame):
    """Módulo de facturación."""

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly
        self._tutor_map: dict[str, int] = {}
        self._art_map: dict[str, dict] = {}  # label → {id, precio, nombre}
        self._consulta_map: dict[str, dict] = {}
        self._items_pendientes: list[dict] = []  # ítems a agregar a la factura actual
        self._selected_factura_id: Optional[int] = None

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

        ctk.CTkLabel(hdr, text="🧾 Facturación",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        self._build_historial(body)
        self._build_nueva_factura(body)

    def _build_historial(self, parent) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Historial de Facturas", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkButton(frame, text="🔄 Recargar", height=30, font=FONTS["small"],
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"],
                      text_color="#FFF", corner_radius=6,
                      command=self.refresh).grid(row=1, column=0, padx=12, pady=(0, 4), sticky="w")

        self.hist_table = BaseTable(
            frame,
            columns=[
                {"id": "id",     "text": "ID",     "width": 40,  "stretch": False},
                {"id": "numero", "text": "Número", "width": 110},
                {"id": "fecha",  "text": "Fecha",  "width": 100},
                {"id": "tutor",  "text": "Cliente","width": 120},
                {"id": "total",  "text": "Total",  "width": 80, "anchor": "e"},
                {"id": "pago",   "text": "Método", "width": 80},
            ],
            on_select=self._on_factura_select,
        )
        self.hist_table.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # Detalle de ítems de la factura seleccionada
        ctk.CTkLabel(frame, text="Ítems de la factura seleccionada", font=FONTS["small"],
                     text_color=PALETTE["text_muted"]).grid(row=3, column=0, padx=12, sticky="w")

        self.items_table = BaseTable(
            frame,
            columns=[
                {"id": "desc",    "text": "Descripción","width": 160},
                {"id": "qty",     "text": "Cant.",      "width": 50, "anchor": "center"},
                {"id": "precio",  "text": "Precio",     "width": 70, "anchor": "e"},
                {"id": "sub",     "text": "Subtotal",   "width": 80, "anchor": "e"},
            ],
            height=7,
        )
        self.items_table.grid(row=4, column=0, sticky="nsew", padx=12, pady=(2, 6))

        ctk.CTkButton(frame, text="🗑️ Anular Factura", height=32, font=FONTS["body"],
                      fg_color=PALETTE["danger"], hover_color=PALETTE["danger_dark"],
                      text_color="#FFF", corner_radius=8,
                      command=self._anular_factura).grid(row=5, column=0, padx=12, pady=(4, 12), sticky="w")

        frame.grid_rowconfigure(2, weight=2)
        frame.grid_rowconfigure(4, weight=1)

    def _build_nueva_factura(self, parent) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Nueva Factura", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        # Cliente
        ctk.CTkLabel(frame, text="Cliente (Tutor) *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=1, column=0, padx=12, sticky="w")
        self.tutor_var = tk.StringVar()
        self.tutor_combo = ctk.CTkComboBox(frame, variable=self.tutor_var, values=[],
                                            height=36, font=FONTS["body"],
                                            border_color=PALETTE["border"])
        self.tutor_combo.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))

        # ── Sección agregar ítem ─────────────────────────────────────────
        sep = ctk.CTkFrame(frame, height=1, fg_color=PALETTE["border"])
        sep.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(frame, text="Agregar Ítem", font=FONTS["body_bold"],
                     text_color=PALETTE["primary"]).grid(row=4, column=0, padx=12, sticky="w")

        # Tipo de ítem
        ctk.CTkLabel(frame, text="Tipo", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=5, column=0, padx=12, sticky="w", pady=(4, 2))
        self.tipo_var = tk.StringVar(value="Artículo")
        ctk.CTkComboBox(frame, variable=self.tipo_var,
                        values=["Artículo", "Consulta", "Manual"],
                        height=34, font=FONTS["body"], border_color=PALETTE["border"],
                        command=lambda _: self._on_tipo_change()).grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 4))

        # Referencia (artículo o consulta)
        ctk.CTkLabel(frame, text="Referencia", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=5, column=1, padx=12, sticky="w", pady=(4, 2))
        self.ref_var = tk.StringVar()
        self.ref_combo = ctk.CTkComboBox(frame, variable=self.ref_var, values=[],
                                          height=34, font=FONTS["body"],
                                          border_color=PALETTE["border"],
                                          command=lambda _: self._on_ref_change())
        self.ref_combo.grid(row=6, column=1, sticky="ew", padx=12, pady=(0, 4))

        # Descripción
        ctk.CTkLabel(frame, text="Descripción *", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=7, column=0, padx=12, sticky="w")
        self.desc_var = tk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.desc_var, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))

        # Cantidad y precio
        ctk.CTkLabel(frame, text="Cantidad", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=9, column=0, padx=12, sticky="w")
        self.qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(frame, textvariable=self.qty_var, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 4))

        ctk.CTkLabel(frame, text="Precio Unitario", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=9, column=1, padx=12, sticky="w")
        self.precio_var = tk.StringVar(value="0.00")
        ctk.CTkEntry(frame, textvariable=self.precio_var, height=34,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").grid(row=10, column=1, sticky="ew", padx=12, pady=(0, 4))

        ctk.CTkButton(frame, text="➕ Agregar Ítem", height=36, corner_radius=8,
                      font=FONTS["body_bold"], fg_color=PALETTE["success"],
                      hover_color="#1E8449", text_color="#FFF",
                      command=self._agregar_item).grid(
            row=11, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 8))

        # ── Tabla de ítems pendientes ─────────────────────────────────────
        sep2 = ctk.CTkFrame(frame, height=1, fg_color=PALETTE["border"])
        sep2.grid(row=12, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

        ctk.CTkLabel(frame, text="Ítems en esta factura", font=FONTS["body_bold"],
                     text_color=PALETTE["primary"]).grid(row=13, column=0, padx=12, sticky="w")

        ctk.CTkButton(frame, text="✖ Quitar último", height=28, font=FONTS["small"],
                      fg_color=PALETTE["danger"], hover_color=PALETTE["danger_dark"],
                      text_color="#FFF", corner_radius=6,
                      command=self._quitar_ultimo).grid(row=13, column=1, padx=12, sticky="e")

        self.pending_table = BaseTable(
            frame,
            columns=[
                {"id": "desc",   "text": "Descripción","width": 160},
                {"id": "qty",    "text": "Cant.",      "width": 50, "anchor": "center"},
                {"id": "precio", "text": "Precio",     "width": 70, "anchor": "e"},
                {"id": "sub",    "text": "Subtotal",   "width": 80, "anchor": "e"},
            ],
            height=6,
        )
        self.pending_table.grid(row=14, column=0, columnspan=2, sticky="nsew", padx=12, pady=(2, 4))

        # Totales
        totales_f = ctk.CTkFrame(frame, fg_color=PALETTE["row_alt"], corner_radius=8)
        totales_f.grid(row=15, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 8))

        ctk.CTkLabel(totales_f, text="Descuento ($):", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.desc_factura_var = tk.StringVar(value="0")
        ctk.CTkEntry(totales_f, textvariable=self.desc_factura_var, width=100, height=32,
                     font=FONTS["body"], border_color=PALETTE["border"],
                     fg_color="#FFFFFF").grid(row=0, column=1, padx=(0, 16))

        ctk.CTkLabel(totales_f, text="Método de pago:", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=0, column=2, padx=4)
        self.metodo_var = tk.StringVar(value="Efectivo")
        ctk.CTkComboBox(totales_f, variable=self.metodo_var,
                        values=["Efectivo", "Tarjeta Débito", "Tarjeta Crédito", "Transferencia", "Otro"],
                        height=32, width=150, font=FONTS["body"],
                        border_color=PALETTE["border"]).grid(row=0, column=3, padx=(0, 12))

        self.lbl_total = ctk.CTkLabel(totales_f, text="TOTAL: $0.00",
                                       font=("Segoe UI Semibold", 18),
                                       text_color=PALETTE["primary"])
        self.lbl_total.grid(row=0, column=4, padx=16)

        # Botón emitir
        ctk.CTkButton(frame, text="🧾 Emitir Factura", height=42, corner_radius=8,
                      font=("Segoe UI Semibold", 15),
                      fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"],
                      text_color="#FFF",
                      command=self._emitir_factura).grid(
            row=16, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 16))

        frame.grid_rowconfigure(14, weight=1)

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_tipo_change(self) -> None:
        tipo = self.tipo_var.get()
        if tipo == "Artículo":
            self.ref_combo.configure(values=list(self._art_map.keys()))
            self.ref_var.set("")
        elif tipo == "Consulta":
            self.ref_combo.configure(values=list(self._consulta_map.keys()))
            self.ref_var.set("")
        else:
            self.ref_combo.configure(values=[])
            self.ref_var.set("")
        self.desc_var.set("")
        self.precio_var.set("0.00")

    def _on_ref_change(self) -> None:
        tipo = self.tipo_var.get()
        ref = self.ref_var.get()
        if tipo == "Artículo" and ref in self._art_map:
            art_info = self._art_map[ref]
            self.desc_var.set(art_info["nombre"])
            self.precio_var.set(str(art_info["precio_venta"]))
        elif tipo == "Consulta" and ref in self._consulta_map:
            c_info = self._consulta_map[ref]
            self.desc_var.set(c_info["desc"])
            self.precio_var.set(str(c_info["precio"]))

    def _agregar_item(self) -> None:
        desc = self.desc_var.get().strip()
        if not desc:
            CTkMessagebox(title="Error", message="La descripción es obligatoria.", icon="cancel")
            return
        try:
            qty = int(self.qty_var.get())
            precio = float(self.precio_var.get())
        except ValueError:
            CTkMessagebox(title="Error", message="Cantidad o precio inválidos.", icon="cancel")
            return

        tipo = self.tipo_var.get()
        ref_id = None
        tipo_key = "manual"

        if tipo == "Artículo":
            ref = self.ref_var.get()
            if ref in self._art_map:
                ref_id = self._art_map[ref]["id"]
                tipo_key = "articulo"
        elif tipo == "Consulta":
            ref = self.ref_var.get()
            if ref in self._consulta_map:
                ref_id = self._consulta_map[ref]["id"]
                tipo_key = "consulta"

        item = {
            "tipo": tipo_key,
            "ref_id": ref_id,
            "desc": desc,
            "qty": qty,
            "precio": precio,
        }
        self._items_pendientes.append(item)
        self._refresh_pending_table()

        # Resetear campos
        self.desc_var.set("")
        self.qty_var.set("1")
        self.precio_var.set("0.00")
        self.ref_var.set("")

    def _quitar_ultimo(self) -> None:
        if self._items_pendientes:
            self._items_pendientes.pop()
            self._refresh_pending_table()

    def _refresh_pending_table(self) -> None:
        rows = []
        total = 0.0
        for it in self._items_pendientes:
            sub = it["qty"] * it["precio"]
            total += sub
            rows.append((it["desc"], it["qty"], f"${it['precio']:.2f}", f"${sub:.2f}"))
        self.pending_table.populate(rows)
        desc = float(self.desc_factura_var.get() or 0)
        self.lbl_total.configure(text=f"TOTAL: ${total - desc:,.2f}")

    def _emitir_factura(self) -> None:
        tutor_key = self.tutor_var.get()
        if not tutor_key or tutor_key not in self._tutor_map:
            CTkMessagebox(title="Error", message="Seleccioná un cliente.", icon="cancel")
            return
        if not self._items_pendientes:
            CTkMessagebox(title="Error", message="Agregá al menos un ítem.", icon="cancel")
            return
        try:
            descuento = float(self.desc_factura_var.get() or 0)
        except ValueError:
            descuento = 0.0

        try:
            f = create_factura(
                session=self.session,
                tutor_id=self._tutor_map[tutor_key],
                items=self._items_pendientes,
                descuento=descuento,
                metodo_pago=self.metodo_var.get(),
            )
            CTkMessagebox(
                title="Factura Emitida",
                message=f"✅ Factura {f.numero} emitida.\nTotal: ${f.total:,.2f}",
                icon="check",
            )
            self._items_pendientes.clear()
            self.refresh()
        except ValueError as exc:
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")
        except Exception as exc:
            CTkMessagebox(title="Error", message=f"Error inesperado:\n{exc}", icon="cancel")

    def _on_factura_select(self) -> None:
        vals = self.hist_table.selected_values()
        if not vals:
            return
        fid = int(vals[0])
        self._selected_factura_id = fid
        f = get_factura_by_id(self.session, fid)
        if not f:
            return
        self.items_table.populate([
            (it.descripcion, it.cantidad, f"${it.precio_unitario:.2f}", f"${it.subtotal:.2f}")
            for it in f.items
        ])

    def _anular_factura(self) -> None:
        if not self._selected_factura_id:
            return
        msg = CTkMessagebox(title="Anular", message="¿Anular (eliminar) esta factura? Esta acción no restaura stock.",
                             icon="warning", option_1="Cancelar", option_2="Anular")
        if msg.get() == "Anular":
            delete_factura(self.session, self._selected_factura_id)
            self._selected_factura_id = None
            self.items_table.clear()
            self.refresh()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _refresh_data(self) -> None:
        tutores = get_all_tutores(self.session)
        self._tutor_map = {f"{t.apellido}, {t.nombre}": t.id for t in tutores}
        self.tutor_combo.configure(values=list(self._tutor_map.keys()))

        arts = get_articulos_activos(self.session)
        self._art_map = {
            f"{a.nombre} [{a.codigo or '—'}]": {
                "id": a.id, "nombre": a.nombre, "precio_venta": a.precio_venta
            }
            for a in arts
        }

        consultas = get_consultas_sin_factura(self.session)
        self._consulta_map = {}
        for c in consultas:
            label = f"Consulta #{c.id} — {c.paciente.nombre if c.paciente else '?'} ({c.fecha.strftime('%Y-%m-%d')})"
            self._consulta_map[label] = {
                "id": c.id,
                "desc": f"Consulta veterinaria — {c.paciente.nombre if c.paciente else ''}",
                "precio": 0.0,
            }

        # Actualizar combo de referencia según tipo actual
        self._on_tipo_change()

    def refresh(self) -> None:
        self.session.expire_all()
        self._refresh_data()
        facturas = get_all_facturas(self.session)
        self.hist_table.populate([
            (
                f.id,
                f.numero,
                f.fecha.strftime("%Y-%m-%d"),
                f.tutor.nombre_completo if f.tutor else "",
                f"${f.total:,.2f}",
                f.metodo_pago or "",
            )
            for f in facturas
        ])
        self.items_table.clear()
        self._refresh_pending_table()
