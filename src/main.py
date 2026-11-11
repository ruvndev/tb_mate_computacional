"""
Punto de entrada principal de la aplicación de escritorio:
Problema del Camino Mínimo — Algoritmo de Dijkstra Paso a Paso.

Arquitectura modular:
- `src/backend/`: Núcleo en Python (generación de grafos, layout 2D, algoritmo de Dijkstra y API).
- `src/frontend/`: Interfaz gráfica web offline en HTML5, CSS3 y JavaScript renderizada mediante pywebview.
"""

from pathlib import Path
import sys
import webview

# Asegurar que el directorio `src` esté en sys.path para las importaciones del paquete `backend`
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.api import DesktopAPI


class ApplicationLauncher:
    """Inicializa el puente de comunicación con Python y lanza la ventana nativa con pywebview."""

    @staticmethod
    def start() -> None:
        api = DesktopAPI()
        frontend_entry = SRC_DIR / "frontend" / "index.html"

        webview.create_window(
            title="Problema del Camino Mínimo - Algoritmo de Dijkstra",
            url=frontend_entry.as_uri(),
            js_api=api,
            width=1420,
            height=860,
            min_size=(1100, 700),
            background_color="#0d1117",
        )
        webview.start(debug=False)


if __name__ == "__main__":
    ApplicationLauncher.start()
