# Modificacion PDF

Aplicacion web protegida por Cloudflare Access para subir un PDF, describir cambios en lenguaje natural y descargar una version modificada.

## Capacidades

- Identificacion de usuarios desde `Cf-Access-Authenticated-User-Email`.
- Acceso permitido a `edicionesnobel.com`, `paraninfo.es` y `think-tank.es`.
- Administracion para `pelayo@think-tank.es` y `pelayo@edicionesnobel.com`.
- Estadisticas de uso en SQLite.
- Planificacion de cambios con OpenAI Responses API y aplicacion de operaciones PDF con PyMuPDF.

## Operaciones PDF soportadas

- Anadir texto en coordenadas de pagina.
- Anadir marca de agua.
- Resaltar texto.
- Redactar texto.
- Reemplazar texto aproximado conservando la posicion.
- Rotar, eliminar y reordenar paginas.

Las instrucciones libres se transforman en un plan JSON validado. Si el cambio pedido no se puede ejecutar con estas operaciones, la app devuelve un error claro en vez de generar un PDF ambiguo.

## Variables

Ver `.env.example`. En Coolify se debe configurar como minimo:

- `OPENAI_API_KEY`
- `PDF_LLM_MODEL`
- `DATA_DIR=/data`
- `ALLOWED_EMAIL_DOMAINS=edicionesnobel.com,paraninfo.es,think-tank.es`
- `ADMIN_EMAILS=pelayo@think-tank.es,pelayo@edicionesnobel.com`

Montar un volumen persistente en `/data`.

## Desarrollo local

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
$env:LOCAL_DEV_USER_EMAIL = "pelayo@think-tank.es"
uvicorn app.main:app --reload
```

Validacion:

```powershell
python -m pytest
```
