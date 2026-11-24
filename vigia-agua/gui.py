"""Ventana para configurar y lanzar el vigia de agua. Se compila a VigiaAgua.exe (ver .github/workflows)."""
import json, os, secrets, subprocess, sys
from urllib.parse import quote

DATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "VigiaAgua")
SAVED = os.path.join(DATA, "datos.json")  # shortcut: claves en texto plano en tu usuario de Windows; cifrar si se comparte la PC
FIELDS = [  # (etiqueta, clave, oculto)
    ("IP de la grabadora", "ip", False), ("Usuario de la grabadora", "user", False),
    ("Clave de la grabadora", "pwd", True), ("Numero de camara (1, 2, 3...)", "canal", False),
    ("API key de Anthropic", "api", True), ("Pushover User Key", "puser", False),
    ("Pushover API Token", "ptoken", True), ("Vigilar desde la hora (0-23)", "desde", False),
    ("hasta la hora (0-24)", "hasta", False),
    ("Tema de ntfy (gratis, alternativa)", "ntfy", False),
]
OPTIONAL = {"puser", "ptoken", "ntfy"}  # basta ntfy, o Pushover completo
DEFAULTS = {"user": "admin", "canal": "1", "desde": "22", "hasta": "6", "ntfy": "agua-" + secrets.token_hex(5)}


def cam_url(ip, user, pwd, canal):
    # quote evita que @ o # en la clave rompan la URL; canal 1 -> 102 (flujo liviano)
    return f"rtsp://{quote(user, safe='')}:{quote(pwd, safe='')}@{ip}:554/Streaming/Channels/{int(canal)}02"


def env_for(d):
    return dict(
        os.environ, PYINSTALLER_RESET_ENVIRONMENT="1", CAM_URL=cam_url(d["ip"], d["user"], d["pwd"], d["canal"]),
        ANTHROPIC_API_KEY=d["api"], PUSHOVER_USER=d["puser"], PUSHOVER_TOKEN=d["ptoken"], NTFY_TOPIC=d["ntfy"],
        FROM_H=d["desde"], TO_H=d["hasta"],
    )


def spawn(mode, d):
    cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(__file__)]
    out = os.path.join(DATA, mode + ".log")
    p = subprocess.Popen(cmd + [mode, out], cwd=DATA, env=env_for(d), creationflags=0x08000000 if os.name == "nt" else 0)
    return p, out


def keep_awake(on):  # evita que Windows suspenda la PC mientras vigila
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 if on else 0x80000000)


def main():
    import tkinter as tk
    from tkinter import messagebox

    os.makedirs(DATA, exist_ok=True)
    try:
        saved = json.load(open(SAVED))
    except (OSError, ValueError):
        saved = {}
    root = tk.Tk()
    root.title("Vigia de agua")
    vars_ = {}
    for i, (label, key, hide) in enumerate(FIELDS):
        tk.Label(root, text=label, anchor="w").grid(row=i, column=0, sticky="w", padx=8, pady=2)
        vars_[key] = tk.StringVar(value=saved.get(key, DEFAULTS.get(key, "")))
        tk.Entry(root, textvariable=vars_[key], width=38, show="*" if hide else "").grid(row=i, column=1, padx=8)
    status = tk.StringVar(value="Llena los datos y sigue los botones en orden.")
    watcher = {"p": None, "log": None}

    def values():
        d = {k: v.get().strip() for k, v in vars_.items()}
        if not all(v for k, v in d.items() if k not in OPTIONAL) or not (d["ntfy"] or (d["puser"] and d["ptoken"])):
            return messagebox.showerror("Faltan datos", "Llena todos los campos y el tema de ntfy o las dos claves de Pushover.")
        try:
            int(d["canal"]); assert 0 <= int(d["desde"]) <= 24 and 0 <= int(d["hasta"]) <= 24
        except (ValueError, AssertionError):
            return messagebox.showerror("Datos invalidos", "Camara y horas deben ser numeros (horas 0-24).")
        json.dump(d, open(SAVED, "w"))
        return d

    def run_and_show(mode, title):
        d = values()
        if not d:
            return
        if mode != "setup" and not os.path.exists(os.path.join(DATA, "limite.json")):
            return messagebox.showwarning("Falta el limite", "Primero usa el boton 1 para marcar la linea limite.")
        status.set("Trabajando...")
        root.update()
        p, out = spawn(mode, d)
        p.wait()  # shortcut: bloquea la ventana unos segundos, cambiar a hilo si molesta
        try:
            text = open(out, encoding="utf-8").read().strip()[-700:]
        except OSError:
            text = ""
        status.set("Listo.")
        messagebox.showinfo(title, text or "Listo.")

    def start():
        d = values()
        if not d or (watcher["p"] and watcher["p"].poll() is None):
            return
        if not os.path.exists(os.path.join(DATA, "limite.json")):
            return messagebox.showwarning("Falta el limite", "Primero usa el boton 1 para marcar la linea limite.")
        watcher["p"], watcher["log"] = spawn("iniciar", d)
        keep_awake(True)
        status.set("Vigilando... deja esta ventana abierta (puedes minimizarla).")

    def stop():
        if watcher["p"] and watcher["p"].poll() is None:
            watcher["p"].terminate()
        keep_awake(False)
        status.set("Detenido.")

    def refresh():
        p = watcher["p"]
        if p:
            try:
                last = open(watcher["log"], encoding="utf-8").read().strip().splitlines()[-1:]
            except (OSError, IndexError):
                last = []
            state = "Vigilando" if p.poll() is None else "SE DETUVO (revisa el ultimo mensaje)"
            status.set(f"{state}. Ultimo: {last[0] if last else '-'}")
        root.after(5000, refresh)

    def close():
        stop()
        root.destroy()

    buttons = [
        ("1. Marcar limite (de dia, calle seca)", lambda: run_and_show("setup", "Limite")),
        ("2. Probar lectura ahora", lambda: run_and_show("probar", "Lectura")),
        ("3. Probar alarma en el iPhone", lambda: run_and_show("alarma", "Alarma")),
        ("4. INICIAR vigilancia", start), ("Detener", stop),
    ]
    for i, (text, cmd) in enumerate(buttons, start=len(FIELDS)):
        tk.Button(root, text=text, command=cmd).grid(row=i, column=0, columnspan=2, sticky="ew", padx=8, pady=3)
    tk.Label(root, textvariable=status, wraplength=380, justify="left").grid(row=len(FIELDS) + len(buttons), column=0, columnspan=2, padx=8, pady=8)
    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 2:  # modo trabajador: gui <modo> <archivo_salida>; el exe sin consola no tiene stdout
        sys.stdout = sys.stderr = open(sys.argv[2], "w", buffering=1, encoding="utf-8")
        sys.argv = sys.argv[:2]
        import watch
        try:
            watch.main()
        except SystemExit as e:
            if e.code:
                print(e.code)
    else:
        main()
