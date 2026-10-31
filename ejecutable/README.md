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
`cb1e27ec3b88e1f8d7c3367541cd579afe7ea22f`.

Incluye la corrección de lectura PNG: Tk 9 ya no debe mostrar el logo SVG de
los metadatos en lugar de Alice, Eve y Bob. Cerrar cualquier instancia anterior
antes de actualizar el ejecutable y volver a abrir esta copia de la carpeta.
