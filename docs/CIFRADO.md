# Funciones de cifrado de mensajes

La extensión permite enviar textos cifrados después del acuerdo de K, desde
la pestaña **Mensajes**. Está conectada al modo local, las salas de Internet,
los archivos y los sockets TCP. La matemática y el formato siguen separados
de Tk y del transporte.

La aritmética de Diffie-Hellman conserva su implementación propia en
`core/aritmetica.py`. La extensión simétrica usa `cryptography==50.0.2` para
HKDF-SHA256 y AES-256-GCM. Instalar las dependencias con:

```powershell
python -m pip install -r requirements.txt
```

## Separación de responsabilidades

| Módulo | Responsabilidad | API |
|---|---|---|
| `core/clave_simetrica.py` | Convertir K en una clave de 32 bytes mediante HKDF-SHA256 | `derivar_clave(secreto, sal, contexto=...)` |
| `core/cifrado.py` | Cifrar bytes y verificar su autenticidad al descifrar | `cifrar_bytes()` y `descifrar_bytes()` |
| `protocolo/mensajes_cifrados.py` | Manejar texto UTF-8, generar sal/nonce y serializar un sobre público | `cifrar_mensaje()`, `descifrar_mensaje()` y `MensajeCifrado` |
| `protocolo/conversacion.py` | Vincular sobres a un intercambio y mantener las lecturas de cada actor | `Conversacion` |
| `gui/mensajes.py` | Redacción, recepción y visualización de lo interceptado por Eve | `PanelMensajes` |

La interfaz usa `Conversacion`, que llama a las funciones de mensajes. El módulo de bytes queda
disponible para pruebas u otros formatos; allí el llamador debe garantizar que
no se repita el mismo par clave/nonce. `cifrar_mensaje()` genera una sal y un
nonce aleatorios en cada llamada con `secrets.token_bytes()`.

## Uso desde Alice y Bob

```python
from protocolo.mensajes_cifrados import (
    MensajeCifrado, cifrar_mensaje, descifrar_mensaje,
)

# En la GUI son alice.secreto y bob.secreto, calculados por DH.
k_alice = 2
k_bob = 2
contexto = b"sesion-demo:Alice->Bob"

# Alice cifra. El canal recibe solamente esta cadena JSON.
mensaje = cifrar_mensaje("Hola, Bob", k_alice, contexto=contexto)
por_el_canal = mensaje.a_texto()

# Bob valida el sobre, autentica y recupera el texto con su propio K.
recibido = MensajeCifrado.desde_texto(por_el_canal)
texto = descifrar_mensaje(recibido, k_bob, contexto=contexto)
assert texto == "Hola, Bob"
```

Eve puede conservar `por_el_canal` y los datos públicos de DH. Si el ataque
existente encuentra una privada y permite reconstruir K, puede llamar a la
misma función `descifrar_mensaje()` con ese K y el contexto público. La prueba
de integración cubre el recorrido completo, sin darle la privada a Eve.

El contexto es un dato público asociado al mensaje: puede identificar la
sesión, el remitente y el destinatario. Debe reconstruirse igual en ambos
extremos. Un contexto diferente hace fallar la autenticación. El valor vacío
permite usar las funciones de forma aislada. `Conversacion` construye un
contexto con el identificador del intercambio, la huella SHA-256 de p/g/A/B,
los roles de origen/destino y el identificador único del mensaje.

## Qué viaja en el sobre

El JSON contiene exactamente estos campos:

| Campo | Contenido |
|---|---|
| `version` | Entero `1` |
| `algoritmo` | `AES-256-GCM` |
| `sal` | 32 bytes públicos, codificados en Base64 |
| `nonce` | 12 bytes públicos, codificados en Base64 |
| `texto_cifrado` | Texto cifrado y etiqueta de autenticación de 16 bytes, en Base64 |

K y la clave AES permanecen en el llamador y no forman parte del sobre. La
clase tampoco guarda las privadas de DH ni el texto original. El JSON ocupa
una sola línea ASCII. Los canales aceptan el tipo `CIFRADO`, con `id` y
`sobre`; el identificador público `intercambio` acompaña al mensaje. En las
salas se usa la `partida` asignada por el servidor. En archivos y TCP, Alice
genera el identificador y lo envía junto con p y g.

## Uso en la GUI

1. Publicar p/g, elegir las privadas y enviar las dos públicas A/B.
2. Cada participante deriva su K con su propio botón.
3. Abrir **Mensajes**. En modo local se elige Alice o Bob para redactar;
   en red solo aparece el personaje de esta instancia.
4. Escribir y tocar **Cifrar y enviar**. El destinatario ve el contenido
   cifrado en **Conversación**, todavía pendiente de descifrado.
5. En local, elegir el rol del destinatario (por ejemplo Bob). Con K derivada,
   pulsar **Descifrar mensaje** para recuperar el primer mensaje pendiente.
   Cada clic procesa uno; tener K o recibir el sobre no lo descifra por sí solo.
6. En **Eve / canal**, observar una muestra del cifrado o copiar el sobre
   completo del último mensaje. **Intentar ataque** usa el mismo límite
   configurado en la tarjeta de Eve. Si reconstruye K, muestra el texto.

La consola relata cuándo cada participante cifra y cuándo el destinatario
descifra y verifica el mensaje. Eve tiene su propio diálogo en la escena:
se pregunta qué significa el cifrado y, cuando realmente logra descifrarlo,
anuncia «¡Lo descifré!» con una vista breve del texto recuperado. Los mensajes
largos se abrevían en el globo y se conservan completos en la pestaña Mensajes.

En las salas, el emisor conserva su texto al recibir la confirmación del
servidor. El servidor valida y reenvía el sobre sin obtener ninguna clave ni
texto original. Un servidor anterior sigue admitiendo el intercambio DH,
pero la GUI deshabilita el chat hasta que publique la capacidad
`mensajes-cifrados-v1`. Ambas instancias de archivos/TCP deben usar esta versión.
Los cambios de datos públicos o el reinicio vacían el historial de la GUI.
En local, la conversación sigue el rol elegido: el texto que Alice escribió
solo se presenta como recibido por Bob después de pulsar **Descifrar mensaje**.
El botón se habilita con K y un mensaje pendiente. Una autenticación fallida
muestra un error; cambiar K permite volver a intentarlo.

## Límites y errores

- El texto admite hasta 8192 bytes UTF-8, incluido el mensaje vacío. El límite
  se mide en bytes: letras acentuadas y emojis pueden ocupar varios bytes.
- El sobre admite hasta 16 KB. Se rechazan campos extra o repetidos,
  versiones o algoritmos desconocidos, Base64 no canónico y tamaños inválidos.
- K debe ser un entero positivo de hasta 4096 bits. No se convierten cadenas,
  números con decimales o booleanos en secretos de forma implícita.
- `ErrorMensajeCifrado` indica un texto o sobre inválido.
- `ErrorAutenticacion`, definido en `core/cifrado.py`, indica que la clave,
  el contexto o los datos no coinciden. Nunca se devuelve texto parcial.

Ambos errores de mensajes/autenticación heredan de `ErrorCifrado`, que hereda
de `ValueError`. La validación de la derivación también usa `ValueError`.

El ejemplo K=2 sigue siendo débil y deliberadamente atacable por Eve. Derivar
32 bytes no convierte un secreto pequeño en uno con 256 bits de entropía.
La autenticación del cifrado verifica los datos con la clave compartida; no
añade autenticación de identidad al intercambio DH. `Conversacion` evita
duplicados por id y rechaza un mismo id con otro contenido. El servidor de
salas rechaza ids ya usados. Se admiten hasta 200 mensajes por intercambio;
el historial es temporal y no se guarda al cerrar o reiniciar la sesión.

## Verificación

```powershell
python -m unittest discover -s tests -p test_cifrado.py -v
python -m unittest discover -s tests -v
```

Se cubre un vector externo de HKDF del RFC 5869, recuperación exacta de UTF-8,
aleatoriedad por envío, claves/contextos incorrectos, sobres modificados,
límites, formato inválido y el recorrido de Alice, Bob y Eve con DH real.
Las pruebas de GUI cubren envío, recepción, K pendiente y lectura de Eve;
incluyen dos clientes contra un servidor local y un intercambio TCP real.

Referencias:

- [HKDF-SHA256 y vectores del RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)
- [HKDF en cryptography](https://cryptography.io/en/50.0.2/hazmat/primitives/key-derivation-functions/#hkdf)
- [AES-GCM en cryptography](https://cryptography.io/en/50.0.2/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM)
