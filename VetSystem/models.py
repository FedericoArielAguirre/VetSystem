# =============================================================================
# VetSystem — models.py
# Todos los modelos de dominio (SQLAlchemy 2.0 declarative)
# =============================================================================

from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# =============================================================================
# SECCIÓN 1 — Autenticación y Usuarios
# =============================================================================

class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    usuarios: Mapped[List["Usuario"]] = relationship("Usuario", back_populates="rol")

    def __repr__(self) -> str:
        return f"<Rol {self.nombre}>"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")
    turnos: Mapped[List["Turno"]] = relationship("Turno", back_populates="veterinario")
    consultas: Mapped[List["Consulta"]] = relationship("Consulta", back_populates="veterinario")

    def __repr__(self) -> str:
        return f"<Usuario {self.username}>"


# =============================================================================
# SECCIÓN 2 — Tutores y Pacientes
# =============================================================================

class Tutor(Base):
    __tablename__ = "tutores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    apellido: Mapped[str] = mapped_column(String(150), nullable=False)
    dni: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    pacientes: Mapped[List["Paciente"]] = relationship(
        "Paciente", back_populates="tutor", cascade="all, delete-orphan"
    )
    facturas: Mapped[List["Factura"]] = relationship("Factura", back_populates="tutor")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    def __repr__(self) -> str:
        return f"<Tutor {self.nombre_completo}>"


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    especie: Mapped[str] = mapped_column(String(80), nullable=False)
    raza: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sexo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fecha_nacimiento: Mapped[Optional[datetime.date]] = mapped_column(
        DateTime, nullable=True
    )
    color: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    microchip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutores.id"), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    tutor: Mapped["Tutor"] = relationship("Tutor", back_populates="pacientes")
    turnos: Mapped[List["Turno"]] = relationship("Turno", back_populates="paciente")
    consultas: Mapped[List["Consulta"]] = relationship(
        "Consulta", back_populates="paciente"
    )

    def __repr__(self) -> str:
        return f"<Paciente {self.nombre} ({self.especie})>"


# =============================================================================
# SECCIÓN 3 — Agenda / Turnos
# =============================================================================

ESTADO_TURNO = ("Pendiente", "Completado", "Cancelado")


class Turno(Base):
    __tablename__ = "turnos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_hora: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, default=30)
    motivo: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="Pendiente")
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), nullable=False)
    veterinario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="turnos")
    veterinario: Mapped["Usuario"] = relationship("Usuario", back_populates="turnos")
    consulta: Mapped[Optional["Consulta"]] = relationship(
        "Consulta", back_populates="turno", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Turno {self.id} — {self.estado}>"


# =============================================================================
# SECCIÓN 4 — Consultas Clínicas y Maniobras
# =============================================================================

class Maniobra(Base):
    __tablename__ = "maniobras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio: Mapped[float] = mapped_column(Float, default=0.0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    consultas_link: Mapped[List["ConsultaManiobra"]] = relationship(
        "ConsultaManiobra", back_populates="maniobra"
    )

    def __repr__(self) -> str:
        return f"<Maniobra {self.nombre}>"


class Consulta(Base):
    __tablename__ = "consultas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    anamnesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    examen_fisico: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tratamiento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    peso_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperatura: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), nullable=False)
    veterinario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    turno_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("turnos.id"), nullable=True
    )
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="consultas")
    veterinario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="consultas"
    )
    turno: Mapped[Optional["Turno"]] = relationship(
        "Turno", back_populates="consulta"
    )
    maniobras_link: Mapped[List["ConsultaManiobra"]] = relationship(
        "ConsultaManiobra", back_populates="consulta", cascade="all, delete-orphan"
    )
    items_factura: Mapped[List["ItemFactura"]] = relationship(
        "ItemFactura", back_populates="consulta"
    )

    def __repr__(self) -> str:
        return f"<Consulta {self.id} — {self.fecha}>"


class ConsultaManiobra(Base):
    """Tabla de asociación Consulta ↔ Maniobra (M:N)."""

    __tablename__ = "consulta_maniobra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consulta_id: Mapped[int] = mapped_column(
        ForeignKey("consultas.id"), nullable=False
    )
    maniobra_id: Mapped[int] = mapped_column(
        ForeignKey("maniobras.id"), nullable=False
    )
    precio_aplicado: Mapped[float] = mapped_column(Float, default=0.0)

    consulta: Mapped["Consulta"] = relationship(
        "Consulta", back_populates="maniobras_link"
    )
    maniobra: Mapped["Maniobra"] = relationship(
        "Maniobra", back_populates="consultas_link"
    )


# =============================================================================
# SECCIÓN 5 — Inventario Unificado (Petshop + Farmacia)
# =============================================================================

class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)

    articulos: Mapped[List["ArticuloInventario"]] = relationship(
        "ArticuloInventario", back_populates="categoria"
    )

    def __repr__(self) -> str:
        return f"<Categoria {self.nombre}>"


class ArticuloInventario(Base):
    __tablename__ = "articulos_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categorias.id"), nullable=True
    )
    precio_compra: Mapped[float] = mapped_column(Float, default=0.0)
    precio_venta: Mapped[float] = mapped_column(Float, default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=5)
    proveedor: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    ubicacion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    categoria: Mapped[Optional["Categoria"]] = relationship(
        "Categoria", back_populates="articulos"
    )
    items_factura: Mapped[List["ItemFactura"]] = relationship(
        "ItemFactura", back_populates="articulo"
    )

    def __repr__(self) -> str:
        return f"<Articulo {self.nombre}>"


# =============================================================================
# SECCIÓN 6 — Facturación
# =============================================================================

class Factura(Base):
    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    fecha: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutores.id"), nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    descuento: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    pagado: Mapped[bool] = mapped_column(Boolean, default=False)
    metodo_pago: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    tutor: Mapped["Tutor"] = relationship("Tutor", back_populates="facturas")
    items: Mapped[List["ItemFactura"]] = relationship(
        "ItemFactura", back_populates="factura", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Factura {self.numero}>"


class ItemFactura(Base):
    __tablename__ = "items_factura"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    precio_unitario: Mapped[float] = mapped_column(Float, default=0.0)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    # Relaciones opcionales — un ítem puede ser artículo de inventario o consulta
    articulo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("articulos_inventario.id"), nullable=True
    )
    consulta_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("consultas.id"), nullable=True
    )

    factura: Mapped["Factura"] = relationship("Factura", back_populates="items")
    articulo: Mapped[Optional["ArticuloInventario"]] = relationship(
        "ArticuloInventario", back_populates="items_factura"
    )
    consulta: Mapped[Optional["Consulta"]] = relationship(
        "Consulta", back_populates="items_factura"
    )

    def __repr__(self) -> str:
        return f"<ItemFactura {self.descripcion} x{self.cantidad}>"
