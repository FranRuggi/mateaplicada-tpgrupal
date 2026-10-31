# Ejecutable de Windows

Abrí **DiffieHellman-TP.exe** con doble clic. Al clonar o actualizar la rama
**FranFran**, el programa ya está disponible en esta carpeta.

Es un archivo único para Windows de 64 bits. Incluye Python, librerías,
personajes y la configuración de Render. Se puede copiar y compartir solo
el `.exe`; no necesita ZIP ni carpetas adicionales.

Para generar otra compilación, abrir [generar_exe.cmd](../generar_exe.cmd)
desde la raíz del repositorio, con Python 3.14 de 64 bits instalado. El
generador deja el resultado en `dist/<fecha>/`. Para actualizar esta copia
del repo, reemplazar el exe y su archivo `.sha256.txt` por los recién generados.

Esta copia se compiló desde la revisión
`6ee96869dfe218891dd6e66dc7ced9f2e84f5683`.

Incluye la corrección de lectura PNG: Tk 9 ya no debe mostrar el logo SVG de
los metadatos en lugar de Alice, Eve y Bob. Cerrar cualquier instancia anterior
antes de actualizar el ejecutable y volver a abrir esta copia de la carpeta.

Incluye `cryptography` para cifrar y descifrar mensajes. Los errores de
dependencias se muestran dentro de la app y en su consola; un intento fallido
conserva el borrador o el mensaje recibido pendiente de descifrar.
