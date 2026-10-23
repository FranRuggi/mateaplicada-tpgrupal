# TP Final · Diffie-Hellman (Matemática Aplicada)

App de escritorio en **Python + CustomTkinter**.

## Cómo correrla

```bash
pip install -r requirements.txt
python main.py
```

En Linux puede hacer falta `sudo apt install python3-tk`. En Windows y Mac viene con Python.

## Estructura

```
main.py                    punto de entrada
core/aritmetica.py         MOTOR MATEMÁTICO   ← hoy es MOCK (usa pow de Python)
protocolo/sesion.py        Alice/Bob: estados, validaciones, errores amigables
transporte/canal.py        Canal (interfaz) + CanalMemoria ✔ / CanalArchivo ✘ / CanalSocket ✘
gui/tema.py                colores, fuentes, helper para no congelar la ventana
gui/componentes.py         tarjeta de participante, panel paso a paso, campos
gui/vistas/inicio.py       portada + estado de los módulos
gui/vistas/modo_local.py   Alice | Canal + Eve | Bob en la misma pantalla
gui/vistas/modo_red.py     un rol por computadora, por .txt o por sockets
gui/vistas/eve.py          ataque por fuerza bruta (logaritmo discreto)
```

Regla de dependencias: `gui → protocolo → core` y `gui → transporte`.
La GUI **nunca** hace cuentas. Por eso los módulos se pueden reemplazar sin tocarla.

## Cómo enchufar cada módulo

| Módulo | Qué hay que hacer | Cómo se nota en la GUI |
|---|---|---|
| Motor matemático | Reescribir las funciones de `core/aritmetica.py` sin cambiar sus firmas y poner `MOCK = False`. `mod_pow` tiene que devolver `(resultado, lista de Paso)`. | Desaparece "Motor: MOCK" y el panel Paso a paso muestra los pasos reales. |
| Canal por archivos | Implementar `CanalArchivo.enviar/recibir` usando `Mensaje.a_texto()` y `Mensaje.desde_texto()`. | El botón "Conectar" del modo red deja de mostrar "pendiente". |
| Canal por sockets | Implementar `CanalSocket`: Bob es el servidor y Alice el cliente. | Ídem. |
| Recepción en modo red | Hacer polling con `self.after(500, ...)` sobre `canal.recibir()` y pasar lo recibido a `Participante`. | Aparece lo recibido en la tarjeta. |

Cada `TODO(...)` del código marca un punto de enganche.

## Deploy

No hay servidor. Es una app de escritorio que corre en cada computadora.

- Para la demo con dos máquinas, hay que tener las dos PCs (o PC + VM con red en modo *bridge*) en la misma red.
- Opcional: `pyinstaller --onefile --windowed main.py` genera un `.exe` para que la otra PC no necesite Python.

## Preguntas para el profe

1. "Sin bibliotecas" ¿incluye los enteros grandes nativos de Python (`int` de precisión arbitraria) o hay que implementar la aritmética de números grandes también?
2. ¿Se puede usar `random` o `secrets` para generar la clave privada y los candidatos a primo, o también hay que hacer un generador propio (por ejemplo, un LCG)?
3. ¿La GUI puede usar una biblioteca externa (CustomTkinter)? Suponemos que sí, porque la restricción habla de "la matemática modular".
4. ¿Se puede usar `socket` de la biblioteca estándar para el objetivo secundario?
5. ¿Qué tamaño de `p` esperan ver en la demo (64, 256, 2048 bits)? Esto define cuánto hay que optimizar Miller-Rabin.
6. ¿La exposición dura 15 o 25 minutos? El instructivo dice las dos cosas.
