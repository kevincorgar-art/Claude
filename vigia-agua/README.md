# Vigia de agua (Hikvision)

Cada 2 min (22:00-06:00 por defecto) saca una foto de la camara, la compara con una foto de la calle seca
y la linea limite que marcaste, y Claude decide SEGURO / CERCA / ALERTA. ALERTA suena en tu celular.

## Una sola vez
1. **RTSP**: Hik-Connect es nube y no sirve para esto. El script lee la camara por la red de tu casa:
   busca la IP de la camara en tu router (o con SADP de Hikvision) y prueba en VLC la URL
   `rtsp://usuario:clave@IP:554/Streaming/Channels/102` (102 = flujo liviano; si pide, activa RTSP en el menu de la camara).
   Si la clave tiene `@` o `#`, escribelos como `%40` o `%23`.
2. **Celular**: instala la app gratis **ntfy**, suscribete a un tema con nombre largo y secreto (ej. `agua-k3j9x2m7q`)
   y en Ajustes permite que las notificaciones urgentes suenen aunque este en No molestar.
3. **PC que quede encendida de noche** (laptop vieja, Raspberry):
   `pip install -r requirements.txt` y exporta:
   ```
   export CAM_URL='rtsp://usuario:clave@192.168.1.64:554/Streaming/Channels/102'
   export NTFY_TOPIC='agua-k3j9x2m7q'
   export ANTHROPIC_API_KEY='sk-ant-...'
   ```
4. **De dia, con la calle seca**: `python watch.py setup` -> 2 clics para dibujar la linea limite, Enter para guardar (`r` repite).

## Cada noche
`python watch.py` (te llega una notificacion de prueba al arrancar). Si la camara o la API fallan 3 veces seguidas, te avisa.

Ajustes opcionales: `FROM_H`, `TO_H`, `EVERY_SEC`, `MODEL`.
Costo aprox.: 240 consultas por noche; con `MODEL=claude-haiku-5-5` es mucho menor.
