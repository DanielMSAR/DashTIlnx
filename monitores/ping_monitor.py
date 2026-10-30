import asyncio
import platform
import socket
import subprocess


async def check_tcp_port(
    host: str, port: int = 4370, timeout: float = 2.0
) -> dict:
  """Verifica la conexión mediante un socket TCP (ideal para relojes ZKTeco que bloquean PING)."""
  loop = asyncio.get_running_loop()
  start_time = loop.time()

  def _socket_connect():
    with socket.create_connection((host, port), timeout=timeout):
      pass

  try:
    await loop.run_in_executor(None, _socket_connect)
    end_time = loop.time()
    latency_ms = round((end_time - start_time) * 1000)

    return {
        "status": "ONLINE",
        "latency": f"{latency_ms} ms",
        "is_up": True,
    }
  except (socket.timeout, ConnectionRefusedError, OSError):
    return {"status": "OFFLINE", "latency": "TIMEOUT", "is_up": False}


async def ping_host(host: str, timeout: int = 2) -> dict:
  """Realiza un ping ICMP a un host convencional y devuelve el estado y latencia."""
  is_windows = platform.system().lower() == "windows"
  if is_windows:
    cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
  else:
    cmd = ["ping", "-c", "1", "-W", str(timeout), host]

  loop = asyncio.get_running_loop()
  start_time = loop.time()
  try:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    returncode = await proc.wait()
  except OSError:
    return {"status": "OFFLINE", "latency": "ERROR", "is_up": False}
  end_time = loop.time()

  is_up = returncode == 0
  latency_ms = round((end_time - start_time) * 1000) if is_up else None

  return {
      "status": "ONLINE" if is_up else "OFFLINE",
      "latency": f"{latency_ms} ms" if is_up else "TIMEOUT",
      "is_up": is_up,
  }


async def check_single_device(server: dict) -> dict:
  """Evalúa si el dispositivo usa chequeo por socket TCP o PING tradicional."""
  check_type = server.get("type", "icmp")
  host = server.get("host")

  if check_type == "tcp":
    port = server.get("port", 4370)
    return await check_tcp_port(host, port)
  else:
    return await ping_host(host)


async def check_all_servers(servers_list: list) -> list:
  """Ejecuta las verificaciones a toda la lista de forma concurrente."""
  tasks = [check_single_device(s) for s in servers_list]
  results = await asyncio.gather(*tasks)

  # Combinar la información del servidor/reloj con el resultado obtenido
  for server, res in zip(servers_list, results):
    server.update(res)

  return servers_list
