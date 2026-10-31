# TP Final · Diffie-Hellman (Matemática Aplicada)

App de escritorio en **Python + CustomTkinter**.

## Cómo correrla

```bash
python -m pip install -r requirements.txt
python main.py
```

Para ejecutar o probar el servidor de Internet, instalar también
`python -m pip install -r servidor/requirements.txt`. La app de escritorio no necesita
FastAPI ni Uvicorn para conectarse a un servidor ya publicado.

Después de actualizar el repositorio, repetí la instalación de `requirements.txt`
con el mismo `python` que usás para abrir `main.py`. El cifrado y descifrado de
mensajes requieren `cryptography`; si falta, el intercambio de claves puede
funcionar, pero esos botones mostrarán un error de dependencia. Instalá los
requisitos y volvé a abrir la app. Como alternativa, el archivo
[`ejecutable/DiffieHellman-TP.exe`](ejecutable/DiffieHellman-TP.exe) ya incluye
Python y todas las dependencias.

En Linux puede hacer falta `sudo apt install python3-tk`. En Windows y Mac viene con Python.

## Estructura

```
main.py                    punto de entrada
core/aritmetica.py         potencia modular propia, Miller-Rabin, primos y generadores
core/clave_simetrica.py    derivación de una clave AES desde K (HKDF-SHA256)
core/cifrado.py            cifrado autenticado de bytes (AES-256-GCM)
protocolo/sesion.py        Alice/Bob: estados, validaciones, errores amigables
protocolo/mensajes_cifrados.py  texto UTF-8 y sobre JSON para el cifrado
transporte/canal.py        CanalMemoria ✔ / CanalArchivo con sesiones y confirmación ✔ / CanalSocket (TCP en red local) ✔
gui/tema.py                colores, fuentes, helper para no congelar la ventana
gui/componentes.py         tarjeta de participante, panel paso a paso, campos
gui/escena.py              sprites y cola visual de los eventos del intercambio
gui/ataque_eve.py          ataque incrustado y datos capturados de la sesión
gui/registro.py            consola acoplable con separador arrastrable
gui/vistas/internet.py     sala y elección de personajes por Internet
gui/vistas/partida_red.py  escena compartida, con un rol controlable por PC
transporte/internet.py     cliente WebSocket en otro hilo
servidor/                  servidor de salas y requisitos para Render
render.yaml                configuración del servicio gratuito
configuracion.json         dirección pública del servidor para el .exe
assets/personajes-arcade.png  Alice, Eve y Bob en pixel art
gui/vistas/inicio.py       portada + estado de los módulos
gui/vistas/modo_local.py   escena arcade + controles de Alice y Bob + consola
gui/vistas/modo_red.py     un rol por computadora, por .txt o por sockets
gui/vistas/eve.py          ataque por fuerza bruta (logaritmo discreto)
```

Regla de dependencias: `gui → protocolo → core` y `gui → transporte`.
La GUI **nunca** hace cuentas. Por eso los módulos se pueden reemplazar sin tocarla.

## Escena arcade en Modo local

La escena muestra a Alice, Bob y Eve junto con el estado real del protocolo.
Al publicar parámetros o enviar una pública, un paquete recorre el canal y una
copia baja hacia Eve. Los personajes reaccionan al calcular, enviar y recibir.
Las privadas permanecen junto a sus dueños y se pueden mostrar con **Ver**;
el secreto se calcula por separado y nunca aparece como paquete.

Los controles de cada participante están debajo de la escena. **Consola** guarda
los mensajes con sus números completos y **Paso a paso** conserva el detalle
matemático de la última operación. En la escena y los campos compactos se
abrevian los números largos; **Copiar** conserva siempre el valor completo.

Los controles se agrupan en tres tarjetas: **Alice · Eve · Bob**, en el mismo
orden que los personajes. Alice y Bob muestran sus valores en filas; Eve agrupa
los datos capturados en dos columnas. El bloque se centra y tiene un ancho máximo
para mantener las tarjetas compactas al maximizar la ventana.

Durante un movimiento se pausan los controles de los participantes. **Reiniciar**
cancela también los movimientos pendientes. El interruptor **Animaciones** permite
terminar la cola visual y continuar sin esperas. La ventana sigue respondiendo.
El área de la escena y los controles se desplaza verticalmente si no entra en
una pantalla baja. El registro tiene su propio panel y sigue visible.

### Tamaño y ubicación de la consola

En la parte superior de **Modo local**, elegir **Abajo** o **Derecha** para
ubicar el panel de **Consola y pasos**. Arrastrar el separador entre ese panel
y la escena para cambiar su altura o su ancho. **Ampliar** le da más espacio
con un clic; **Restaurar** vuelve al tamaño anterior.

El historial, el detalle matemático y la pestaña seleccionada se conservan al
cambiar de ubicación, incluso durante el ataque de Eve. Se recuerda el tamaño
de cada ubicación mientras la ventana siga abierta. La escena y los controles
se desplazan de forma independiente del texto del registro.

En el modo lateral las tarjetas se reordenan según el espacio disponible:
tres en una fila, Alice y Bob arriba con Eve debajo, o una columna en el ancho
mínimo. Los parámetros también se acomodan para que sus botones sigan accesibles.

La escena está integrada en **Modo local** y en **Internet · salas**. La opción
de archivos conserva su interfaz anterior. Tk carga los sprites locales; el modo
local no necesita Internet. El modo de salas usa WebSocket para comunicarse.

## Salas por Internet

Servidor publicado en Render Free:
[mateaplicada-dh-salas.onrender.com](https://mateaplicada-dh-salas.onrender.com).
La dirección ya viene en `configuracion.json`. El servicio usa la rama `FranFran`
del repositorio del grupo; la interfaz sigue en la app de escritorio.

En **Modo red → Internet · salas**, el flujo tiene tres pasos separados:

1. **Sala:** una persona toca **Crear sala** y comparte el código; la otra lo
   ingresa y toca **Entrar a sala**. Durante la conexión se puede cancelar.
2. **Personaje:** recién dentro de la sala aparecen las tarjetas para elegir
   Alice o Bob y el código para compartir. Un personaje ocupado queda
   deshabilitado y el servidor evita reservas simultáneas del mismo rol.
3. **Partida:** cuando ambos eligieron, comienza automáticamente en las dos PC.

El paso actual queda marcado en la parte superior. Al salir de la sala se vuelve
al primer paso. Si se retira la otra persona, se vuelve a la elección conservando
el personaje propio.

Cada persona controla su privada y su cálculo de K. La tarjeta del otro personaje
es de solo lectura: muestra los datos públicos, sin recibir su privada o secreto.
Eve observa los mensajes y puede atacarlos en la misma escena. La consola admite
las mismas ubicaciones y ajustes que en el modo local.

Al desconectarse alguien se vuelve a la sala y se libera su personaje. La siguiente
partida tiene un identificador nuevo; no mezcla datos del intercambio anterior.
El servidor y el despliegue gratuito están explicados en [servidor/README.md](servidor/README.md).

### Atacar desde la misma escena

Debajo de los personajes, el panel de **Eve** completa `p`, `g`, `A` y `B` a
medida que terminan de pasar los paquetes por el canal. No hace falta cambiar de
pestaña ni copiar números. Calcular una pública sin enviarla no la revela a Eve.

Con `p`, `g` y `A` capturados, elegir el límite y tocar **Intentar ataque**.
La búsqueda real se ejecuta en otro hilo: el personaje se mueve mientras prueba
exponentes y muestra el contador y el resto del último candidato. Al encontrar
un exponente, Eve festeja; si agota el límite, muestra que no lo encontró dentro
de ese número de intentos. **Detener** cancela la búsqueda.

Si además capturó `B`, Eve calcula por su cuenta `K = B^a mod p` usando el
exponente encontrado. Si `B` llega después, completa ese cálculo sin repetir la
búsqueda. No consulta las privadas ni el secreto de los participantes. El
resultado y los intentos también quedan en la consola.

**Reiniciar** o publicar otra sesión cancela el ataque y descarta los resultados
pendientes para evitar mezclar intercambios. La sección separada **Ataque de Eve**
se mantiene para cargar casos manuales o traer datos del modo red.

## Intercambio por carpeta compartida

Se pueden abrir dos instancias en una misma PC o una instancia en cada PC.
Cada participante debe poder leer y escribir en **la misma carpeta física**.
Las rutas pueden ser distintas en cada equipo (por ejemplo, una unidad de red).

1. Abrir la aplicación dos veces y elegir **Modo red → Archivos · Sockets**.
2. Elegir **Alice** en una instancia y **Bob** en la otra. Usar **Archivos .txt**.
3. Seleccionar la carpeta compartida en ambas y escribir el mismo código de
   **Sesión**. `demo` sirve para la primera prueba. El botón **Nuevo** genera
   otro código: copiarlo también en la instancia de Bob.
4. Tocar **Conectar** en ambas. La conexión no consume mensajes pendientes.
5. Alice ingresa `p = 23`, `g = 5` y toca **Publicar p y g al canal**.
   También puede generar automáticamente parámetros de 64 bits.
6. Alice elige privada `6` y calcula A; Bob elige privada `15` y calcula B.
   Cada uno envía su pública. La recepción es automática cada 500 ms;
   **Buscar mensajes nuevos** permite adelantarla manualmente.
7. Derivar el secreto en cada instancia: el resultado esperado es `K = 2`.

Para parámetros grandes, se pueden usar privadas aleatorias. Los números
pequeños del ejemplo son exclusivamente didácticos.

### Qué queda en la carpeta

```text
carpeta-compartida/
  sesiones/
    demo/
      Alice_a_Bob_<orden>_<id>.txt
      Alice_a_Bob_<otro-orden>_<otro-id>.txt
      Bob_a_Alice_<orden>_<id>.txt
      rechazados/                 mensajes inválidos para inspeccionar
```

- Cada envío crea un archivo distinto. Los mensajes pendientes no se sobrescriben.
- Los nombres permiten ordenar los mensajes de cada emisor. Un emisor que se
  reinicia también toma en cuenta la secuencia de los archivos pendientes.
- Se escribe primero un `.tmp` y después se publica el `.txt` completo.
  Los archivos temporales no se reciben.
- `recibir()` lee y conserva el archivo. `confirmar()` lo retira **después**
  de que el participante lo haya procesado. Un error de acceso deja el mensaje
  pendiente para reintentar; un mensaje inválido se aparta en `rechazados/`.
- Una retransmisión idéntica de parámetros o de una pública conserva el estado
  ya calculado. Recibir una pública diferente invalida el secreto anterior.
- Los mensajes contienen solo datos públicos: `p`, `g`, `A` o `B`.
  Las privadas y el secreto compartido no se escriben en el canal.

Usar **una sola instancia por rol y sesión**. Para comenzar otro intercambio,
desconectar ambas y elegir un código de sesión nuevo. Desconectar no borra la
cola; al reiniciar la aplicación se pierden las privadas que estaban en memoria.
La sesión separa intercambios, pero no autentica a los participantes.

Ambas instancias deben utilizar esta versión: los archivos con el nombre fijo
del prototipo (`Alice_a_Bob.txt`) no se consumen ni se borran automáticamente.

## Intercambio por sockets en la red local (objetivo secundario)

Conexión TCP directa entre dos computadoras, con `socket` de la biblioteca
estándar. No usa Internet ni el servidor de Render: las dos PC (o una PC y una
máquina virtual con red en modo *bridge*) tienen que estar en la **misma red**.

1. En las dos PC: **Modo red → Archivos · Sockets** y en Transporte elegir
   **Sockets TCP**.
2. **Bob** elige su rol y toca **Conectar**. Queda escuchando en el puerto
   (5000 por defecto) y la tarjeta muestra **su IP en la red**.
3. **Alice** escribe esa IP y el mismo puerto, y toca **Conectar**. Si Bob
   todavía no estaba escuchando, Alice reintenta cada segundo.
4. Cuando las dos dicen **Conectado**, seguir los pasos 5 a 7 de la carpeta
   compartida. El resultado esperado es otra vez `K = 2`.

Los mensajes tienen el mismo formato que los `.txt`, con una línea vacía al
final para marcar dónde termina cada uno (TCP entrega bytes, no mensajes).
Un hilo lee el socket y la interfaz consulta lo recibido cada 500 ms, así la
ventana no se congela. Un mensaje mal formado se descarta sin cortar la
conexión. Si el otro se desconecta, se informa en el estado.

La primera vez que Bob escucha, Windows puede preguntar por el firewall:
permitir el acceso en **redes privadas**. Para otro intercambio, desconectar
ambas y volver a conectar. Para probar en una sola PC, usar la IP `127.0.0.1`.

## Probar el ataque de Eve sin copiar números

En **Ataque de Eve**, usar **Traer de Modo local** o **Traer de Modo red**.
Se cargan automáticamente `p`, `g` y la pública `A` de Alice que ya circularon
por el canal. La privada y el secreto compartido no se transfieren a esa vista.

En modo red se usan los datos enviados y recibidos por **esa misma instancia**:
sirve tanto desde Alice como desde Bob, incluso después de confirmar y retirar
los archivos del intercambio. Traer datos no lee ni consume mensajes de la cola.
Al desconectar, se limpia esta instantánea de la sesión.

Si faltan valores, la vista los indica y limpia los campos faltantes para no
mezclar intercambios. Primero publicar los parámetros y enviar `A`; después
volver a traer los datos, elegir el límite y tocar **Intentar romper**.
También se mantiene la carga manual y el atajo desde el canal del modo local.

## Funciones de cifrado de mensajes

La base modular para cifrar y descifrar textos a partir de K está implementada
en `core/clave_simetrica.py`, `core/cifrado.py` y
`protocolo/mensajes_cifrados.py`. Usa HKDF-SHA256 y AES-256-GCM mediante
`cryptography`; la aritmética propia de Diffie-Hellman conserva su módulo.
La pestaña **Mensajes** permite redactar, cifrar y enviar textos después del
intercambio de A/B y la derivación de K. Funciona en local, archivos, TCP y
salas con el servidor actualizado. Si el destinatario todavía no derivó K,
el mensaje queda pendiente de descifrado. Tener K tampoco lo abre automáticamente:
el destinatario pulsa **Descifrar mensaje** en **Conversación**, un mensaje por
clic. En local se elige el rol del destinatario para ver sus recibidos.
En **Eve / canal** se ve el cifrado
y, si el ataque reconstruye K, el texto recuperado. La tarjeta de Eve conserva
la selección del límite de intentos.

`protocolo/conversacion.py` administra la sesión y las lecturas;
`gui/mensajes.py` es el panel compartido. El servidor anuncia la capacidad
`mensajes-cifrados-v1`; en servidores anteriores la GUI mantiene DH y
deshabilita los mensajes cifrados. Ver la API, el formato y los límites en
[docs/CIFRADO.md](docs/CIFRADO.md).

## Verificación

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren orden y persistencia de la cola, sesiones, errores de lectura
y confirmación, mensajes inválidos, intercambio entre dos procesos y recepción
automática en la interfaz. Las pruebas de interfaz necesitan Tk y una sesión gráfica.
También se comprueba el intercambio desde los controles de la escena, los números
grandes, las copias públicas para Eve y el reinicio de una animación en curso.
El ataque integrado cubre éxito, límite, cancelación, progreso real, llegada
posterior de `B` y resultados tardíos después de reiniciar.

## Deploy

La app de escritorio corre en cada computadora. El modo de salas requiere el
servidor publicado; el modo local y el intercambio por archivos son independientes.

- En las salas por Internet, cada persona abre la app en su computadora y
  comparte el código de sala. No hace falta una carpeta compartida.
- Para la opción **Archivos .txt**, ambas necesitan acceso de lectura y escritura
  a la carpeta compartida. Para probar en una PC alcanza con abrir dos instancias.
- Para **Sockets TCP**, ambas tienen que estar en la misma red local y Alice
  necesita la IP de Bob. Para probar en una PC, usar `127.0.0.1`.

### Ejecutable de Windows dentro del repositorio

El programa está en la carpeta **[ejecutable/](ejecutable/)** de la rama
**FranFran**. Al clonar o actualizar esa rama, abrir
**[ejecutable/DiffieHellman-TP.exe](ejecutable/DiffieHellman-TP.exe)** con doble clic.
Es un archivo único para Windows
de 64 bits: incluye Python, librerías, personajes y configuración de Render.
No requiere ZIP, carpeta `_internal` ni instalar Python para jugar.

### Generar el ejecutable manualmente

Con Python **3.14 de 64 bits** instalado, abrir `generar_exe.cmd` desde la raíz
del repositorio. Crea `.venv-build`, instala las dependencias de compilación y
genera el exe único dentro de una carpeta nueva de `dist/`. También se puede
ejecutar desde PowerShell:

```powershell
.\generar_exe.cmd
```

Desde Windows de 64 bits, con el entorno virtual activado:

```powershell
python -m pip install -r requirements-build.txt
python herramientas/empaquetar_windows.py
```

Se genera `dist/<fecha>/DiffieHellman-TP.exe` y su archivo de verificación SHA-256.
La configuración y documentación se incluyen dentro del ejecutable. Si se
necesita otro servidor, se puede ingresar su dirección en la pantalla o dejar
un `configuracion.json` junto al exe como reemplazo opcional.

El formato anterior de carpeta y ZIP sigue disponible con
`python herramientas/empaquetar_windows.py --formato carpeta`.

Para ejecutar `main.py` desde el código, instalar `requirements.txt` y usar los
recursos de la misma rama. El entorno de referencia usa Python 3.14. Las imágenes
están en `assets/personajes-arcade.png`. La carga fuerza el formato PNG para
que Tk 9 no confunda el icono SVG de los metadatos con los personajes.

## Preguntas para el profe

1. "Sin bibliotecas" ¿incluye los enteros grandes nativos de Python (`int` de precisión arbitraria) o hay que implementar la aritmética de números grandes también?
2. ¿Se puede usar `random` o `secrets` para generar la clave privada y los candidatos a primo, o también hay que hacer un generador propio (por ejemplo, un LCG)?
3. ¿La GUI puede usar una biblioteca externa (CustomTkinter)? Suponemos que sí, porque la restricción habla de "la matemática modular".
4. ¿Se puede usar `socket` de la biblioteca estándar para el objetivo secundario? (Implementado así en `CanalSocket`.)
5. ¿Qué tamaño de `p` esperan ver en la demo (64, 256, 2048 bits)? Esto define cuánto hay que optimizar Miller-Rabin.
6. ¿La exposición dura 15 o 25 minutos? El instructivo dice las dos cosas.
