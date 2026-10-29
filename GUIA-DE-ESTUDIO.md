# Guía de estudio · TP Final Diffie-Hellman

Todo lo que hay que entender para defender el TP en el oral: qué pide la consigna, la matemática, qué hace cada función del código y las preguntas que nos pueden hacer.

**Cómo leerla:** las secciones 1 a 4 son los conceptos, la 5 es la matemática del código (la parte más importante) y la 9 son las preguntas probables. Si tienen poco tiempo, lean 2, 3, 5 y 9.

---

## 1. Qué pide la consigna

> **Objetivo.** Crear una aplicación que implemente el protocolo de establecimiento de claves Diffie-Hellman utilizando archivos de texto para el intercambio de información entre las partes involucradas. La implementación del protocolo (específicamente, la matemática modular) debe ser hecha desde cero, sin utilizar bibliotecas.
>
> **Objetivo secundario.** Realizar el intercambio de información entre "dos computadoras distintas" (puede ser una máquina virtual), utilizando sockets.

Son tres cosas que tenemos que poder mostrar:

| Pide | Dónde está en nuestro código |
|---|---|
| Diffie-Hellman | `protocolo/sesion.py` (clase `Participante`) |
| Matemática modular sin bibliotecas | `core/aritmetica.py` |
| Intercambio por archivos de texto | `CanalArchivo` en `transporte/canal.py` |
| Dos computadoras con sockets | `CanalSocket` en `transporte/canal.py` |

---

## 2. La idea en un minuto

Alice y Bob quieren hablar en secreto, pero nunca se vieron para acordar una contraseña, y **todo lo que se dicen lo escucha Eve**. Diffie-Hellman les permite **generar** una clave común sin que esa clave viaje nunca por el canal.

La analogía de la pintura:

1. Acuerdan en público un color base (amarillo).
2. Cada uno le mezcla un color **secreto** propio y le manda la mezcla al otro.
3. Cada uno le agrega su color secreto a la mezcla que recibió. Los dos terminan con **el mismo color final**.
4. Eve vio el amarillo y las dos mezclas, pero "separar" una mezcla es muy difícil.

**Diffie-Hellman no manda un mensaje secreto.** Solo sirve para acordar la clave. Después esa clave (K) se usa para cifrar la conversación con otro algoritmo, como el cifrado en bloque del TP2. Nuestro TP llega hasta acordar K.

---

## 3. El protocolo paso a paso

Ejemplo con números chicos (son los mismos que usa la app y la presentación):

| Paso | Alice | Por el canal (Eve lo ve) | Bob |
|---|---|---|---|
| 1. Parámetros públicos | | **p = 23**, **g = 5** | |
| 2. Cada uno elige su privada | **a = 6** (secreto) | | **b = 15** (secreto) |
| 3. Calculan su pública | A = 5⁶ mod 23 = **8** | A = 8 → | |
| | | ← B = 19 | B = 5¹⁵ mod 23 = **19** |
| 4. Calculan el secreto | K = 19⁶ mod 23 = **2** | | K = 8¹⁵ mod 23 = **2** |

**Por qué los dos llegan al mismo K:**

```
K de Alice = B^a = (g^b)^a = g^(a·b)  (mod p)
K de Bob   = A^b = (g^a)^b = g^(a·b)  (mod p)
```

El 2 **no lo eligió nadie** y **nunca pasó por el canal**. Eve vio 23, 5, 8 y 19, nada más.

### Qué es público y qué es secreto

| Público (viaja por el canal) | Secreto (nunca sale de cada PC) |
|---|---|
| p, g, A, B | a, b, K |

`g = 5` no es un mensaje que haya que "recuperar": es una regla del juego que conoce todo el mundo.

---

## 4. Por qué es seguro: el logaritmo discreto

- **Ir para adelante es fácil:** con g, a y p, calcular A = gᵃ mod p es rapidísimo gracias a la exponenciación rápida (sección 5.1).
- **Ir para atrás es difícil:** con g, p y A, encontrar el `a` tal que gᵃ ≡ A (mod p) se llama **logaritmo discreto**. No se conoce un método eficiente: básicamente hay que probar a = 1, 2, 3…

Hacen falta en promedio unos **p/2 intentos**:

| Tamaño de p | Intentos esperados |
|---|---|
| p = 23 | ≈ 11 (en el ejemplo alcanzan 6) |
| p de 64 bits (lo que genera la app) | ≈ 10¹⁹ |
| p de 2048 bits (lo que se usa en la vida real) | ≈ 10⁶¹⁶ |

En la app, la pantalla de Eve hace exactamente esto: con p = 23 encuentra la privada al instante, y con un p de 64 bits llega al límite de intentos sin encontrarla.

---

## 5. La matemática del código (lo más importante)

Todo está en **`core/aritmetica.py`**. Las funciones solo usan suma, multiplicación, división entera y resto (`%`). **La interfaz nunca hace cuentas:** siempre llama a estas funciones.

| Lo que haría una biblioteca | Nuestra función | Para qué |
|---|---|---|
| `pow(g, a, p)` | `potencia_modular` / `mod_pow` | Calcular A, B y K |
| `sympy.isprime(n)` | `es_primo` (Miller-Rabin) | Verificar que p es primo |
| `dh.generate_parameters(...)` | `generar_parametros` | Buscar un primo seguro p = 2q + 1 |
| `sympy.primitive_root(p)` | `encontrar_generador` | Elegir g |
| `sympy.discrete_log(...)` | `log_discreto_fuerza_bruta` | El ataque de Eve |

### 5.1 `potencia_modular(base, exp, mod)`: exponenciación rápida

**Reemplaza:** `pow(g, a, p)`. Es la función más importante: con ella se calculan A, B y K.

**Idea:** en vez de multiplicar `g` por sí mismo `a` veces, recorre el exponente **en binario**.

```python
resultado = 1
base = base % mod
while exp > 0:
    if exp & 1:                           # el último bit es 1 (exp impar)
        resultado = (resultado * base) % mod
    exp = exp >> 1                        # dividir por 2 (correr un bit)
    base = (base * base) % mod            # elevar la base al cuadrado
return resultado
```

**Ejemplo 5⁶ mod 23** (6 en binario es 110):

| exp al empezar | bit | resultado | base al empezar |
|---|---|---|---|
| 6 | 0 | queda en 1 | 5 |
| 3 | 1 | 1 · 2 = 2 | 2 |
| 1 | 1 | 2 · 4 = 8 | 4 |
| 0 | — | **8** ✔ | 16 |

**Para decir en el oral:** *"Hace unas log₂(exp) vueltas. Con un exponente de 2048 bits son unas 2048 vueltas, en lugar de un número de 616 cifras de multiplicaciones. Y como reducimos mod p en cada paso, los números nunca crecen."*

`mod_pow` hace la misma cuenta, pero además guarda cada vuelta para mostrarla en el panel "Paso a paso" de la app.

### 5.2 `es_primo(n)`: test de Miller-Rabin

**Reemplaza:** `sympy.isprime(n)`. Sirve para generar p y para validar el p que llega por el canal.

**Por qué no dividir por todos:** con un número de 64 bits, probar divisores hasta su raíz llevaría muchísimo tiempo.

**Pasos:**
1. Descartar los divisibles por primos chicos (2 a 37).
2. Escribir n − 1 = 2ʳ · d, con d impar.
3. Elegir un `a` al azar y calcular x = aᵈ mod n (con nuestra exponenciación rápida).
4. Si x = 1 o x = n − 1, la ronda pasa.
5. Si no, elevar x al cuadrado hasta r − 1 veces buscando n − 1. Si nunca aparece, **n es compuesto, seguro**.

**Por qué funciona:** si n es primo, vale Fermat (aⁿ⁻¹ ≡ 1) y las únicas raíces cuadradas de 1 mod n son 1 y n − 1. Un número compuesto "se delata" en alguna de esas cuentas.

**Cuánto confiar:** cada ronda deja pasar un compuesto con probabilidad ≤ 1/4. Hacemos 20 rondas, así que el error es ≤ (1/4)²⁰ ≈ 10⁻¹².

**Ejemplo con n = 23:** 22 = 2¹ · 11, o sea r = 1 y d = 11. Con a = 2: 2¹¹ mod 23 = 1, así que la ronda pasa.

### 5.3 `generar_parametros(bits)`: primo seguro

**Reemplaza:** `dh.generate_parameters(...)` de la librería `cryptography`.

**Qué hace:** sortea un `q` de la cantidad de bits pedida y prueba con Miller-Rabin que **q** y **p = 2q + 1** sean los dos primos. Si no, sortea otro. Después busca el generador (5.4).

**Por qué un primo seguro:** así el grupo tiene p − 1 = 2q elementos, y verificar un generador se vuelve muy fácil.

### 5.4 `encontrar_generador(p)`: el generador g

**Reemplaza:** `sympy.primitive_root(p)`.

**Qué es un generador:** un `g` cuyas potencias g¹, g², g³… recorren **todos** los números de 1 a p − 1.

**Cómo lo encuentra:** prueba g = 2, 3, 4… y se queda con el primero que cumple **g² ≠ 1 y g^q ≠ 1 (mod p)**.

**Por qué alcanza con eso:** por el **teorema de Lagrange**, el orden de g divide al tamaño del grupo (2q), así que solo puede ser 1, 2, q o 2q. Si g² ≠ 1 y g^q ≠ 1, el orden no es 1, 2 ni q: es 2q, y g genera todo el grupo.

**Ejemplo con p = 23 (q = 11):**

| g | g² mod 23 | g¹¹ mod 23 | ¿Genera? |
|---|---|---|---|
| 2 | 4 | 1 | No (orden 11) |
| 3 | 9 | 1 | No |
| 4 | 16 | 1 | No |
| **5** | 2 | 22 | **Sí** |

`encontrar_generador(23)` devuelve **5**. Por eso el ejemplo usa g = 5.

### 5.5 `log_discreto_fuerza_bruta(g, objetivo, p, max_intentos)`: el ataque de Eve

**Reemplaza:** `sympy.discrete_log(...)`.

**Qué hace:** multiplica por g una y otra vez (g¹, g², g³…, reduciendo mod p) hasta dar con la pública. El exponente donde la encuentra es la clave privada. Tiene un tope de intentos y se puede cancelar desde la interfaz.

**Para qué está:** para **demostrar** que con p chico Eve gana enseguida y con p grande no tiene chance.

### 5.6 `generar_privada(p)`: la clave privada

Elige un número al azar entre 2 y p − 2.

> ⚠️ **Ojo:** esta función y las de primos usan `random` de Python para sortear números. No hace ninguna cuenta modular, solo elige al azar. Si el profe pregunta, la respuesta es esa. La presentación lo aclara en una línea.

---

## 6. Cómo viajan los mensajes

Todos los modos mandan **el mismo formato de texto plano**:

```
de=Alice
para=Bob
tipo=PARAMETROS
p=23
g=5
```

Los tipos son `PARAMETROS` (solo lo manda Alice, con p y g) y `PUBLICA` (A o B). **Solo viajan datos públicos.**

### 6.1 Por archivos .txt (objetivo principal): `CanalArchivo`

- Las dos partes usan una **carpeta compartida** y un mismo código de **sesión**.
- Cada envío crea un archivo distinto (`Alice_a_Bob_<orden>_<id>.txt`), así no se pisan.
- Primero se escribe un `.tmp` y después se **renombra** a `.txt`. Renombrar es atómico: nunca se lee un archivo a medio escribir.
- El que recibe lo **valida** (remitente, tipo, que los datos sean enteros). Recién después de procesarlo lo **confirma**, y ahí se borra. Si es inválido, va a la carpeta `rechazados/`.
- La app revisa la carpeta cada 500 ms (recepción automática).

### 6.2 Por sockets entre dos PCs (objetivo secundario): `CanalSocket`

- **Bob es el servidor:** abre un socket TCP y escucha en un puerto (5000 por defecto). La app le muestra su IP en la red.
- **Alice es el cliente:** se conecta a la IP de Bob. Si Bob todavía no está escuchando, reintenta cada segundo.
- Las dos PCs tienen que estar **en la misma red** (el mismo WiFi, o una PC y una máquina virtual en modo *bridge*).
- Viaja el mismo texto, con **una línea vacía al final** de cada mensaje. Hace falta porque TCP entrega un chorro de bytes, no mensajes separados.
- Un hilo aparte escucha la red, así la ventana no se congela.
- Usa el módulo `socket`, que viene con Python.
- La primera vez, Windows puede preguntarle a Bob por el firewall: hay que permitirlo en **redes privadas**.

> 📌 Esto está en la rama **`sockets-red-local`**, que sale de `FranFran`. Hay que revisarla y unirla antes de la entrega.

### 6.3 Salas por Internet (extra, no lo pide el TP)

Francisco armó un modo donde las dos PCs se conectan a un servidor publicado en Render, usando WebSocket. Funciona entre casas distintas y es lindo para mostrar, pero **no es el objetivo 2**: hay un servidor en el medio y usa librerías externas (`websockets`, `fastapi`). Presentarlo como extra.

---

## 7. Mapa del código

```
main.py                    arranca la app
core/aritmetica.py         ★ LA MATEMÁTICA (sección 5)
protocolo/sesion.py        ★ Participante: guarda p, g, privada, pública, K y valida
transporte/canal.py        ★ Mensaje, CanalArchivo, CanalSocket
transporte/internet.py     cliente WebSocket de las salas (extra)
servidor/                  servidor de salas en Render (extra)
gui/                       la interfaz: ventanas, escena arcade, consola
tests/                     pruebas automáticas
```

**Regla de capas:** `gui → protocolo → core` y `gui → transporte`. La interfaz no sabe hacer cuentas ni sabe por dónde viajan los mensajes; por eso se puede cambiar archivo por socket sin tocar el protocolo.

### Validaciones de `Participante` (pueden preguntar)

- `p` tiene que ser primo y mayor que 3.
- `g` tiene que cumplir 1 < g < p − 1.
- La privada tiene que estar entre 2 y p − 2.
- **La pública recibida tiene que estar entre 2 y p − 2.** Si alguien manda 0, 1 o p − 1, el secreto sería trivial (siempre 0, 1 o ±1), así que se rechaza.

---

## 8. Cómo correrla y guion de demo

```bash
pip install -r requirements.txt
python main.py
```

**Guion sugerido:**

1. **Modo local** con p = 23, g = 5 y privadas 6 y 15. Se ve viajar cada paquete y la copia que baja a Eve. Los dos llegan a **K = 2**.
2. **Ataque de Eve** sobre esos números: encuentra a = 6 al instante.
3. **Generar p y g de 64 bits** y repetir el ataque: Eve llega al límite de intentos.
4. **Modo red → Archivos · Sockets**, con dos instancias y la misma carpeta: intercambio por `.txt`.
5. **Sockets TCP** entre dos PCs: Bob toca Conectar y le pasa su IP a Alice. Repetir y mostrar que K coincide.

**Probar los sockets antes del día del oral, en el mismo WiFi donde vamos a presentar.** Las redes de la facultad a veces bloquean conexiones entre equipos. Plan B: una PC y una máquina virtual, o dos instancias en la misma PC con la IP `127.0.0.1`.

---

## 9. Preguntas probables del oral

**¿Diffie-Hellman cifra el mensaje?**
No. Solo acuerda una clave compartida (K). Esa clave se usa después en un cifrado simétrico.

**¿Qué es público y qué es secreto?**
Públicos: p, g, A y B. Secretos: las privadas a y b, y K. Nunca viajan las privadas ni K.

**¿Por qué Alice y Bob obtienen el mismo K?**
Porque (gᵇ)ᵃ = (gᵃ)ᵇ = gᵃᵇ mod p. La exponenciación conmuta en el exponente.

**¿Por qué Eve no puede calcular K?**
Necesitaría a o b, o sea resolver un logaritmo discreto. No hay un método eficiente conocido; por fuerza bruta lleva unos p/2 intentos.

**¿Por qué no usaron `pow()` de Python?**
Porque la consigna pide la matemática modular desde cero. Implementamos la exponenciación rápida (square-and-multiply) en `potencia_modular`.

**¿Cuánto cuesta la exponenciación rápida?**
Unas log₂(exponente) vueltas, con hasta dos multiplicaciones modulares por vuelta: O(log e).

**¿Por qué Miller-Rabin y no probar divisores?**
Porque probar divisores hasta √n es inviable para números grandes. Miller-Rabin es probabilístico, pero con 20 rondas el error es menor a 10⁻¹².

**¿Qué es un primo seguro y para qué sirve?**
Es un p = 2q + 1 con q primo. El grupo tiene 2q elementos, así que el orden de cualquier g solo puede ser 1, 2, q o 2q (Lagrange), y verificar un generador se reduce a dos cuentas.

**¿Qué es un generador?**
Un g cuyas potencias recorren todos los valores de 1 a p − 1. Si g no genera todo el grupo, las claves quedan en un subgrupo más chico y es más fácil atacarlas.

**¿Por qué rechazan una pública igual a 0, 1 o p − 1?**
Porque harían el secreto trivial y predecible. Es una validación de seguridad.

**¿Qué pasa si Eve, en vez de escuchar, modifica los mensajes?**
Es el ataque *man-in-the-middle*: Eve se hace pasar por Bob ante Alice y por Alice ante Bob, y acuerda una clave distinta con cada uno. Diffie-Hellman "puro" **no autentica** a las partes, así que es vulnerable. En la práctica se combina con firmas o certificados. Nuestro TP modela a Eve como espía pasiva.

**¿Qué tamaño de p usan?**
La app genera p de 64 bits para que la demo sea rápida. En la vida real se usan 2048 bits o más.

**¿Los enteros grandes de Python cuentan como biblioteca?**
No. El `int` de precisión arbitraria es el tipo nativo del lenguaje, no una biblioteca. Todas las operaciones modulares (potencia, primalidad, generador, logaritmo) las programamos nosotros.

**¿Por qué una línea vacía al final de cada mensaje por socket?**
Porque TCP entrega bytes, no mensajes: un mensaje puede llegar partido o dos pueden llegar juntos. La línea vacía marca dónde termina cada uno.

**¿Por qué escriben un `.tmp` y lo renombran?**
Para que el otro nunca lea un archivo a medio escribir. Renombrar es una operación atómica.

---

## 10. Puntos a tener claros (para que no nos agarren)

- **`random`:** se usa para sortear candidatos a primo y privadas, no para ninguna cuenta. Si quieren cero discusión, se reemplaza por un generador propio (un LCG son unas 10 líneas).
- **Interfaz con `customtkinter`:** es una librería externa, pero la consigna restringe la matemática, no la interfaz.
- **Salas por Internet:** son un extra; el objetivo 2 lo cumple `CanalSocket`.
- **Ramas:** `FranFran` tiene todo lo de la app y es la que usa el servidor de Render (no hacer push sin avisar). `sockets-red-local` agrega los sockets. Falta unir todo en `main` antes de entregar.

---

## 11. Glosario

| Término | Qué es |
|---|---|
| **a mod p** | El resto de dividir a por p |
| **a ≡ b (mod p)** | a y b dan el mismo resto al dividir por p |
| **Primo seguro** | p = 2q + 1 con q también primo |
| **Generador** | g cuyas potencias recorren todo el grupo |
| **Orden de g** | El menor k > 0 con gᵏ ≡ 1 (mod p) |
| **Teorema de Lagrange** | El orden de un elemento divide al tamaño del grupo |
| **Pequeño teorema de Fermat** | Si p es primo y no divide a a, aᵖ⁻¹ ≡ 1 (mod p) |
| **Logaritmo discreto** | Dado gˣ ≡ A (mod p), encontrar x |
| **Exponenciación rápida** | Calcular gᵉ mod p en log₂(e) pasos usando el binario de e |
| **Miller-Rabin** | Test probabilístico de primalidad |
| **Man-in-the-middle** | Atacante que se mete en el medio y modifica los mensajes |
| **Socket TCP** | Conexión directa entre dos programas por la red |
