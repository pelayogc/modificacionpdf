# Instrucciones del proyecto

Si hay algun aprendizaje derivado de un error, incorporarlo en este `AGENTS.md` para que no vuelva a suceder.

Coolify esta en `http://10.164.18.45:8000/`.

## Trabajo en paralelo y consistencia

- Antes de modificar nada, ejecutar `git status --short --branch` y revisar si hay cambios locales no propios.
- No modificar, formatear, revertir, mover ni borrar cambios locales ajenos.
- Si hay cambios ajenos en archivos que necesito tocar, leerlos primero y trabajar encima sin revertirlos. Si no es claro como integrarlos, preguntar.
- Stagear solo los archivos/lineas propios. No usar `git add .` salvo que se haya comprobado que todo el diff pertenece a esta tarea.
- Antes de commit, ejecutar `git diff --cached` y verificar que el commit contiene solo cambios de la tarea actual.
- Antes de push, ejecutar `git status --short --branch` y confirmar que no quedan cambios propios sin commitear ni cambios ajenos incluidos accidentalmente.
- No hacer `git reset --hard`, `git checkout --`, `git restore`, rebase, squash, force-push ni operaciones destructivas sin instruccion explicita.
- Si se trabaja en paralelo, usar ramas separadas por tarea con prefijo `codex/`, salvo que el usuario indique otra rama.
- Si la tarea requiere despliegue, desplegar solo despues de commit y push correctos, y mencionar el commit desplegado.
- Si el repositorio tiene cambios locales ajenos al terminar, indicarlos claramente en la respuesta final.

## Despliegues

- Por defecto, las tareas se validan localmente con `npm run check`, `npm run lint` y, si aplica, servidor local o prueba HTTP local.
- En este proyecto Python, usar `python -m pytest` y, si aplica, prueba HTTP local contra `/healthz`.
- En este proyecto, cada cambio de Codex debe terminar con commit, push y redeployment en Coolify, salvo instruccion explicita en contra.
- Antes de desplegar, ejecutar `git status --short --branch`, commitear solo cambios propios, hacer push y lanzar redeploy en Coolify.
- No desplegar si hay cambios locales ajenos sin commitear que puedan hacer que el estado local no coincida con el commit desplegado.
- En la respuesta final indicar si la tarea quedo solo validada localmente o tambien desplegada. Si se desplego, indicar commit, rama, resultado del push, id del redeploy si existe y verificacion basica.

## Cloudflare Access

- La app debe quedar protegida por Cloudflare Access.
- Los usuarios permitidos pertenecen a los dominios `edicionesnobel.com`, `paraninfo.es` y `think-tank.es`.
- Los administradores iniciales son `pelayo@think-tank.es` y `pelayo@edicionesnobel.com`.
- La app identifica al usuario desde `Cf-Access-Authenticated-User-Email`; no implementar passwords propios para sustituir Access.

## Aprendizajes de modificacion PDF

- Para cambios semanticos en PDFs, como modificar una direccion, telefono, CIF o dato de cliente, el LLM debe recibir primero texto extraido del PDF con bloques y coordenadas. No planificar `replace_text` con palabras genericas como `direccion`; usar operaciones basadas en bloque/rectangulo cuando el usuario pide cambiar un dato localizado por contexto.
- Al modificar texto existente en un PDF, preservar los tipos de letra, tamanos y color del bloque original siempre que el extractor pueda obtenerlos. El contexto enviado al LLM debe incluir esos metadatos y las operaciones deben reutilizarlos.

## Aprendizajes Coolify y Cloudflare

- En Coolify 4.1.2, `POST /api/v1/applications/private-github-app` puede fallar con `Attempt to read property "private_key" on null` si la GitHub App existente no tiene private key asociada. Si el repo es publico, usar `POST /api/v1/applications/public` evita depender de esa integracion.
- En Coolify 4.1.2, el endpoint de creacion de env vars `POST /api/v1/applications/{uuid}/envs` rechaza `is_build_time`; usar `key`, `value`, `is_preview`, `is_literal` e `is_multiline`.
- En Coolify 4.1.2, `fqdn` puede no estar permitido en `POST/PATCH /api/v1/applications...`. Si se ajusta directamente en la DB, limpiar tambien `custom_labels` y `config_hash` antes de redeploy para que Traefik regenere etiquetas con el dominio real y no conserve el `sslip.io` temporal.
- En Cloudflare Tunnel gestionado por token remoto (`cloudflared tunnel run --token`), no hay `config.yml` local; actualizar `ingress` con la API `/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations`.
- En lanzamientos nuevos en Coolify, mantener separacion estricta entre repos, proyectos, entornos, claves de despliegue y bases de datos. Confirmar en Coolify `git_repository`, `git_branch`, `environment_id`, `fqdn`, `ports_exposes`, volumenes y base asociada antes de diagnosticar o desplegar.
- En dominios servidos por Cloudflare Tunnel, crear el CNAME hacia `*.cfargotunnel.com` no basta. El tunel tambien debe tener una regla `ingress` para el hostname antes del `http_status:404`, normalmente apuntando al proxy local de Coolify (`https://localhost:443`) con `originServerName` igual al dominio.
- Para diagnosticar un 404 en un dominio nuevo de Coolify, comparar contra un dominio que funciona en cuatro capas: DNS, reglas `ingress` del tunel, politica de Cloudflare Access y configuracion Coolify (`fqdn`, puerto expuesto, rama, estado y logs). Si DNS coincide pero el tunel no tiene `ingress`, el dominio caera en el 404 final aunque la app este arrancada.
- Cloudflare Access puede ocultar errores de origen. Para aislarlos, usar un bypass temporal solo durante la prueba, verificar que el origen devuelve 200, y eliminar el bypass al terminar. La verificacion final sin sesion debe ser un 302 hacia Cloudflare Access; con sesion autorizada debe cargar la app.
- Tras cambiar rutas de Cloudflare Tunnel, verificar tanto el dominio publico como una ruta interna sencilla de la app. Documentar la version del tunel actualizada y confirmar que no se han dejado politicas `bypass` abiertas.
- En apps nuevas de Coolify, activar o definir healthcheck cuando sea posible. Un estado `running:unknown` puede ser aceptable si la app responde, pero dificulta distinguir contenedor arrancado de servicio realmente saludable.

## Aprendizajes PowerShell y SSH

- Al construir comandos Linux remotos dentro de strings de PowerShell, no usar variables shell como `$d`, `$n`, `$i`, etc. sin escaparlas: PowerShell las expande localmente antes de enviarlas por SSH/plink y el remoto recibe valores vacios o comandos rotos.
- Para plink/ssh desde PowerShell, preferir comandos explicitos por dominio/host o escapar `$` como `` `$ ``. Si se necesita un bucle remoto, envolverlo de forma que PowerShell no interprete las variables del shell remoto.
- Evitar SQL remoto o shell complejo mezclado con muchas comillas en una sola llamada plink. Dividir en comandos pequenos y verificables reduce errores de diagnostico.
- Evitar enviar scripts Linux largos a `plink` por stdin desde PowerShell si el script debe ejecutarse tal cual: PowerShell puede introducir CRLF y comandos como `sort` llegan como `sort\r`. Para scripts remotos largos, codificar el contenido en base64 localmente, decodificarlo en el servidor y ejecutarlo alli.
