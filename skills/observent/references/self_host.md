# observent — Local Self-Host Provisioning

This file is the **canonical reference** for standing up a backend locally with Docker when
the user has chosen a self-host backend that isn't already running. The observent skill reads
the templates here in Phase 2 and emits them as lifecycle tasks (a `write_file` for a vendored
compose file, and/or a `run_command` that runs `docker compose ... up -d --wait`) — see
`SKILL.md` Phase 1 § 1.6 and Phase 3 § 3.1.

Provisioning is **only ever offered** when **all** of these hold:

1. The backend's resolved endpoint `mode` is `self-host` (cloud is never provisioned).
2. The endpoint is unreachable at probe time (`detection.backends_reachable.<backend> == false`).
3. Docker + Compose are available (`detection.docker_available && detection.docker_compose_available`).
4. The backend is one of **Phoenix · Langfuse · SigNoz · Elastic APM · Opik · Jaeger** (see LangSmith note below).

`docker compose up` runs **only after** the user approves the `confirm` task — provisioning is
never silent.

---

## Provisioning method per backend

Two methods, chosen per backend by what the upstream stack needs:

| Backend | Method | Why |
|---|---|---|
| Phoenix | `vendored-compose` | Single container, no external config files — fully self-contained. |
| Jaeger | `vendored-compose` | Single all-in-one container, OTLP enabled inline via env — fully self-contained. |
| Elastic APM | `vendored-compose` | ES + Kibana + APM Server; config passed inline via `-E` flags / env. |
| Langfuse | `upstream-clone` | v3 stack is 6 coupled services with generated secrets; upstream compose is the supported path. |
| SigNoz | `upstream-clone` | Compose mounts ClickHouse / OTel-Collector config files from the repo — not self-contained. |
| Opik | `upstream-clone` | Multi-service stack (backend, frontend, ClickHouse, MySQL, Redis, MinIO) wired via compose profiles; upstream compose is the supported path. |

- **`vendored-compose`** → the skill writes `docker-compose.observent-<backend>.yml` into the
  user's project root (a `write_file` task), then runs
  `docker compose -f docker-compose.observent-<backend>.yml up -d --wait` (a `run_command` task).
- **`upstream-clone`** → the skill runs a single `run_command` that shallow-clones the pinned
  upstream repo into `.observent/vendor/<backend>/` and brings it up. No compose file is written
  into the project root.

Every `up` uses `--wait` so the command blocks until container healthchecks pass; the final
`validate` task then runs against a live endpoint.

---

## Arize Phoenix — `vendored-compose`

UI + OTLP HTTP on `6006`, OTLP gRPC on `4317`. No auth, no database (in-memory by default).

`docker-compose.observent-phoenix.yml`:
```yaml
services:
  phoenix:
    image: arizephoenix/phoenix:version-15.10.0
    container_name: observent-phoenix
    ports:
      - "6006:6006"   # UI + OTLP HTTP (/v1/traces)
      - "4317:4317"   # OTLP gRPC
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:6006').status==200 else sys.exit(1)"]
      interval: 5s
      timeout: 5s
      retries: 12
```

- Up: `docker compose -f docker-compose.observent-phoenix.yml up -d --wait`
- UI: `http://localhost:6006` · OTLP: `http://localhost:6006/v1/traces`
- Down: `docker compose -f docker-compose.observent-phoenix.yml down`
- **No-Docker alternative:** `px.launch_app()` in-process (see `matrix.md § Arize Phoenix`). Offer
  this if `detection.docker_available == false`.

---

## Jaeger — `vendored-compose`

Single all-in-one container. Jaeger v2 ships OTLP receivers on `4317`/`4318` enabled by default; the
explicit `COLLECTOR_OTLP_ENABLED=true` below is harmless on v2 and required if you pin a v1 image.
UI on `16686`, OTLP HTTP on `4318`. No auth, in-memory storage (local dev only).

`docker-compose.observent-jaeger.yml`:
```yaml
services:
  jaeger:
    image: jaegertracing/jaeger:2.19.0
    container_name: observent-jaeger
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"   # UI
      - "4318:4318"     # OTLP HTTP (/v1/traces)
      - "4317:4317"     # OTLP gRPC
```

- **Readiness:** Jaeger's image is distroless (no shell/curl/python), so it carries **no**
  in-container `healthcheck:` — `docker compose up -d --wait` waits for the container to reach the
  *running* state (Jaeger starts in ~1s), and the downstream `validate` task then probes the OTLP
  endpoint. This is the one vendored stack without a healthcheck block, for that reason.
- Up: `docker compose -f docker-compose.observent-jaeger.yml up -d --wait`
- UI: `http://localhost:16686` · OTLP: `http://localhost:4318/v1/traces` (set `JAEGER_ENDPOINT` to it)
- No auth — leave it unset.
- **Note:** Jaeger's default `4318`/`4317` OTLP ports collide with a self-hosted SigNoz. If you run
  both, remap one stack's host ports in its compose file.
- Down: `docker compose -f docker-compose.observent-jaeger.yml down`

---

## Elastic APM — `vendored-compose`

ES + Kibana + APM Server, single-node, **security disabled** (local dev only). APM Server on
`8200`, Kibana on `5601`, Elasticsearch on `9200`.

`docker-compose.observent-elastic-apm.yml`:
```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.3
    container_name: observent-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"\\(green\\|yellow\\)\"'"]
      interval: 10s
      timeout: 10s
      retries: 12
  kibana:
    image: docker.elastic.co/kibana/kibana:8.15.3
    container_name: observent-kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      elasticsearch:
        condition: service_healthy
  apm-server:
    image: docker.elastic.co/apm/apm-server:8.15.3
    container_name: observent-apm-server
    ports:
      - "8200:8200"
    depends_on:
      elasticsearch:
        condition: service_healthy
    command: >
      apm-server -e
        -E apm-server.host=0.0.0.0:8200
        -E apm-server.rum.enabled=true
        -E output.elasticsearch.hosts=["http://elasticsearch:9200"]
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:8200/ > /dev/null"]
      interval: 10s
      timeout: 10s
      retries: 12
```

- Up: `docker compose -f docker-compose.observent-elastic-apm.yml up -d --wait`
- APM Server: `http://localhost:8200` (`ELASTIC_APM_SERVER_URL`) · Kibana APM UI: `http://localhost:5601/app/apm`
- No secret token needed (security off) — leave `ELASTIC_APM_SECRET_TOKEN` unset.
- Down (drop volumes): `docker compose -f docker-compose.observent-elastic-apm.yml down -v`

---

## Langfuse — `upstream-clone`

Langfuse v3 self-host is six coupled services (web, worker, postgres, clickhouse, redis, minio)
with generated secrets. Use the upstream compose, pinned to the `:3` major tag (upstream's
stability contract).

- Up:
  ```bash
  git clone --depth 1 -b main https://github.com/langfuse/langfuse.git .observent/vendor/langfuse \
    && docker compose -f .observent/vendor/langfuse/docker-compose.yml up -d --wait
  ```
- UI: `http://localhost:3000` · OTLP: `http://localhost:3000/api/public/otel/v1/traces`
- After first start, create a project in the UI and copy `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`
  into `.env`, with `LANGFUSE_HOST=http://localhost:3000`. Unlike the other stacks these keys can't
  be known ahead of time, so the `validate` task may report missing keys until the user fills them in.
- Down: `docker compose -f .observent/vendor/langfuse/docker-compose.yml down`

---

## SigNoz — `upstream-clone`

The SigNoz compose mounts ClickHouse + OTel-Collector config files from the repo, so it can't be
vendored as a single file. Clone the repo and bring up `deploy/docker`, pinning the image tags.

- Up:
  ```bash
  git clone --depth 1 -b main https://github.com/SigNoz/signoz.git .observent/vendor/signoz \
    && docker compose -f .observent/vendor/signoz/deploy/docker/docker-compose.yaml up -d --wait
  ```
- UI: `http://localhost:8080` (recent unified `signoz/signoz` image; older releases used `3301`)
- OTLP: `http://localhost:4318/v1/traces` (HTTP) / `localhost:4317` (gRPC) — unchanged across versions.
- No auth for self-host (leave `SIGNOZ_INGESTION_KEY` unset; set `SIGNOZ_ENDPOINT=http://localhost:4318/v1/traces`).
- Down: `docker compose -f .observent/vendor/signoz/deploy/docker/docker-compose.yaml down`

---

## Opik — `upstream-clone`

Opik's compose brings up a multi-service stack (backend, frontend, ClickHouse, MySQL, Redis, MinIO)
selected via the `opik` profile. Clone the repo at the pinned tag so the compose file matches the
pinned images, and pin `OPIK_VERSION` for the `ghcr.io/comet-ml/opik/*` images (the compose defaults
them to `latest`).

- Up:
  ```bash
  git clone --depth 1 -b 2.1.3 https://github.com/comet-ml/opik.git .observent/vendor/opik \
    && OPIK_VERSION=2.1.3 docker compose -f .observent/vendor/opik/deployment/docker-compose/docker-compose.yaml --profile opik up -d --wait
  ```
- UI: `http://localhost:5173` · OTLP: `http://localhost:5173/api/v1/private/otel/v1/traces`
- No auth for self-host (leave `OPIK_API_KEY` / `OPIK_WORKSPACE` unset; set `OPIK_URL_OVERRIDE=http://localhost:5173/api`).
- If port `5173` is taken, set `NGINX_PORT` (or `OPIK_PORT_OFFSET` to shift every Opik port) before `up`.
- Down: `docker compose -f .observent/vendor/opik/deployment/docker-compose/docker-compose.yaml --profile opik down`

---

## LangSmith — not provisioned

LangSmith has **no free OSS / Docker edition**. It is commercial and cloud-first; self-host is
an enterprise-licensed deployment. observent does **not** generate a local stack for it.

When LangSmith is selected with a non-cloud `LANGSMITH_ENDPOINT` that is unreachable, surface this
text instead of a provisioning offer:

> LangSmith self-host requires an enterprise license. Point `LANGSMITH_ENDPOINT` at your licensed
> deployment, or use LangSmith Cloud (`https://api.smith.langchain.com`, the default) with
> `LANGSMITH_API_KEY`. observent can't provision LangSmith locally.

---

## Image Versions

Canonical pin record for the provisioning stacks (analogous to `matrix.md § Verified Versions`).
These are exact image tags, not floors. Bump alongside the matrix's pip pins and update the
`Last verified` date.

| Backend | Image | Tag | Source |
|---|---|---|---|
| Phoenix | `arizephoenix/phoenix` | `version-15.10.0` | Docker Hub — https://hub.docker.com/r/arizephoenix/phoenix/tags |
| Elastic APM | `docker.elastic.co/elasticsearch/elasticsearch` | `8.15.3` | Elastic registry — https://www.docker.elastic.co |
| Elastic APM | `docker.elastic.co/kibana/kibana` | `8.15.3` | Elastic registry |
| Elastic APM | `docker.elastic.co/apm/apm-server` | `8.15.3` | Elastic registry |
| Langfuse | `langfuse/langfuse`, `langfuse/langfuse-worker` | `3` (major; upstream compose) | https://github.com/langfuse/langfuse |
| SigNoz | `signoz/signoz` | `v0.126.1` (upstream compose `VERSION`) | https://github.com/SigNoz/signoz |
| SigNoz | `signoz/signoz-otel-collector` | `v0.144.4` (upstream `OTELCOL_TAG`) | https://github.com/SigNoz/signoz |
| SigNoz | `clickhouse/clickhouse-server` | `25.5.6` (upstream compose) | https://github.com/SigNoz/signoz |
| Opik | `ghcr.io/comet-ml/opik/opik-backend`, `opik-frontend`, `opik-python-backend` | `2.1.3` (`OPIK_VERSION`) | https://github.com/comet-ml/opik |
| Opik | `clickhouse/clickhouse-server` | `25.8.16.34-alpine` (upstream compose) | https://github.com/comet-ml/opik |
| Opik | `mysql` | `8.4.2` (upstream compose) | https://github.com/comet-ml/opik |
| Opik | `redis` | `7.2.4-alpine3.19` (upstream compose) | https://github.com/comet-ml/opik |
| Jaeger | `jaegertracing/jaeger` | `2.19.0` | Docker Hub — https://hub.docker.com/r/jaegertracing/jaeger/tags |

*Last verified: 2026-06-25.* Langfuse, SigNoz, and Opik tags are governed by their upstream compose
files (`upstream-clone` method); the rows above record what those files pinned at verification time.

---

## Port-conflict & readiness notes

- **Readiness:** every `up` uses `--wait`; vendored compose files carry `healthcheck:` blocks so
  `--wait` blocks until healthy. `upstream-clone` stacks ship their own healthchecks. The lone
  exception is Jaeger, whose distroless image can't self-healthcheck — `--wait` falls back to the
  container's *running* state and the final `validate` task probes its OTLP endpoint.
- **Port conflicts:** if a probe shows a port already in use by something *other* than the intended
  backend (e.g. `6006` taken but not Phoenix), warn the user and let them remap the host port in the
  compose file rather than forcing `up`.
- **Teardown:** each section lists its `down` command. The skill surfaces the matching `down` line in
  the Phase 4 § 4.3 summary so the user can stop the stack.
