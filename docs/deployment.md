# Deployment Notes

## Current target

- Hostname: `modificacionpdf.nobel.es`
- Coolify URL: `http://10.164.18.45:8000/`
- Coolify project: `ModificacionPDF`
- Coolify project UUID: `bkknejfri65pvhxxvbxm9a2e`
- Coolify production environment UUID: `j7r96k83xk7k5l7viymlr6nc`
- Coolify server UUID: `jgo08g44gws0k8kw80g8owko`
- Coolify application: `modificacionpdf-web`
- Coolify application UUID: `r5hhxxrrpbvyyi7vz74o2jv5`
- Coolify public GitHub source UUID: `l4gock04gwggocoggwcc080k`
- Coolify private GitHub App source UUID for `pelayogc`: `uaq30904muhi794ke3fpeaka`
- Git repository: `https://github.com/pelayogc/modificacionpdf.git`
- Git branch: `main`
- Exposed port: `8000`
- Health check: `/healthz`
- Persistent storage: `r5hhxxrrpbvyyi7vz74o2jv5-modificacionpdf-data` mounted at `/data`

## Cloudflare Access

- Access application: `Modificacion PDF Nobel`
- Access application ID: `d0e48b11-f104-47d5-8213-5b0743265605`
- Access policy: `Allow group email domains`
- Access policy ID: `6ee30b4b-7e00-4e4b-aa31-0ab9c750b30d`
- Allowed email domains:
  - `edicionesnobel.com`
  - `paraninfo.es`
  - `think-tank.es`

## DNS and tunnel

Existing Nobel apps use a proxied CNAME to:

`b4568616-bb1e-461a-be43-27a25576b2eb.cfargotunnel.com`

DNS record:

- `modificacionpdf.nobel.es` CNAME `b4568616-bb1e-461a-be43-27a25576b2eb.cfargotunnel.com`, proxied
- Cloudflare DNS record ID: `836ff9dfe2c58b611e3c268637c664e8`

Tunnel ingress:

- Tunnel ID: `b4568616-bb1e-461a-be43-27a25576b2eb`
- Configuration version with `modificacionpdf.nobel.es`: `19`
- Rule points to `https://localhost:443` with `originServerName=modificacionpdf.nobel.es` and `noTLSVerify=true`.

## Deployment

- Initial app deploy: `hsb3hd7yzj1vndbozpoug11r`
- Final label-regeneration deploy: `cb4vza513tlm4e1k19cuccvv`
- Documentation redeploy after final notes: `vewmim6zvzlzpf0zkqvcv9wj`
- Runtime code was introduced in commit `38d8d6fe6608385c234e7429546fd57ace7bc988`; later documentation-only commits can be deployed without changing the application image contents because the Dockerfile copies only `app/` and `requirements.txt`.
- Status after deployment: `running:healthy`

Validation performed:

- Internal Coolify proxy: `https://localhost/healthz` with `Host: modificacionpdf.nobel.es` returned `200`.
- Public unauthenticated request to `https://modificacionpdf.nobel.es/` returned `302` to Cloudflare Access.
- Internal authenticated-origin simulation with `Cf-Access-Authenticated-User-Email: pelayo@think-tank.es` rendered `Modificar PDF`.
- Full internal upload smoke test generated a modified PDF result page using the deployed app and OpenAI key.

## Operational notes

- The repository is public, so the application was created through `POST /api/v1/applications/public`.
- The existing private GitHub App source failed for app creation with `Attempt to read property "private_key" on null`.
- Coolify API did not allow `fqdn` on create/patch. The field was set directly in the Coolify DB for this app, then `custom_labels` and `config_hash` were cleared before redeploy so labels regenerated for `modificacionpdf.nobel.es`.
- Env var creation in Coolify 4.1.2 rejects `is_build_time`; use only the accepted env fields.
