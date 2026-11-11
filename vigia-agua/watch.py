"""Vigila una camara Hikvision (RTSP) y avisa al celular si el agua llega a la linea limite.

Uso:  python watch.py setup   -> marcas la linea limite con 2 clics (de dia, con la calle seca)
      python watch.py         -> vigila en el horario configurado
"""
import base64, json, os, sys, time, urllib.request
from datetime import datetime

import anthropic
import cv2

CAM = os.environ.get("CAM_URL", "")  # rtsp://usuario:clave@IP:554/Streaming/Channels/102
TOPIC = os.environ.get("NTFY_TOPIC", "")  # nombre largo y secreto, ej. agua-k3j9x2m7q
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")  # claude-haiku-5-5 es mas barato
EVERY = int(os.environ.get("EVERY_SEC", 120))
START, END = int(os.environ.get("FROM_H", 22)), int(os.environ.get("TO_H", 6))  # 8 h
LINE, REF = "limite.json", "referencia.jpg"

PROMPT = (
    "Imagen 1: la calle seca, con una linea roja = limite maximo tolerable de agua. "
    "Imagen 2: ahora mismo (puede ser de noche, infrarrojo, con lluvia, reflejos o luces de autos). "
    "Ignora lluvia en el aire y reflejos de luces; cuenta solo agua acumulada o corriendo en el suelo. "
    "El agua ha llegado a la linea roja o la pasa? Responde SOLO con SEGURO, CERCA (a poco de la linea) "
    "o ALERTA (toca o pasa la linea), luego ' - ' y una frase corta."
)


def in_window(h, start=START, end=END):
    return (h >= start or h < end) if start > end else start <= h < end


def grab():
    cap = cv2.VideoCapture(CAM)
    frame = None
    for _ in range(5):  # descarta frames viejos del buffer
        ok, f = cap.read()
        frame = f if ok else frame
    cap.release()
    if frame is None:
        raise RuntimeError("no pude leer la camara")
    return frame


def draw(frame, pts):
    out = frame.copy()
    cv2.line(out, tuple(pts[0]), tuple(pts[1]), (0, 0, 255), 3)
    return out


def b64(frame):
    s = min(1, 1280 / frame.shape[1])  # reduce para gastar menos tokens
    small = cv2.resize(frame, None, fx=s, fy=s)
    return base64.b64encode(cv2.imencode(".jpg", small)[1]).decode()


def img(data):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def notify(title, msg, priority="default"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=msg.encode(),
        headers={"Title": title, "Priority": priority, "Tags": "warning"},
    )
    urllib.request.urlopen(req, timeout=15)


def setup():
    frame, pts = grab(), []

    def click(e, x, y, *_):
        if e == cv2.EVENT_LBUTTONDOWN and len(pts) < 2:
            pts.append([x, y])

    cv2.namedWindow("limite")
    cv2.setMouseCallback("limite", click)
    while True:
        view = draw(frame, pts) if len(pts) == 2 else frame.copy()
        for p in pts:
            cv2.circle(view, tuple(p), 5, (0, 0, 255), -1)
        cv2.imshow("limite", view)
        k = cv2.waitKey(50)
        if k == ord("r"):
            pts.clear()
        if k == 13 and len(pts) == 2:  # Enter
            break
    cv2.imwrite(REF, draw(frame, pts))
    json.dump(pts, open(LINE, "w"))
    print(f"Guardado {LINE} y {REF}")


def main():
    if not (CAM and TOPIC and os.environ.get("ANTHROPIC_API_KEY")):
        sys.exit("Faltan variables: CAM_URL, NTFY_TOPIC, ANTHROPIC_API_KEY")
    if sys.argv[1:] == ["setup"]:
        return setup()
    pts = json.load(open(LINE))
    ref = b64(cv2.imread(REF))
    client = anthropic.Anthropic()
    notify("Vigia de agua activo", "Prueba: si lees esto, las alertas llegan.")
    fails, last_alert = 0, 0
    while True:
        if in_window(datetime.now().hour):
            try:
                r = client.messages.create(
                    model=MODEL, max_tokens=100,
                    messages=[{"role": "user", "content": [img(ref), img(b64(draw(grab(), pts))), {"type": "text", "text": PROMPT}]}],
                )
                verdict = r.content[0].text.strip()
                fails = 0
            except Exception as e:
                fails += 1
                print("error:", e)
                if fails == 3:  # si el vigia cae, avisa: sino dormirias confiado
                    notify("VIGIA CAIDO", f"No puedo vigilar: {e}", "high")
                verdict = ""
            print(datetime.now().strftime("%H:%M"), verdict)
            if verdict.startswith("ALERTA") and time.time() - last_alert > 600:
                notify("AGUA EN EL LIMITE", verdict, "urgent")
                last_alert = time.time()
            elif verdict.startswith("CERCA") and time.time() - last_alert > 1800:
                notify("Agua subiendo", verdict, "high")
                last_alert = time.time()
        time.sleep(EVERY)


if __name__ == "__main__":
    main()
