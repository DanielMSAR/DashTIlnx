import json
from pathlib import Path
from nicegui import app, ui
from monitores.ping_monitor import check_all_servers
from monitores.backup_monitor import BACKUP_DIR, check_backup_files

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / 'data' / 'servidores.json'

def load_servers():
    if JSON_PATH.exists():
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_servers(servers):
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(servers, f, indent=4, ensure_ascii=False)

servers = load_servers()
backup_data = {'files': [], 'has_alert': False, 'status': 'CHECKING', 'message': '', 'last_check': '--'}
_monitors_started = False


# Grid de tarjetas estilo KPI Bloques Sólidos
@ui.refreshable
def render_grid():
    with ui.element('div').classes(
        'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4'
        ' xl:grid-cols-6 gap-3 p-4 w-full'
    ):
        for s in servers:
            is_up = s.get('is_up', None)

            # Definición de colores sólidos vibrantes estilo KPI
            if is_up is None:
                # Estado Pendiente / Verificando -> Amarillo
                card_bg = 'bg-amber-500'
            elif is_up:
                # Estado Online -> Verde
                card_bg = 'bg-emerald-600'
            else:
                # Estado Offline -> Rojo
                card_bg = 'bg-rose-600'

            with (
                ui.card()
                .classes(
                    f'w-full {card_bg} text-white p-4 rounded-xl shadow-md flex'
                    ' flex-col justify-between transition-all hover:scale-[1.02]'
                )
                .style('min-height: 110px;')
            ):
                # Título del equipo en la parte superior
                ui.label(s['name']).classes(
                    'text-sm font-bold text-white/90 truncate drop-shadow-sm w-full'
                ).tooltip(s['name'])

                # Estado principal destacado al centro (grande y blanco)
                status_text = s.get('status', 'VERIFICANDO')
                ui.label(status_text).classes(
                    'text-2xl font-black text-white tracking-wider my-1'
                    ' drop-shadow'
                )

                # IP y Latencia en la parte inferior
                with ui.row().classes(
                    'w-full justify-between items-center pt-2 border-t'
                    ' border-white/30 text-xs font-semibold text-white/90'
                ):
                    ui.label(s['host']).classes('font-mono truncate').tooltip(
                        s['host']
                    )
                    ui.label(s.get('latency', '--')).classes('font-mono font-bold')


# Tarjeta de Copias de Seguridad SQL
@ui.refreshable
def render_backup_card():
    has_alert = backup_data.get('has_alert', False)
    status_color = 'border-rose-500 bg-rose-950/20' if has_alert else 'border-emerald-500 bg-slate-800/90'
    
    with ui.card().classes(f'w-full max-w-none border-l-4 shadow-md {status_color} text-slate-100 p-4 mx-4 mb-4 rounded-r-lg'):
        with ui.row().classes('w-full justify-between items-center mb-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('storage', size='sm', color='rose' if has_alert else 'emerald')
                ui.label('Respaldos SQL').classes('font-bold text-sm')
                ui.label(f'({BACKUP_DIR})').classes('text-xs text-slate-400 font-mono')
            
            with ui.row().classes('items-center gap-3'):
                badge_bg = 'bg-rose-500/20 text-rose-300 border border-rose-500' if has_alert else 'bg-emerald-500/20 text-emerald-300 border border-emerald-500'
                status_label = 'ALERTA (>10 días)' if has_alert else 'OK (Actualizados)'
                if backup_data.get('status') == 'CHECKING':
                    status_label = 'VERIFICANDO...'
                    badge_bg = 'bg-amber-500/20 text-amber-300 border border-amber-500'
                elif backup_data.get('status') == 'ERROR':
                    status_label = 'ERROR / SIN ACCESO'
                
                ui.label(status_label).classes(f'text-xs px-2.5 py-0.5 rounded-full font-bold {badge_bg}')
                ui.label(f"Verificado: {backup_data.get('last_check', '--')}").classes('text-xs text-slate-400 font-mono')
        
        if backup_data.get('status') == 'ERROR':
            ui.label(backup_data.get('message', 'Error al acceder a la ruta')).classes('text-xs text-rose-400 font-bold p-2')
        elif not backup_data.get('files'):
            ui.label('Escaneando respaldos...').classes('text-xs text-slate-400 py-2')
        else:
            with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 mt-2'):
                for f in backup_data.get('files', []):
                    is_old = f.get('is_outdated', False)
                    card_border = 'border-rose-500 bg-rose-950/50 text-rose-100' if is_old else 'border-slate-700 bg-slate-900/80 text-slate-200'
                    text_age_color = 'text-rose-400 font-bold' if is_old else 'text-emerald-400'
                    
                    with ui.card().classes(f'p-3 border-l-4 rounded-r shadow-xs {card_border} flex flex-col justify-between gap-1'):
                        with ui.row().classes('w-full justify-between items-center no-wrap'):
                            ui.label(f['name']).classes('text-xs font-bold truncate w-full').tooltip(f['name'])
                        
                        with ui.row().classes('w-full justify-between items-center text-[11px] text-slate-400 font-mono mt-1 pt-1 border-t border-slate-700/50'):
                            ui.label(f['size']).classes('text-[11px] text-slate-400')
                            ui.label(f['mtime']).classes('text-[11px] text-slate-300')
                        
                        with ui.row().classes('w-full justify-between items-center mt-1'):
                            age_text = f"Hace {f['age_days']} días" if f['age_days'] > 0 else "Hoy"
                            ui.label(age_text).classes(f'text-xs {text_age_color}')
                            if is_old:
                                ui.label('¡>10 DÍAS!').classes('text-[10px] bg-rose-600 text-white px-1.5 py-0.5 rounded font-bold')
                            else:
                                ui.label('OK').classes('text-[10px] bg-emerald-700 text-white px-1.5 py-0.5 rounded font-bold')


# Función asíncrona que chequea los servidores y refresca el grid
async def update_data():
    await check_all_servers(servers)
    render_grid.refresh()


# Función asíncrona que chequea las copias de seguridad
async def update_backups():
    res = await check_backup_files()
    backup_data.update(res)
    render_backup_card.refresh()


def start_background_monitors():
    """Inicia los temporizadores globales de monitoreo una única vez en el servidor."""
    global _monitors_started
    if _monitors_started:
        return
    _monitors_started = True
    app.timer(5.0, update_data)
    app.timer(30.0, update_backups)


def create_dashboard():
    ui.dark_mode(True)
    
    # Encabezado
    with ui.header().classes('bg-slate-900 justify-between items-center px-6 py-3'):
        ui.label('DashBoard TI COFRA').classes('text-xl font-bold text-emerald-400')
        
        # Modal para agregar servidor
        with ui.dialog() as dialog, ui.card():
            ui.label('Agregar Nuevo Servidor').classes('text-lg font-bold')
            input_name = ui.input('Nombre (ej. Servidor BD)')
            input_host = ui.input('IP o Dominio (ej. 172.16.1.50)')
            
            def on_save():
                if input_name.value and input_host.value:
                    servers.append({'name': input_name.value, 'host': input_host.value})
                    save_servers(servers)
                    render_grid.refresh()
                    dialog.close()
                    ui.notify('Servidor agregado con éxito', type='positive')

            with ui.row():
                ui.button('Guardar', on_click=on_save).props('bg-emerald-600')
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                
        ui.button('Agregar Servidor', icon='add', on_click=dialog.open).props('bg-emerald-600')

    # Titular Servidores
    with ui.row().classes('w-full px-4 pt-4 justify-between items-center'):
        ui.label('Estado de Servidores y Red').classes('text-base font-bold text-slate-200')

    render_grid()

    # Titular Copias de Seguridad
    with ui.row().classes('w-full px-4 pt-2 justify-between items-center'):
        ui.label('Copias de Seguridad (SQL)').classes('text-base font-bold text-slate-200')

    render_backup_card()
