# Azure Container Apps deployment

This deployment uses the existing backend image and a separate production build of
the React frontend. The frontend image serves static files with unprivileged Nginx
and proxies same-origin API requests to the backend sidecar. Local Docker Compose
and `frontend/Dockerfile` remain development-only and are not changed.

## Prerequisites and assumptions

- An Azure resource group, Container Apps managed environment, Azure Container
  Registry, Key Vault, and PostgreSQL database already exist. This configuration
  deliberately does not provision them.
- The Container Apps environment permits external ingress. ACA terminates TLS at
  its ingress; the Container App rejects insecure HTTP (`allowInsecure: false`).
  For a custom domain, configure its DNS and certificate on the Container Apps
  environment separately. No domain, certificate, or region is assumed here.
- A deployment identity can deploy Bicep, read the selected Key Vault secrets, and
  pull/publish the images. Grant the Container App and migration job identities
  `AcrPull` on the existing registry before starting the migration job. The
  application uses managed identity for registry image pulls; registry passwords
  are not configured here.
- Build and push both images with immutable tags (or digests). Supply the image
  references and names as deployment parameters; none are checked in.
- Use a unique `SESSION_SECRET_KEY` with at least 32 characters and a strong
  bootstrap administrator password of at least 12 characters. The bootstrap user
  is created only when the users table is empty.

## Build images

Build and push the backend from the repository root using the existing Dockerfile.
Build the production frontend from the `frontend/` context using
`frontend/Dockerfile.production`; it runs `npm ci` and `npm run build`, then
serves the bundle on port 8080. Substitute your own registry/name/immutable tag
when running the commands:

```sh
docker build -f Dockerfile -t <registry-server>/<backend-name>:<immutable-tag> .
docker build -f frontend/Dockerfile.production \
  -t <registry-server>/<frontend-name>:<immutable-tag> frontend
docker push <registry-server>/<backend-name>:<immutable-tag>
docker push <registry-server>/<frontend-name>:<immutable-tag>
```

The root and frontend Docker ignore files exclude local credentials, environment
files, generated media, databases, dependency directories, and local parameter
files from their respective build contexts. Publish both images to the existing
registry.

Use the image reference parameters `backendImage`, `frontendImage`, and
`registryServer` in the Bicep deployment. Do not use the development frontend
image produced by `frontend/Dockerfile`.

## Secrets and configuration

All required database, session, and bootstrap values are secure Bicep parameters.
Optional OpenAI, Instagram, Facebook, Telegram, and YouTube credentials are also
secure parameters. Bicep writes the supplied values to Container Apps secrets;
the containers receive them only through `secretRef` environment entries. The
YouTube OAuth JSON values, when supplied, are mounted from ACA secret volumes
instead of being placed in image layers or source files.

Supply secure values at deployment from a protected CI secret store or an ARM
parameter file that uses Key Vault references. Do not commit the parameter file
or pass literal secrets in shell command arguments. A Key Vault-backed secure
parameter entry has this shape in a local, untracked ARM parameter file:

```json
{
  "databaseUrl": {
    "reference": {
      "keyVault": { "id": "<existing Key Vault resource ID>" },
      "secretName": "<database-url secret name>"
    }
  }
}
```

Use the same reference form for `sessionSecretKey`,
`bootstrapAdminUsername`, `bootstrapAdminPassword`, and any optional credentials.
The deployment principal must be authorized for the Key Vault reference. Supply
non-secret parameters (environment resource ID, app/job names, image references,
registry server, and any non-secret integration IDs/URLs) separately. Keep the
parameter file outside the repository.

`SESSION_COOKIE_SECURE=true` is set by the deployment. The frontend and backend
share one Container App network namespace; Nginx proxies requests that are not
static frontend assets to `127.0.0.1:8000`. ACA ingress sends HTTPS traffic to
Nginx on port 8080, and the backend session cookie is always marked secure.

## Migration-first deployment

The Bicep template creates a manual migration job and conditionally creates the
public app. Keep `deployApplication=false` for the first deployment so the API
does not start against an unmigrated schema.

1. Build and push both images, prepare an untracked parameter file with image and
   existing resource identifiers plus Key Vault references, and deploy
   `infra/azure/container-apps.bicep` with `deployApplication=false`:

   ```sh
   az deployment group create \
     --resource-group <existing-resource-group> \
     --name <deployment-name> \
     --template-file infra/azure/container-apps.bicep \
     --parameters @<local-untracked-parameters.json>
   ```

2. Grant the migration job's managed identity `AcrPull` on the existing registry.
   Start it with
   `az containerapp job start --name <migration-job-name> --resource-group <existing-resource-group>`
   and wait for the execution to succeed. Review job execution logs and verify the
   database migration reached the latest Alembic revision. Do not proceed on failure.
3. Set `deployApplication=true` in the untracked parameter file and deploy the
   template again. Grant the app's managed identity `AcrPull` on the registry.
   Wait for both container probes and the latest revision to become healthy.
4. Open the ACA HTTPS FQDN and verify `/api/health`, login, and the secure session
   cookie. Configure a custom domain/certificate and `PUBLIC_MEDIA_BASE_URL`
   separately if required for publishing integrations.

The migration job executes `alembic upgrade head` from the backend image and
uses the same secure database/session parameters. It has no scheduled trigger and
is not run automatically during application startup. The existing Alembic
baseline is designed to adopt existing installations without dropping their
rows.

## Validation and operational notes

- The Bicep app has HTTPS-only external ingress, one active revision, bounded
  replica count, explicit CPU/memory, and frontend/backend HTTP health probes.
- The frontend image can be built locally without changing Compose:
  `docker build -f frontend/Dockerfile.production -t <local-test-tag> frontend`.
- The configuration assumes the PostgreSQL endpoint is reachable from the ACA
  environment. Database network rules, backup/HA policy, domain/certificate
  setup, monitoring, and role assignments are responsibilities of the existing
  Azure environment and are not provisioned by this template.
- Updating an existing database or rolling out a new backend image requires
  reviewing and running the migration job before enabling the app revision.
