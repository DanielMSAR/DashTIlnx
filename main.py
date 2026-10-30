from pathlib import Path
from nicegui import app, ui
from ui.dashboard_view import create_dashboard, start_background_monitors

# Obtener ruta absoluta de la carpeta 'assets'
ASSETS_DIR = Path(__file__).resolve().parent / 'assets'
app.add_static_files('/assets', str(ASSETS_DIR))

# Iniciar tareas globales de monitoreo en segundo plano
start_background_monitors()

# Definir la página principal para acceso web desde la red
@ui.page('/')
def index():
    create_dashboard()

# Ejecución en modo servidor headless para Linux (systemd)
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='TI Monitoreo',
        host='0.0.0.0',
        port=9090,
        reload=False,
        show=False,
        dark=True,
    )
