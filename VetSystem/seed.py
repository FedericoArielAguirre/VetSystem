# =============================================================================
# VetSystem — seed.py
# Datos iniciales: roles, usuarios demo, categorías y artículos de ejemplo
# =============================================================================

from __future__ import annotations

import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_core import SessionLocal, hash_password, init_db
from models import (
    ArticuloInventario,
    Categoria,
    Maniobra,
    Rol,
    Usuario,
)


def seed() -> None:
    print("[SEED] Inicializando base de datos...")
    init_db()

    session = SessionLocal()
    try:
        # ── Roles ────────────────────────────────────────────────────────────
        roles_data = ["admin", "veterinario", "recepcionista"]
        roles: dict[str, Rol] = {}
        for nombre in roles_data:
            rol = session.query(Rol).filter_by(nombre=nombre).first()
            if not rol:
                rol = Rol(nombre=nombre)
                session.add(rol)
                print(f"  [+] Rol creado: {nombre}")
            roles[nombre] = rol
        session.flush()

        # ── Usuarios demo ────────────────────────────────────────────────────
        usuarios_data = [
            {
                "username": "admin",
                "password": "admin123",
                "nombre_completo": "Administrador del Sistema",
                "email": "admin@vetsystem.com",
                "rol": "admin",
            },
            {
                "username": "dra.garcia",
                "password": "vet123",
                "nombre_completo": "Dra. Laura García",
                "email": "laura.garcia@vetsystem.com",
                "rol": "veterinario",
            },
            {
                "username": "recepcion",
                "password": "recep123",
                "nombre_completo": "Sofía Martínez",
                "email": "sofia.martinez@vetsystem.com",
                "rol": "recepcionista",
            },
        ]
        for u_data in usuarios_data:
            existing = session.query(Usuario).filter_by(username=u_data["username"]).first()
            if not existing:
                user = Usuario(
                    username=u_data["username"],
                    password_hash=hash_password(u_data["password"]),
                    nombre_completo=u_data["nombre_completo"],
                    email=u_data["email"],
                    rol=roles[u_data["rol"]],
                    activo=True,
                )
                session.add(user)
                print(f"  [+] Usuario creado: {u_data['username']} (pass: {u_data['password']})")

        session.flush()

        # ── Categorías de inventario ─────────────────────────────────────────
        categorias_data = [
            ("Medicamentos",    "Fármacos y productos veterinarios"),
            ("Alimentos",       "Alimentos balanceados y suplementos"),
            ("Accesorios",      "Collares, correas, juguetes y accesorios"),
            ("Higiene",         "Shampoos, cepillos y productos de limpieza"),
            ("Antiparasitarios","Productos antipulgas, garrapatas y vermífugos"),
            ("Servicios",       "Servicios prestados en consulta"),
        ]
        cats: dict[str, Categoria] = {}
        for nombre, desc in categorias_data:
            cat = session.query(Categoria).filter_by(nombre=nombre).first()
            if not cat:
                cat = Categoria(nombre=nombre, descripcion=desc)
                session.add(cat)
                print(f"  [+] Categoria creada: {nombre}")
            cats[nombre] = cat
        session.flush()

        # ── Artículos de inventario demo ─────────────────────────────────────
        articulos_data = [
            # (codigo, nombre, categoria, precio_compra, precio_venta, stock, stock_min, proveedor)
            ("MED-001", "Amoxicilina 500mg x10",     "Medicamentos",    800,  1400,  50, 10, "FarmVet SA"),
            ("MED-002", "Dexametasona Inyectable",   "Medicamentos",    350,   600,  30,  5, "FarmVet SA"),
            ("MED-003", "Ivermectina 1% x50ml",      "Medicamentos",    420,   750,  25,  8, "Vetfar"),
            ("MED-004", "Metronidazol 250mg x20",    "Medicamentos",    290,   520,  40, 10, "FarmVet SA"),
            ("ALI-001", "Royal Canin Perro Adulto 15kg","Alimentos",    4200,  6800,  20,  5, "DistribAlim"),
            ("ALI-002", "Whiskas Adulto 1kg",         "Alimentos",      380,   620,  35,  8, "DistribAlim"),
            ("ALI-003", "Purina Pro Plan Puppy 3kg",  "Alimentos",     1800,  2900,  15,  4, "DistribAlim"),
            ("ACC-001", "Collar Antiparasitario",     "Accesorios",     450,   850,  40, 10, "PetSupplies"),
            ("ACC-002", "Juguete Kong Rojo M",        "Accesorios",     800,  1400,  20,  5, "PetSupplies"),
            ("ACC-003", "Cama Polar 70cm",            "Accesorios",    1200,  2200,  10,  3, "PetSupplies"),
            ("HIG-001", "Shampoo Medicado 500ml",     "Higiene",        520,   950,  28,  6, "BioVet"),
            ("HIG-002", "Cepillo Slicker Mediano",    "Higiene",        320,   580,  15,  4, "PetSupplies"),
            ("ANT-001", "Frontline Spray 100ml",      "Antiparasitarios",950, 1650,  30,  8, "Boehringer"),
            ("ANT-002", "Nexgard Spectra 10-25kg",   "Antiparasitarios",1400, 2400,  20,  5, "Boehringer"),
            ("SRV-001", "Consulta General",           "Servicios",        0,  2500,   0,  0, "Interno"),
            ("SRV-002", "Vacuna Antirrábica",         "Servicios",      600,  1800,   0,  0, "Interno"),
            ("SRV-003", "Desparasitación interna",    "Servicios",      400,  1200,   0,  0, "Interno"),
        ]
        for codigo, nombre, cat_nombre, pc, pv, stock, stk_min, prov in articulos_data:
            existing = session.query(ArticuloInventario).filter_by(codigo=codigo).first()
            if not existing:
                art = ArticuloInventario(
                    codigo=codigo,
                    nombre=nombre,
                    categoria=cats[cat_nombre],
                    precio_compra=pc,
                    precio_venta=pv,
                    stock=stock,
                    stock_minimo=stk_min,
                    proveedor=prov,
                    activo=True,
                )
                session.add(art)
                print(f"  [+] Articulo creado: {nombre}")

        # ── Maniobras clínicas demo ──────────────────────────────────────────
        maniobras_data = [
            ("Consulta General",         "Examen clínico completo",       2500.0),
            ("Vacunación",               "Aplicación de vacuna",          1800.0),
            ("Desparasitación Interna",  "Administración de antiparásito",1200.0),
            ("Desparasitación Externa",  "Aplicación de antiparasitario ext.", 900.0),
            ("Extracción Dental",        "Extracción de pieza dentaria",  3500.0),
            ("Sutura",                   "Sutura de herida",              2800.0),
            ("Radiografía",              "Toma radiográfica",             4000.0),
            ("Análisis de Sangre",       "Hemograma completo",            3500.0),
            ("Ecografía Abdominal",      "Ecografía de abdomen",          5000.0),
            ("Castración Macho",         "Orquiectomía bilateral",        8000.0),
            ("Castración Hembra",        "Ovariohisterectomía",          12000.0),
            ("Internación (día)",        "Internación con vigilancia",    4500.0),
        ]
        for nombre, desc, precio in maniobras_data:
            existing = session.query(Maniobra).filter_by(nombre=nombre).first()
            if not existing:
                m = Maniobra(nombre=nombre, descripcion=desc, precio=precio, activo=True)
                session.add(m)
                print(f"  [+] Maniobra creada: {nombre}")

        session.commit()
        print("\n[OK] Seed completado exitosamente.")
        print("\nCredenciales de acceso:")
        print("  admin      / admin123     (Administrador)")
        print("  dra.garcia / vet123       (Veterinario)")
        print("  recepcion  / recep123     (Recepcionista)")

    except Exception as exc:
        session.rollback()
        print(f"\n[ERROR] Durante el seed: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
