# Deployment Notes

## Current target

- Hostname: `modificacionpdf.nobel.es`
- Coolify URL: `http://10.164.18.45:8000/`
- Coolify project: `ModificacionPDF`
- Coolify project UUID: `bkknejfri65pvhxxvbxm9a2e`
- Coolify production environment UUID: `j7r96k83xk7k5l7viymlr6nc`
- Coolify server UUID: `jgo08g44gws0k8kw80g8owko`
- Coolify public GitHub source UUID: `l4gock04gwggocoggwcc080k`
- Coolify private GitHub App source UUID for `pelayogc`: `uaq30904muhi794ke3fpeaka`

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

Do not create `modificacionpdf.nobel.es` DNS alone. Add DNS only together with the matching Cloudflare Tunnel ingress rule and a deployed Coolify application, otherwise the hostname will fall through to the tunnel 404 rule.

## Deployment blocker

The local application is committed at `72f323c`, but there is no remote repository yet:

`git@github.com:pelayogc/modificacionpdf.git`

GitHub SSH authentication for `pelayogc` works locally, but GitHub does not create repositories on `git push`. Create the repository or provide a GitHub-capable tool/token, then:

1. Add remote: `git remote add origin git@github.com:pelayogc/modificacionpdf.git`
2. Push: `git push -u origin main`
3. Create a Coolify application from the private GitHub App source or public source.
4. Configure:
   - build pack: `dockerfile`
   - Dockerfile: `/Dockerfile`
   - exposed port: `8000`
   - health check path: `/healthz`
   - FQDN: `https://modificacionpdf.nobel.es`
   - persistent volume: `/data`
   - environment variables from `.env.example`
5. Add Cloudflare DNS CNAME and Tunnel ingress for `modificacionpdf.nobel.es`.
6. Deploy and verify:
   - internal `/healthz` returns `200`
   - public unauthenticated request returns Cloudflare Access redirect
   - authenticated request renders the upload form
