# pump_wsl_helper.py  — Windows Python → WSL per-command, with UAC and absolute usbipd.exe
import os, re, time, shutil, subprocess

DISTRO = "Ubuntu"   # set to your exact WSL name from `wsl -l -v` (e.g., "Ubuntu-22.04")
USBIPD_EXE = r"C:\Program Files\usbipd-win\usbipd.exe"  # your installed path
PAUSE = 0.20

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def wsl(cmd: str, pause: float = PAUSE, check: bool = True):
    res = run(["wsl", "-d", DISTRO, "bash", "-lc", cmd])
    if res.stdout: print(res.stdout, end="")
    if res.stderr: print(res.stderr, end="")
    if check and res.returncode != 0:
        raise RuntimeError(f"WSL cmd failed ({res.returncode}): {cmd}\n{res.stderr}")
    time.sleep(pause)
    return res

# ---------- elevation (UAC) ----------
def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"

def run_elevated(app: str, args_list: list[str]) -> None:
    ps = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "Start-Process -FilePath {} -ArgumentList {} -Verb RunAs -Wait".format(
            _ps_quote(app), _ps_quote(" ".join(args_list))
        )
    ]
    res = run(ps)
    if res.returncode != 0:
        raise RuntimeError(f"Elevated call failed for {app} {args_list}\n{res.stderr}")

# ---------- usbipd attach ----------
def usbipd_list() -> str:
    if not os.path.isfile(USBIPD_EXE):
        raise RuntimeError(f"usbipd.exe not found at: {USBIPD_EXE}")
    res = run([USBIPD_EXE, "wsl", "list"])
    if res.returncode != 0:
        raise RuntimeError(f"'usbipd wsl list' failed:\n{res.stderr}")
    return res.stdout

def pick_busid(table: str) -> str | None:
    # Prefer Bartels PID b4c0; else any FTDI 0403:*
    cands = []
    for ln in table.splitlines():
        if re.search(r"\b0403:", ln, re.I):
            m_bus = re.match(r"\s*([0-9-]+(?:\.[0-9]+)*)\s+", ln)
            m_pid = re.search(r"\b0403:([0-9a-f]{4})\b", ln, re.I)
            if m_bus and m_pid:
                cands.append((m_pid.group(1).lower(), m_bus.group(1), ln))
    if not cands: return None
    for pid, bus, _ in cands:
        if pid == "b4c0": return bus
    return cands[0][1]

def try_attach(busid: str):
    # Try non-elevated first, then elevate (UAC) if needed
    a1 = run([USBIPD_EXE, "wsl", "attach", "--busid", busid, "--distribution", DISTRO])
    if a1.returncode == 0:
        return
    print("Requesting elevation to attach USB device to WSL…")
    run_elevated(USBIPD_EXE, ["wsl", "attach", "--busid", busid, "--distribution", DISTRO])

# ---------- serial discovery & setup ----------
def detect_port() -> str | None:
    res = wsl("ls -1 /dev/serial/by-id/* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n1",
              pause=0.05, check=False)
    return (res.stdout or "").strip() or None

def ensure_attached_and_bound():
    if detect_port():
        return
    table = usbipd_list()
    busid = pick_busid(table)
    if not busid:
        raise RuntimeError("No FTDI (VID 0403) device in 'usbipd wsl list'. Plug the pump in.")
    try_attach(busid)
    # Bind Linux FTDI driver + Bartels PID (0403:b4c0). If sudo prompts, it will print a warning.
    wsl("sudo -n modprobe ftdi_sio || sudo modprobe ftdi_sio || true", pause=0.05, check=False)
    wsl("echo 0403 b4c0 | sudo -n tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id >/dev/null || "
        "echo 0403 b4c0 | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id >/dev/null || true",
        pause=0.10, check=False)
    time.sleep(0.5)

def init_serial(port: str | None = None) -> str:
    ensure_attached_and_bound()
    p = port or detect_port()
    if not p:
        wsl("lsusb | grep -i 0403 || true", pause=0.05, check=False)
        raise RuntimeError("Still no /dev/ttyUSB* or /dev/ttyACM* after attach.")
    # 9600 8N1, no flow control, CR handling
    wsl(f"stty -F {p} 9600 cs8 -cstopb -parenb -ixon -ixoff -echo -icrnl", pause=0.05)
    return p

def send_pump(cmd: str, port: str, pause: float = PAUSE):
    wsl(f"printf '{cmd}\\r' > {port}", pause=pause)

def send_many(cmds: list[str], port: str, pause: float = PAUSE):
    for c in cmds:
        send_pump(c, port, pause=pause)

# ---- demo ----
if __name__ == "__main__":
    port = init_serial()
    send_many(["F100", "A150", "MR", "bon"], port, pause=0.20)
    wsl(f"printf '\\r' > {port}", pause=0.20)  # status (bare Enter)
