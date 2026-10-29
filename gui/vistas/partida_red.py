"""La escena compartida con un único participante controlable en cada PC."""
from gui import tema
from gui.vistas.modo_local import VistaModoLocal
from protocolo.sesion import ErrorProtocolo, Participante
from transporte.canal import ErrorCanal, Mensaje


class VistaPartidaRed(VistaModoLocal):
    def __init__(self, master, cliente, sala, rol, partida, al_salir):
        self._red_lista = False
        self.cliente, self.sala, self.rol, self.partida = cliente, sala, rol, partida
        self.al_salir = al_salir
        self._pendiente = False
        self._secuencia = 0
        super().__init__(master, lambda _datos: None, rol_local=rol)
        self.yo = self.alice if rol == "Alice" else self.bob
        self.otro = self.bob if rol == "Alice" else self.alice
        self.tarjeta = self.t_alice if rol == "Alice" else self.t_bob
        self._red_lista = True
        self.lbl_titulo.configure(text=f"Sala {sala} · Sos {rol}")
        self.btn_reiniciar.configure(text="Salir", command=al_salir)
        self._log(f"Conectado como {rol}. Solo esta PC elige su privada y deriva su secreto.")
        self._refrescar()

    def reiniciar(self, *args, **kw):
        self.al_salir()

    def _generar_parametros(self):
        if self.rol == "Alice" and self.yo.p is None and not self._pendiente:
            super()._generar_parametros()

    def _publicar_parametros(self):
        try:
            if self.rol != "Alice":
                raise ErrorProtocolo("Alice es quien publica los parámetros.")
            p, g = int(self.entrada_p.get()), int(self.entrada_g.get())
            candidato = Participante("Alice")
            candidato.establecer_parametros(p, g)
            if self.yo.p is not None and (self.yo.p, self.yo.g) != (p, g):
                raise ErrorProtocolo("Para cambiar los parámetros, creá una sala nueva.")
            self._publicar("PARAMETROS", {"p": p, "g": g})
        except (ValueError, ErrorProtocolo, ErrorCanal) as e:
            self.mostrar_error(str(e))

    def _enviar(self, quien):
        if quien is not self.yo:
            raise ErrorProtocolo("Solo podés enviar la pública de tu personaje.")
        if quien.publica is None:
            raise ErrorProtocolo("Primero calculá tu clave pública.")
        self._publicar("PUBLICA", {"A" if self.rol == "Alice" else "B": quien.publica})

    def _publicar(self, tipo, datos):
        if self._pendiente:
            raise ErrorProtocolo("Esperá la confirmación del envío anterior.")
        if tipo == "PARAMETROS":
            # Una generación iniciada antes del envío no debe reemplazar los
            # campos de los parámetros que finalmente se publicaron.
            self._generacion += 1
            self.btn_generar.configure(text="Generar p y g")
        self.cliente.enviar("publicar", partida=self.partida, tipo=tipo,
                            datos={k: str(v) for k, v in datos.items()})
        self._pendiente = True
        self._refrescar()

    def aplicar_mensaje(self, evento):
        if evento.get("partida") != self.partida:
            return
        secuencia = evento["secuencia"]
        if type(secuencia) is not int:
            raise ErrorProtocolo("La secuencia del servidor no es válida.")
        if secuencia <= self._secuencia:
            return
        if secuencia != self._secuencia+1:
            raise ErrorProtocolo("Se interrumpió el orden del intercambio. Volvé a ingresar a la sala.")
        datos = evento["datos"]
        if not isinstance(datos, dict) or any(not isinstance(v, str) or len(v) > 1234 or
                                              not v.isascii() or not v.isdecimal() for v in datos.values()):
            raise ErrorProtocolo("El servidor envió datos públicos inválidos.")
        m = Mensaje(evento["remitente"], evento["destinatario"], evento["tipo"],
                    {k: int(v) for k, v in datos.items()})
        m.validar()
        if m.tipo == "PARAMETROS":
            p, g = m.datos["p"], m.datos["g"]
            for actor in (self.alice, self.bob):
                if actor.p is None:
                    actor.establecer_parametros(p, g)
                elif (actor.p, actor.g) != (p, g):
                    raise ErrorProtocolo("El servidor cambió los parámetros de esta partida.")
            for entrada, valor in ((self.entrada_p, p), (self.entrada_g, g)):
                entrada.configure(state="normal")
                entrada.delete(0, "end")
                entrada.insert(0, str(valor))
            self.lbl_param.configure(text="Parámetros recibidos del canal. Elegí tu privada.", text_color=tema.OK)
        else:
            valor = next(iter(m.datos.values()))
            emisor = self.alice if m.remitente == "Alice" else self.bob
            receptor = self.bob if m.remitente == "Alice" else self.alice
            receptor.recibir_publica(valor)
            if emisor is self.otro:
                emisor.publica = valor
        self._secuencia = secuencia
        if m.remitente == self.rol:
            self._pendiente = False
        self._al_pasar_mensaje(m)
        self._refrescar()

    def mostrar_error(self, texto):
        self._pendiente = False
        self.lbl_param.configure(text=texto, text_color=tema.EVE)
        self._log(f"Error: {texto}")
        self._refrescar()

    def _refrescar(self):
        super()._refrescar()
        if not self._red_lista:
            return
        self.tarjeta.bloquear(self._pendiente or self.escena.en_animacion)
        habilitar = self.rol == "Alice" and self.yo.p is None and not self._pendiente
        for control in (self.entrada_p, self.entrada_g, self.btn_generar, self.sel_bits):
            control.configure(state="normal" if habilitar else "disabled")
        self.btn_publicar.configure(state="normal" if habilitar else "disabled")
        if self._pendiente:
            self.lbl_escena.configure(text="Esperando la confirmación del servidor…")
        elif not self.escena.en_animacion:
            self.lbl_escena.configure(text=f"Sos {self.rol}. {self.otro.nombre} controla su personaje desde la otra PC.")
        if self.yo.secreto is not None:
            self.banner.configure(text="Tu secreto K está calculado. Comparalo con el de la otra persona.",
                                   fg_color="#16392a", text_color=tema.OK, height=28)
