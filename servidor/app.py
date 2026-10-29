"""Entrada ASGI para Render: uvicorn servidor.app:app --workers 1."""
import asyncio
from contextlib import suppress
import json

from fastapi import FastAPI, WebSocket

from servidor.salas import Conexion, ErrorSala, Salas

app = FastAPI(docs_url=None, redoc_url=None)
salas = Salas()
conexiones = set()


@app.get("/health")
def salud():
    return {"estado": "ok", "protocolo": 1}


@app.get("/")
def inicio():
    return {"aplicacion": "Diffie-Hellman · Matemática Aplicada", "protocolo": 1}


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    if len(conexiones) >= 250:
        await ws.close(code=1013, reason="Servidor completo")
        return
    cola = asyncio.Queue(maxsize=64)

    def emitir(mensaje):
        try:
            cola.put_nowait(mensaje)
        except asyncio.QueueFull:
            emisor.cancel()  # Cortar un consumidor lento sin bloquear a su pareja.

    cliente = Conexion(emitir=emitir)
    conexiones.add(cliente.id)

    async def enviar():
        while True:
            await ws.send_json(await cola.get())

    async def recibir():
        while True:
            paquete = await ws.receive()
            if paquete["type"] == "websocket.disconnect":
                return
            texto = paquete.get("text")
            try:
                if not isinstance(texto, str) or len(texto) > 16_384:
                    raise ErrorSala("El mensaje debe ser texto JSON de hasta 16 KB.")
                pedido = json.loads(texto)
                salas.ejecutar(cliente, pedido)
            except (ErrorSala, json.JSONDecodeError, TypeError, ValueError) as error:
                emitir({"evento": "error", "mensaje": str(error)})
                if cliente.sala:
                    emitir(salas.estado(cliente))

    emisor = asyncio.create_task(enviar())
    receptor = asyncio.create_task(recibir())
    emitir({"evento": "bienvenida", "protocolo": 1})
    try:
        terminadas, _ = await asyncio.wait((emisor, receptor), return_when=asyncio.FIRST_COMPLETED)
        for tarea in terminadas:
            with suppress(Exception, asyncio.CancelledError):
                tarea.result()
    finally:
        salas.desconectar(cliente)
        conexiones.discard(cliente.id)
        for tarea in (emisor, receptor):
            tarea.cancel()
            with suppress(Exception, asyncio.CancelledError):
                await tarea
        with suppress(Exception):
            await ws.close()
