# =============================================================================
# VetSystem — main.py
# Punto de entrada: inicializa la DB, ejecuta seed si es primer arranque,
# y lanza la ventana de login.
# =============================================================================

from __future__ import annotations

import os
import sys

# Asegurar que el directorio del proyecto esté en el path de importaciones
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app_core import DATABASE_URL, init_db
from app_shell import LoginWindow


def _is_first_run() -> bool:
    """Retorna True si la base de datos todavía no existe."""
    db_path = DATABASE_URL.replace("sqlite:///", "")
    return not os.path.exists(db_path)


def main() -> None:
    first_run = _is_first_run()

    # Crear tablas (idempotente)
    init_db()

    # Sembrar datos iniciales solo en el primer arranque
    if first_run:
        print("🆕 Primera ejecución detectada — ejecutando seed…")
        try:
            from seed import seed
            seed()
        except Exception as exc:
            print(f"[WARN] No se pudo ejecutar el seed: {exc}")

    # Arrancar la interfaz gráfica
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
