# =============================================================================
# VetSystem — modules/inventario.py
# Service + View: Inventario Unificado (Petshop + Farmacia)
# Layout bipartito: panel izquierdo (lista) + panel derecho (formulario)
# =============================================================================

from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from sqlalchemy import func
from sqlalchemy.orm import Session

from app_core import FONTS, PALETTE
from app_shell import BaseTable
from models import ArticuloInventario, Categoria

# =============================================================================
# SERVICE
# =============================================================================


def get_all_articulos(session: Session) -> list[ArticuloInventario]:
    return (
        session.query(ArticuloInventario)
        .filter(ArticuloInventario.activo == True)
        .order_by(ArticuloInventario.nombre)
        .all()
    )


def search_articulos(session: Session, term: str) -> list[ArticuloInventario]:
    t = f"%{term}%"
    return (
        session.query(ArticuloInventario)
        .filter(
            ArticuloInventario.activo == True,
            (
                ArticuloInventario.nombre.ilike(t)
                | ArticuloInventario.codigo.ilike(t)
                | ArticuloInventario.proveedor.ilike(t)
            ),
        )
        .order_by(ArticuloInventario.nombre)
        .all()
    )


def get_articulo_by_id(session: Session, aid: int) -> Optional[ArticuloInventario]:
    return session.get(ArticuloInventario, aid)


def get_all_categorias(session: Session) -> list[Categoria]:
    return session.query(Categoria).order_by(Categoria.nombre).all()


def save_articulo(
    session: Session, data: dict, aid: Optional[int] = None
) -> ArticuloInventario:
    if aid:
        art = session.get(ArticuloInventario, aid)
        if not art:
            raise ValueError("Artículo no encontrado.")
    else:
        art = ArticuloInventario()
        session.add(art)

    art.codigo = data.get("codigo", "").strip() or None
    art.nombre = data["nombre"].strip()
    art.categoria_id = int(data["categoria_id"]) if data.get("categoria_id") else None
    art.precio_compra = float(data.get("precio_compra") or 0)
    art.precio_venta = float(data.get("precio_venta") or 0)
    art.stock = int(data.get("stock") or 0)
    art.stock_minimo = int(data.get("stock_minimo") or 5)
    art.proveedor = data.get("proveedor", "").strip() or None
    art.ubicacion = data.get("ubicacion", "").strip() or None

    session.commit()
    session.refresh(art)
    return art


def delete_articulo(session: Session, aid: int) -> None:
    art = session.get(ArticuloInventario, aid)
    if art:
        art.activo = False
        session.commit()


def get_bajo_stock(session: Session) -> list[ArticuloInventario]:
    """Retorna artículos cuyo stock es menor al stock_minimo."""
    return (
        session.query(ArticuloInventario)
        .filter(
            ArticuloInventario.activo == True,
            ArticuloInventario.stock < ArticuloInventario.stock_minimo,
        )
        .order_by(ArticuloInventario.stock)
        .all()
    )


def get_estadisticas(session: Session) -> dict:
    """Calcula valor total de inventario y cantidad de ítems activos."""
    arts = get_all_articulos(session)
    total_valor = sum(a.precio_venta * a.stock for a in arts)
    total_items = len(arts)
    categorias = session.query(Categoria).count()
    bajo_stock = len(get_bajo_stock(session))
    return {
        "total_valor": total_valor,
        "total_items": total_items,
        "categorias": categorias,
        "bajo_stock": bajo_stock,
    }


def save_categoria(session: Session, nombre: str) -> Categoria:
    cat = Categoria(nombre=nombre.strip())
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


# =============================================================================
# VIEW — InventarioFrame
# Layout: panel izquierdo (búsqueda + tabla) | panel derecho (formulario)
# =============================================================================


class InventarioFrame(ctk.CTkFrame):
    """
    Inventario Unificado.
    Panel izquierdo: artículos con categoría y stock + barra de búsqueda.
    Panel derecho: formulario Datos del Artículo.
    """

    def __init__(self, parent, session: Session, user, readonly: bool = False, **kwargs):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0, **kwargs)
        self.session = session
        self.user = user
        self.readonly = readonly
        self._selected_id: Optional[int] = None
        self._cat_map: dict[str, int] = {}

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

        ctk.CTkLabel(hdr, text="📦 Inventario Unificado",
                     font=FONTS["title"], text_color=PALETTE["primary"]).grid(
            row=0, column=0, padx=20, pady=14, sticky="w")

        # Botones extra en el header
        btn_f = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_f.grid(row=0, column=2, padx=12, sticky="e")

        ctk.CTkButton(
            btn_f, text="⚠️ Bajo Stock", height=34, font=FONTS["body"],
            fg_color=PALETTE["warning"], hover_color="#D68910",
            text_color="#FFF", corner_radius=8,
            command=self._show_bajo_stock,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_f, text="📊 Estadísticas", height=34, font=FONTS["body"],
            fg_color=PALETTE["primary"], hover_color=PALETTE["primary_dark"],
            text_color="#FFF", corner_radius=8,
            command=self._show_estadisticas,
        ).pack(side="left")

    # ── Body ────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        self._build_left_panel(body)
        self._build_right_panel(body)

    # ── Panel Izquierdo ──────────────────────────────────────────────────────

    def _build_left_panel(self, parent) -> None:
        left = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # ── Barra de búsqueda + botones ──────────────────────────────────
        top_bar = ctk.CTkFrame(left, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Buscar por nombre, código o proveedor…",
            height=36, font=FONTS["body"],
            border_color=PALETTE["border"], fg_color="#FFFFFF",
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", lambda _: self._on_search())

        ctk.CTkButton(top_bar, text="🔄 Recargar", height=36, width=90,
                      font=FONTS["body"], fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"], text_color="#FFF",
                      corner_radius=8, command=self.refresh).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(top_bar, text="✖ Limpiar", height=36, width=80,
                      font=FONTS["body"], fg_color=PALETTE["border"],
                      text_color=PALETTE["text"],
                      corner_radius=8,
                      command=self._clear_search).grid(row=0, column=2)

        # ── Tabla de artículos ───────────────────────────────────────────
        self.table = BaseTable(
            left,
            columns=[
                {"id": "id",       "text": "ID",       "width": 40,  "stretch": False},
                {"id": "codigo",   "text": "Código",   "width": 80,  "stretch": False},
                {"id": "nombre",   "text": "Nombre",   "width": 160},
                {"id": "cat",      "text": "Categoría","width": 100},
                {"id": "stock",    "text": "Stock",    "width": 55,  "anchor": "center"},
                {"id": "stk_min",  "text": "S. Mín",  "width": 55,  "anchor": "center"},
                {"id": "p_venta",  "text": "P. Venta", "width": 80,  "anchor": "e"},
            ],
            on_select=self._on_select,
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # Contador
        self.lbl_count = ctk.CTkLabel(left, text="", font=FONTS["small"],
                                       text_color=PALETTE["text_muted"])
        self.lbl_count.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 4))

    # ── Panel Derecho (Formulario) ───────────────────────────────────────────

    def _build_right_panel(self, parent) -> None:
        right = ctk.CTkFrame(parent, fg_color=PALETTE["bg_card"], corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Datos del Artículo", font=FONTS["subtitle"],
                     text_color=PALETTE["primary"]).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        fields = [
            ("Código (SKU/Lote)",  "codigo",       0, 0, "entry"),
            ("Nombre *",           "nombre",        0, 1, "entry"),
            ("Precio Compra",      "precio_compra", 1, 0, "entry"),
            ("Precio Venta",       "precio_venta",  1, 1, "entry"),
            ("Stock",              "stock",         2, 0, "entry"),
            ("Stock Mínimo",       "stock_minimo",  2, 1, "entry"),
            ("Proveedor",          "proveedor",     3, 0, "entry"),
            ("Ubicación",          "ubicacion",     3, 1, "entry"),
        ]

        self._entries: dict[str, ctk.CTkEntry] = {}
        for label, key, row, col, wtype in fields:
            r_lbl = row * 2 + 1
            r_wgt = row * 2 + 2
            ctk.CTkLabel(right, text=label, font=FONTS["body_bold"],
                         text_color=PALETTE["text"]).grid(
                row=r_lbl, column=col, sticky="w", padx=(12, 4), pady=(6, 2))
            entry = ctk.CTkEntry(right, height=36, font=FONTS["body"],
                         border_color=PALETTE["border"], fg_color="#FFFFFF")
            entry.grid(row=r_wgt, column=col, sticky="ew", padx=(12, 4), pady=(0, 2))
            self._entries[key] = entry

        # Categoría (combobox)
        ctk.CTkLabel(right, text="Categoría", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=9, column=0, sticky="w", padx=12, pady=(6, 2))
        self.cat_combo = ctk.CTkComboBox(right, values=[],
                                          height=36, font=FONTS["body"],
                                          border_color=PALETTE["border"])
        self.cat_combo.set("")
        self.cat_combo.grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 2))

        # Nueva categoría inline
        ctk.CTkLabel(right, text="Nueva categoría", font=FONTS["body_bold"],
                     text_color=PALETTE["text"]).grid(row=9, column=1, sticky="w", padx=12, pady=(6, 2))
        new_cat_f = ctk.CTkFrame(right, fg_color="transparent")
        new_cat_f.grid(row=10, column=1, sticky="ew", padx=12, pady=(0, 2))
        new_cat_f.grid_columnconfigure(0, weight=1)
        self.new_cat_entry = ctk.CTkEntry(new_cat_f, height=36, font=FONTS["body"],
                                           placeholder_text="Nombre…",
                                           border_color=PALETTE["border"], fg_color="#FFFFFF")
        self.new_cat_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(new_cat_f, text="➕", width=36, height=36, fg_color=PALETTE["success"],
                      text_color="#FFF", corner_radius=6,
                      command=self._add_categoria).grid(row=0, column=1)

        # ── Botones ──────────────────────────────────────────────────────
        btn_f = ctk.CTkFrame(right, fg_color="transparent")
        btn_f.grid(row=11, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 16))
        btn_cfg = {"height": 38, "corner_radius": 8, "font": FONTS["body_bold"]}

        ctk.CTkButton(btn_f, text="➕ Nuevo", fg_color=PALETTE["success"],
                      hover_color="#1E8449", text_color="#FFF",
                      command=self._new, **btn_cfg).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_f, text="💾 Guardar", fg_color=PALETTE["primary"],
                      hover_color=PALETTE["primary_dark"], text_color="#FFF",
                      command=self._save, **btn_cfg).pack(side="left", padx=(0, 6))

        if not self.readonly:
            ctk.CTkButton(btn_f, text="🗑️ Eliminar", fg_color=PALETTE["danger"],
                          hover_color=PALETTE["danger_dark"], text_color="#FFF",
                          command=self._delete, **btn_cfg).pack(side="left")

        right.grid_rowconfigure(12, weight=1)

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_select(self) -> None:
        vals = self.table.selected_values()
        if not vals:
            return
        aid = int(vals[0])
        self._selected_id = aid
        art = get_articulo_by_id(self.session, aid)
        if not art:
            return
        def _set(key, val):
            e = self._entries[key]
            e.delete(0, "end")
            e.insert(0, val)
        _set("codigo",       art.codigo or "")
        _set("nombre",       art.nombre)
        _set("precio_compra",str(art.precio_compra))
        _set("precio_venta", str(art.precio_venta))
        _set("stock",        str(art.stock))
        _set("stock_minimo", str(art.stock_minimo))
        _set("proveedor",    art.proveedor or "")
        _set("ubicacion",    art.ubicacion or "")
        cat_key = next(
            (k for k, v in self._cat_map.items() if v == art.categoria_id), ""
        )
        self.cat_combo.set(cat_key)

    def _new(self) -> None:
        self._selected_id = None
        for entry in self._entries.values():
            entry.delete(0, "end")
        self._entries["stock"].insert(0, "0")
        self._entries["stock_minimo"].insert(0, "5")
        self.cat_combo.set("")

    def _save(self) -> None:
        nombre = self._entries["nombre"].get().strip()
        if not nombre:
            CTkMessagebox(title="Error", message="El nombre es obligatorio.", icon="cancel")
            return
        cat_key = self.cat_combo.get()
        cat_id = self._cat_map.get(cat_key) if cat_key else None
        data = {k: e.get() for k, e in self._entries.items()}
        data["categoria_id"] = cat_id
        try:
            save_articulo(self.session, data, self._selected_id)
            CTkMessagebox(title="Exito", message="Articulo guardado.", icon="check")
            self.refresh()
        except Exception as exc:
            self.session.rollback()
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    def _delete(self) -> None:
        if not self._selected_id:
            return
        msg = CTkMessagebox(title="Eliminar", message="¿Desactivar este artículo?",
                             icon="warning", option_1="Cancelar", option_2="Eliminar")
        if msg.get() == "Eliminar":
            delete_articulo(self.session, self._selected_id)
            self._selected_id = None
            self._new()
            self.refresh()

    def _add_categoria(self) -> None:
        nombre = self.new_cat_entry.get().strip()
        if not nombre:
            return
        try:
            save_categoria(self.session, nombre)
            self.new_cat_entry.delete(0, "end")
            self._refresh_categorias()
            CTkMessagebox(title="Éxito", message=f"Categoría '{nombre}' creada.", icon="check")
        except Exception as exc:
            CTkMessagebox(title="Error", message=str(exc), icon="cancel")

    def _on_search(self) -> None:
        term = self.search_entry.get().strip()
        if term:
            arts = search_articulos(self.session, term)
        else:
            arts = get_all_articulos(self.session)
        self._populate(arts)

    def _clear_search(self) -> None:
        self.search_entry.delete(0, "end")
        self.refresh()

    def _show_bajo_stock(self) -> None:
        arts = get_bajo_stock(self.session)
        if not arts:
            CTkMessagebox(title="Bajo Stock", message="✅ Todos los artículos tienen stock suficiente.", icon="check")
            return
        # Mostrar ventana emergente
        win = ctk.CTkToplevel(self)
        win.title("⚠️ Artículos con Bajo Stock")
        win.geometry("640x400")
        win.grab_set()
        ctk.CTkLabel(win, text="⚠️ Artículos Bajo Stock Mínimo",
                     font=FONTS["title"], text_color=PALETTE["danger"]).pack(padx=16, pady=(16, 8))

        tbl = BaseTable(
            win,
            columns=[
                {"id": "nombre",  "text": "Nombre",     "width": 200},
                {"id": "cat",     "text": "Categoría",  "width": 100},
                {"id": "stock",   "text": "Stock Actual","width": 90, "anchor": "center"},
                {"id": "stk_min", "text": "Stock Mín",  "width": 80, "anchor": "center"},
                {"id": "prov",    "text": "Proveedor",  "width": 120},
            ],
        )
        tbl.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tbl.populate([
            (
                a.nombre,
                a.categoria.nombre if a.categoria else "",
                a.stock,
                a.stock_minimo,
                a.proveedor or "",
            )
            for a in arts
        ])

    def _show_estadisticas(self) -> None:
        stats = get_estadisticas(self.session)
        msg = (
            f"📦  Artículos activos:    {stats['total_items']}\n"
            f"🗂️  Categorías:           {stats['categorias']}\n"
            f"⚠️  Bajo stock:           {stats['bajo_stock']}\n"
            f"💰  Valor total inventario: ${stats['total_valor']:,.2f}"
        )
        CTkMessagebox(title="📊 Estadísticas de Inventario", message=msg, icon="info")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _refresh_categorias(self) -> None:
        cats = get_all_categorias(self.session)
        self._cat_map = {c.nombre: c.id for c in cats}
        self.cat_combo.configure(values=list(self._cat_map.keys()))

    def _populate(self, arts: list[ArticuloInventario]) -> None:
        rows = []
        for a in arts:
            rows.append((
                a.id,
                a.codigo or "",
                a.nombre,
                a.categoria.nombre if a.categoria else "",
                a.stock,
                a.stock_minimo,
                f"${a.precio_venta:.2f}",
            ))
        self.table.populate(rows)
        self.lbl_count.configure(text=f"{len(rows)} artículo(s) encontrado(s)")

    def refresh(self) -> None:
        self.session.expire_all()
        self._refresh_categorias()
        arts = get_all_articulos(self.session)
        self._populate(arts)
