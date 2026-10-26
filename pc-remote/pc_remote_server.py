"""PC Remote — servidor MCP local que executa no PC os comandos do controle remoto.

Roda via stdio dentro do app Claude para desktop (nenhuma porta de rede é aberta).
O controle (artifact "Controle PC") manda os comandos pelo Claude, e a janela do
artifact aberta no PC chama as ferramentas abaixo como `host:pc_remote`.

Ferramentas:
  pc_status  -> informa sistema e nome do PC (somente leitura)
  pc_input   -> executa uma lista de ações de mouse/teclado/mídia em ordem
  pc_power   -> bloquear, suspender, desligar ou reiniciar
"""

from __future__ import annotations

import platform
import socket
import subprocess
from typing import Any

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from mcp.types import ToolAnnotations

SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"
MAX_ACTIONS = 200
MAX_MOVE = 4000
MAX_SCROLL = 100
MAX_TEXT = 2000

server = _Server("pc_remote")

_mouse = None
_keyboard = None


def _controllers():
    """Carrega o pynput só quando preciso, para pc_status funcionar mesmo sem tela."""
    global _mouse, _keyboard
    if _mouse is None:
        from pynput.keyboard import Controller as Keyboard
        from pynput.mouse import Controller as Mouse

        _mouse, _keyboard = Mouse(), Keyboard()
    return _mouse, _keyboard


def _key(name: str):
    from pynput.keyboard import Key, KeyCode

    name = name.lower()
    aliases = {
        "win": "cmd", "super": "cmd", "meta": "cmd", "command": "cmd",
        "control": "ctrl", "escape": "esc", "return": "enter",
        "del": "delete", "pgup": "page_up", "pgdn": "page_down",
        "vol_up": "media_volume_up", "vol_down": "media_volume_down",
        "mute": "media_volume_mute", "play_pause": "media_play_pause",
        "next": "media_next", "prev": "media_previous",
    }
    name = aliases.get(name, name)
    if hasattr(Key, name):
        return getattr(Key, name)
    if len(name) == 1:
        return KeyCode.from_char(name)
    raise ValueError(f"tecla desconhecida: {name}")


def _combo(keys: list[str]) -> None:
    _, kb = _controllers()
    resolved = [_key(k) for k in keys]
    for k in resolved:
        kb.press(k)
    for k in reversed(resolved):
        kb.release(k)


# Atalhos de navegação equivalentes em cada sistema.
_NAV = {
    "Windows": {"back": ["alt", "left"], "home": ["cmd"], "tasks": ["cmd", "tab"], "desktop": ["cmd", "d"]},
    "Darwin": {"back": ["cmd", "["], "home": ["cmd", "space"], "tasks": ["ctrl", "up"], "desktop": ["f11"]},
    "Linux": {"back": ["alt", "left"], "home": ["cmd"], "tasks": ["alt", "tab"], "desktop": ["cmd", "d"]},
}


def _button(name: str):
    from pynput.mouse import Button

    return {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name, Button.left)


def _clamp(value: Any, limit: int) -> int:
    return max(-limit, min(limit, int(value)))


def _run(action: dict[str, Any]) -> None:
    mouse, kb = _controllers()
    t = action.get("t")
    if t == "move":
        mouse.move(_clamp(action.get("dx", 0), MAX_MOVE), _clamp(action.get("dy", 0), MAX_MOVE))
    elif t == "click":
        mouse.click(_button(action.get("button", "left")), max(1, min(3, int(action.get("count", 1)))))
    elif t == "down":
        mouse.press(_button(action.get("button", "left")))
    elif t == "up":
        mouse.release(_button(action.get("button", "left")))
    elif t == "scroll":
        # dy > 0 rola para cima, dx > 0 rola para a direita (convenção do pynput)
        mouse.scroll(_clamp(action.get("dx", 0), MAX_SCROLL), _clamp(action.get("dy", 0), MAX_SCROLL))
    elif t == "key":
        k = _key(str(action["key"]))
        for _ in range(max(1, min(50, int(action.get("n", 1))))):
            kb.press(k)
            kb.release(k)
    elif t == "combo":
        _combo([str(k) for k in action["keys"]][:5])
    elif t == "text":
        kb.type(str(action.get("text", ""))[:MAX_TEXT])
    elif t == "media":
        _combo([str(action["key"])])
    elif t == "nav":
        _combo(_NAV.get(SYSTEM, _NAV["Linux"])[str(action["key"])])
    else:
        raise ValueError(f"ação desconhecida: {t}")


@server.tool(
    name="pc_status",
    description="Informa se o PC está pronto para receber comandos, com sistema e nome da máquina.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def pc_status() -> dict[str, Any]:
    try:
        _controllers()
        ready, error = True, None
    except Exception as exc:  # sem tela, sem permissão de acessibilidade etc.
        ready, error = False, str(exc)
    return {"ready": ready, "error": error, "os": SYSTEM, "name": socket.gethostname()}


@server.tool(
    name="pc_input",
    description=(
        "Executa em ordem uma lista de ações de entrada no PC. Cada ação é um objeto com 't': "
        "move{dx,dy} | click{button,count} | down{button} | up{button} | scroll{dx,dy} | "
        "key{key,n} | combo{keys[]} | text{text} | media{key: vol_up|vol_down|mute|play_pause|next|prev} | "
        "nav{key: back|home|tasks|desktop}."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
def pc_input(actions: list[dict[str, Any]]) -> dict[str, Any]:
    done, errors = 0, []
    for action in actions[:MAX_ACTIONS]:
        try:
            _run(action)
            done += 1
        except Exception as exc:
            errors.append(f"{action.get('t')}: {exc}")
    return {"done": done, "errors": errors[:5]}


_POWER = {
    "Windows": {
        "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "shutdown": ["shutdown", "/s", "/t", "0"],
        "restart": ["shutdown", "/r", "/t", "0"],
    },
    "Darwin": {
        "lock": ["pmset", "displaysleepnow"],
        "sleep": ["pmset", "sleepnow"],
        "shutdown": ["osascript", "-e", 'tell app "System Events" to shut down'],
        "restart": ["osascript", "-e", 'tell app "System Events" to restart'],
    },
    "Linux": {
        "lock": ["loginctl", "lock-session"],
        "sleep": ["systemctl", "suspend"],
        "shutdown": ["systemctl", "poweroff"],
        "restart": ["systemctl", "reboot"],
    },
}


@server.tool(
    name="pc_power",
    description="Bloqueia, suspende, desliga ou reinicia o PC. action: lock | sleep | shutdown | restart.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
def pc_power(action: str) -> dict[str, Any]:
    command = _POWER.get(SYSTEM, _POWER["Linux"]).get(action)
    if command is None:
        raise ValueError(f"ação de energia desconhecida: {action}")
    subprocess.Popen(command)
    return {"ok": True, "action": action}


if __name__ == "__main__":
    server.run()
