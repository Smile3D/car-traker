# GitHub Actions

Workflows and release automation for **car-traker**.

## Workflows

| Workflow | File | When | What |
|---|---|---|---|
| Build and push backend | `workflows/build-backend.yml` | Push to `main` (backend paths) or manual | Build/push backend image to Artifact Registry, then deploy |
| Build and push frontend | `workflows/build-frontend.yml` | Push to `main` (frontend paths) or manual | Build/push frontend image to Artifact Registry, then deploy |
| Deploy to VM | `workflows/deploy.yml` | Called by build workflows, or manual | IAP SSH to GCE → `docker compose pull` / `up -d` (no downtime `down`) |
| Release | `workflows/release.yml` | Push to `main` or manual | [semantic-release](https://semantic-release.gitbook.io/) → GitHub Release + tag |

## Semantic release

Releases are driven by [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) on `main`.

| Commit type | Version bump | Example |
|---|---|---|
| `fix:` | patch | `fix(auth): correct CORS origin` → `1.0.1` |
| `feat:` | minor | `feat(frontend): add /health page` → `1.1.0` |
| `BREAKING CHANGE` / `type!:` | major | `feat!: drop legacy login` → `2.0.0` |
| `chore:`, `ci:`, `docs:`, … | no release | unless they include a breaking change |

**Outputs**

- GitHub Release (notes from commits since the last tag)
- Git tag `vX.Y.Z`
- Updated `CHANGELOG.md` and `package.json` version (committed as `chore(release): … [skip ci]`)

**Config**

- `.releaserc.json` — plugins and branch
- Root `package.json` — `semantic-release` and plugins (devDependencies)

**Local dry-run**

```bash
npm ci
npx semantic-release --dry-run
```

## Secrets / variables (CD)

Used by build + deploy (not by Release — Release uses `GITHUB_TOKEN`):

| Name | Type | Purpose |
|---|---|---|
| `GCP_SA_KEY` | secret | SA JSON for Artifact Registry push + IAP SSH |
| `VM_SSH_PRIVATE_KEY` | secret | SSH private key for VM user (`garage-tracker`) |
| `VM_NAME` | variable (optional) | default `car-garage-tracker` |
| `VM_ZONE` | variable (optional) | default `europe-central2-a` |
| `VM_SSH_USER` | variable (optional) | default `garage-tracker` |
| `DEPLOY_DIR` | variable (optional) | default `/home/garage-tracker/car-traker` |

Infra prerequisites (IAP firewall + SA IAM) live in the **infra-garage** Terraform stack.
