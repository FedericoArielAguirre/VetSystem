# =============================================================================
# VetSystem — app_core.py
# Engine / Session SQLAlchemy + Paleta UI + Autenticación y Permisos
# =============================================================================

from __future__ import annotations

import hashlib
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base, Usuario

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

# La DB se crea junto al directorio de este archivo
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetsystem.db")
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=True, autocommit=False
)


def init_db() -> None:
    """Crea todas las tablas si no existen."""
    Base.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Paleta de colores y fuentes
# ---------------------------------------------------------------------------

PALETTE = {
    "primary":      "#3B6E91",   # azul profesional — sidebar, botones principales
    "primary_dark": "#2C5674",   # hover de primary
    "bg":           "#F5F6F8",   # fondo general
    "bg_card":      "#FFFFFF",   # fondo de tarjetas / paneles
    "sidebar_bg":   "#2C3E50",   # fondo del sidebar
    "sidebar_fg":   "#ECF0F1",   # texto del sidebar
    "sidebar_sel":  "#3B6E91",   # item seleccionado del sidebar
    "text":         "#222222",   # texto general
    "text_muted":   "#6C757D",   # texto secundario
    "danger":       "#C0392B",   # eliminar, alertas
    "danger_dark":  "#992D22",   # hover de danger
    "success":      "#27AE60",   # confirmaciones, estado OK
    "warning":      "#F39C12",   # advertencias
    "border":       "#D1D5DB",   # bordes sutiles
    "row_alt":      "#F0F4F8",   # filas alternadas de Treeview
    "header_bg":    "#E8EDF2",   # encabezado de tabla
}

FONTS = {
    "body":       ("Segoe UI", 13),
    "body_bold":  ("Segoe UI", 13, "bold"),
    "title":      ("Segoe UI Semibold", 16),
    "subtitle":   ("Segoe UI", 14),
    "small":      ("Segoe UI", 11),
    "sidebar":    ("Segoe UI", 13),
    "mono":       ("Consolas", 12),
}


# ---------------------------------------------------------------------------
# Helpers de contraseña
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_password(plain: str) -> str:
    """Retorna el hash SHA-256 de la contraseña."""
    return _sha256(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compara la contraseña en texto plano con el hash almacenado."""
    return _sha256(plain) == hashed


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

def authenticate_user(session: Session, username: str, password: str) -> Optional[Usuario]:
    """
    Verifica credenciales. Retorna el objeto Usuario si son válidas,
    None en caso contrario.
    """
    user: Optional[Usuario] = (
        session.query(Usuario)
        .filter(Usuario.username == username.strip(), Usuario.activo == True)
        .first()
    )
    if user and verify_password(password, user.password_hash):
        return user
    return None


# ---------------------------------------------------------------------------
# Permisos por rol
# ---------------------------------------------------------------------------

# Clave: nombre del módulo tal como aparecerá en el sidebar
# Valor: conjunto de roles con acceso
_MODULE_PERMISSIONS: dict[str, set[str]] = {
    "Pacientes":      {"admin", "veterinario", "recepcionista"},
    "Turnos":         {"admin", "veterinario", "recepcionista"},
    "Consultas":      {"admin", "veterinario"},
    "Inventario":     {"admin", "veterinario", "recepcionista"},
    "Facturación":    {"admin", "veterinario", "recepcionista"},
    "Reportes":       {"admin", "veterinario"},
    "Configuración":  {"admin", "veterinario"},
}

# Roles que tienen acceso de solo lectura (sin escritura) a ciertos módulos
_READONLY_MODULES: dict[str, set[str]] = {
    "Inventario": {"recepcionista"},
}


def get_user_permissions(rol_nombre: str) -> dict[str, dict]:
    """
    Retorna un diccionario de módulos accesibles para el rol dado.

    Estructura del valor:
        {
            "enabled": bool,
            "readonly": bool,
        }
    """
    result: dict[str, dict] = {}
    for module, allowed_roles in _MODULE_PERMISSIONS.items():
        if rol_nombre in allowed_roles:
            readonly = rol_nombre in _READONLY_MODULES.get(module, set())
            result[module] = {"enabled": True, "readonly": readonly}
    return result


# ---------------------------------------------------------------------------
# Íconos del sidebar (emojis)
# ---------------------------------------------------------------------------

SIDEBAR_ICONS: dict[str, str] = {
    "Pacientes":     "🐾 Pacientes",
    "Turnos":        "📅 Turnos",
    "Consultas":     "🩺 Consultas",
    "Inventario":    "📦 Inventario",
    "Facturación":   "🧾 Facturación",
    "Reportes":      "📊 Reportes",
    "Configuración": "⚙️ Configuración",
}
