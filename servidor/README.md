# Servidor de salas de Diffie-Hellman

Servicio FastAPI + WebSocket, preparado para una instancia **Free** de Render.
La aplicación de escritorio conserva la interfaz arcade, los cálculos y las
privadas. El servidor solo administra dos plazas por sala y reenvía datos públicos.

## Servicio publicado

- Dirección: https://mateaplicada-dh-salas.onrender.com
- Salud: https://mateaplicada-dh-salas.onrender.com/health
- Código fuente: `FranRuggi/mateaplicada-tpgrupal`, rama `FranFran`.
- Plan: Free. Los despliegues se lanzan manualmente desde Render.

La dirección ya está guardada en `configuracion.json`. Las dos personas pueden
abrir la app, entrar a **Modo red → Internet · salas** y compartir solo el código
de la sala. El enlace del servicio es la dirección del servidor; la interfaz
arcade sigue en la aplicación de escritorio.

Verificado el 29/10/2026 contra el servicio público: `/health`, dos clientes por
WSS, reserva de Alice y Bob, intercambio de p/g/A/B, derivación local de K en
ambos clientes y liberación del personaje al desconectarse. Para p=23, g=5,
a=6 y b=15, se recibieron A=8 y B=19 y cada cliente calculó K=2.

## Probar en una PC

Desde la raíz del repositorio:

```powershell
python -m pip install -r requirements.txt -r servidor/requirements.txt
python -m uvicorn servidor.app:app --host 127.0.0.1 --port 8765 --workers 1 --ws-max-size 32768
```

Abrir la aplicación dos veces. En **Modo red → Internet · salas**, usar
`http://127.0.0.1:8765` en ambas. Una crea sala y comparte su código; la otra lo
ingresa. Elegir Alice y Bob. Las dos entran a la partida automáticamente.

Para dos equipos de una LAN, ejecutar el servidor con `--host 0.0.0.0` y usar la
IP de ese equipo, siempre que la red permita la conexión al puerto elegido.

## Publicar en Render

El archivo `render.yaml`, en la raíz, define el servicio. Se usa la rama
`FranFran`, `plan: free`, sin discos, bases de datos ni servicios adicionales.

1. Subir la versión revisada de esa rama al repositorio.
2. En Render crear un **Blueprint** usando este repositorio y `render.yaml`,
   o crear un **Web Service** con estos valores:

| Campo | Valor |
|---|---|
| Runtime | Python |
| Branch | FranFran |
| Build | `pip install -r servidor/requirements.txt` |
| Start | `python -m uvicorn servidor.app:app --host 0.0.0.0 --port $PORT --workers 1 --ws-max-size 32768` |
| Health check | `/health` |
| Instance type | Free |

3. Verificar que `https://URL-REAL-DEL-SERVICIO/health` responde con
   `{"estado":"ok","protocolo":1}`.
4. Escribir la dirección **real** `https://...onrender.com` en `servidor_url`
   dentro de `configuracion.json`, o pegarla en el campo Servidor de las apps.
   El cliente convierte HTTPS a WSS y agrega `/ws`.
5. Probar dos clientes a través de esa dirección antes de distribuir el `.exe`.

`configuracion.json` se entrega junto al `.exe`. También se puede establecer
`DH_SERVER_URL`. No contiene contraseñas ni claves de Render.

## Límites del diseño de la demo

- Ejecutar **un solo proceso / worker** y una instancia: las salas viven en la
  memoria de ese proceso. No se necesita almacenamiento persistente.
- Render Free puede dormir por inactividad y reiniciarse. El cliente reintenta
  el arranque durante aproximadamente 90 segundos y permite cancelar saliendo.
  Si se corta una partida, se vuelve a la sala; no se restaura una privada perdida.
- Al salir un jugador, su plaza se libera y se invalidan los datos de la partida.
  Si entra otra persona, se crea un identificador de partida distinto.
- Las salas cerradas se eliminan. Los códigos tienen 8 caracteres aleatorios;
  no hay directorio público de salas ni autenticación de identidad personal.
- El servidor valida remitente, rol, campos, rangos, tamaños y partida. No acepta
  privadas ni secretos. Los enteros viajan como cadenas decimales, sin redondeo.
- El motor matemático propio valida los parámetros en cada PC. El servidor no
  realiza pruebas de primalidad ni calcula claves.
- Hay límites de conexiones, salas, frecuencia y colas para el servicio de demo.

## Verificación

```powershell
python -m unittest discover -s tests -v
```

Las pruebas incluyen un servidor real en un subproceso y dos clientes reales,
reservas simultáneas, rechazo de un tercer participante, mensajes inválidos,
enteros grandes, liberación de roles, separación de partidas y dos interfaces
Tk que completan el intercambio y ejecutan el ataque de Eve.
