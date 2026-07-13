# PRD4: Generacion asincrona de documentos PDF con Celery y Redis

## 1. Vision general

El modulo de generacion de documentos debe pasar de un flujo HTTP sincrono a
un flujo asincrono basado en workers. El Backend seguira exponiendo el API de
emision, pero la composicion pesada del PDF sera ejecutada por Celery workers
usando Redis como broker.

Objetivo principal: evitar que `POST /api/document-designs/{design_id}/generate`
bloquee el request mientras renderiza HTML/Jinja, procesa PDFs estaticos,
fusiona paginas y guarda el archivo final.

## 2. Contexto actual

El flujo actual de generacion:

1. Recibe `POST /api/document-designs/{design_id}/generate`.
2. Valida el diseno y metadata.
3. Activa el diseno si esta en `draft`.
4. Ejecuta `generate_composed_pdf(...)` en el mismo request.
5. Guarda el PDF con `StorageProvider`.
6. Crea `DocumentIssuance` con `status = "success"`.
7. Retorna `201 Created`.

Problemas:

- El request queda bloqueado durante toda la generacion.
- Un PDF grande puede agotar timeout del BFF, proxy o cliente.
- Si el proceso web cae durante la generacion, el trabajo se pierde.
- No hay estado visible de cola/progreso.
- No hay mecanismo natural de retry.

## 3. Decision tecnica

Usar:

- **Celery** como motor de tareas.
- **Redis** como broker de cola.
- **Backend FastAPI** como productor de tareas.
- **Worker Celery** como consumidor y ejecutor de la generacion PDF.
- **Postgres** como fuente de verdad del estado funcional de la emision.
- **StorageProvider** existente para guardar PDFs finales en local/S3/MinIO.

Redis no debe ser la fuente de verdad del dominio. Redis solo coordina cola y
entrega de tareas. El estado visible para el usuario debe persistirse en
`document_issuances`.

## 4. Arquitectura propuesta

```text
Cliente / BFF / Frontend
        |
        | POST /api/document-designs/{design_id}/generate
        v
Backend FastAPI
        |
        | 1. valida entrada minima
        | 2. crea DocumentIssuance(status="queued")
        | 3. envia task Celery(generate_document_pdf, issuance_id)
        v
Redis Broker
        |
        v
Celery Worker
        |
        | 1. status="processing"
        | 2. carga design/input desde Postgres
        | 3. genera PDF
        | 4. guarda en StorageProvider
        | 5. status="success" o "failure"
        v
Postgres + Storage
```

## 5. Estados de emision

Ampliar `DocumentIssuance.status`.

Estados requeridos:

```text
queued      -> emision registrada y task enviada a Redis
processing  -> worker tomo la task y esta generando el PDF
success     -> PDF generado y almacenado correctamente
failure     -> generacion fallida
```

Transiciones validas:

```text
queued -> processing
queued -> failure
processing -> success
processing -> failure
failure -> queued    (solo retry explicito futuro)
```

## 6. Cambios de modelo de datos

Tabla `document_issuances`:

Campos existentes a revisar:

- `status`: ampliar constraint a los cuatro estados.
- `storage_key`: debe permitir `NULL` mientras el PDF no existe.

Campos nuevos recomendados:

```text
celery_task_id       string nullable
error_message        text nullable
queued_at            datetime nullable
started_at           datetime nullable
completed_at         datetime nullable
retry_count          integer default 0
```

Notas:

- `input_data` y `metadata_values` deben guardarse al encolar, no al finalizar.
- `design_version_id` debe quedar fijado al momento de encolar.
- Si el diseno esta en `draft`, el Backend debe activarlo antes de encolar para
  garantizar que el worker trabaje sobre una version estable.

## 7. Cambios de API

### 7.1 Encolar generacion

Endpoint:

```http
POST /api/document-designs/{design_id}/generate
```

Comportamiento nuevo:

1. Valida bearer token.
2. Carga diseno.
3. Si el diseno esta en `draft`, valida y activa.
4. Valida metadata.
5. Crea `DocumentIssuance`:
   - `status = "queued"`
   - `storage_key = null`
   - `input_data = data`
   - `metadata_values = coerced_metadata`
   - `queued_at = now`
6. Envia task Celery con `issuance_id`.
7. Guarda `celery_task_id`.
8. Retorna `202 Accepted`.

Respuesta esperada:

```json
{
  "id": "uuid",
  "design_version_id": "uuid",
  "storage_key": null,
  "user_id": "uuid",
  "input_data": {},
  "metadata_values": {},
  "status": "queued",
  "error_message": null,
  "created_at": "2026-07-12T15:11:00"
}
```

### 7.2 Consultar estado

Endpoint existente:

```http
GET /api/issuances/{issuance_id}
```

Debe retornar estados `queued`, `processing`, `success`, `failure`.

### 7.3 Descargar PDF

Endpoint existente:

```http
GET /api/issuances/{issuance_id}/download
```

Comportamiento:

- `success`: descarga PDF.
- `queued` o `processing`: retornar `409 Conflict` con detalle
  `"Document generation is not complete"`.
- `failure`: retornar `409 Conflict` con `error_message`.

### 7.4 Preview

Mantener `POST /api/document-designs/{design_id}/preview` sincrono por ahora.

Justificacion:

- Preview es interaccion de edicion y debe seguir respondiendo rapido.
- Si los previews empiezan a ser pesados, se puede crear un flujo async separado.

## 8. Componentes backend nuevos

### 8.1 Configuracion

Agregar settings:

```text
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_TASK_ALWAYS_EAGER=false
```

Para tests unitarios:

```text
CELERY_TASK_ALWAYS_EAGER=true
```

### 8.2 App Celery

Nuevo modulo:

```text
backend/app/workers/celery_app.py
```

Responsabilidad:

- Crear instancia Celery.
- Cargar broker/result backend desde settings.
- Registrar tasks.
- Configurar serializacion JSON.
- Configurar timeouts y retries.

Configuracion recomendada:

```text
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
task_acks_late = true
worker_prefetch_multiplier = 1
task_time_limit = 600
task_soft_time_limit = 540
```

### 8.3 Task de generacion

Nuevo modulo:

```text
backend/app/workers/document_generation.py
```

Task:

```text
generate_document_pdf(issuance_id: str)
```

Responsabilidad:

1. Abrir sesion DB propia.
2. Bloquear/cargar `DocumentIssuance`.
3. Si no esta `queued`, salir idempotentemente.
4. Marcar `processing`, `started_at`.
5. Cargar `DocumentDesign` con paginas, tipo documental y campos.
6. Ejecutar `generate_composed_pdf(...)`.
7. Guardar bytes en `StorageProvider`.
8. Actualizar:
   - `storage_key`
   - `status = "success"`
   - `completed_at`
9. Crear `DocumentTracelog(event_type="generation")`.
10. En excepcion:
   - `status = "failure"`
   - `error_message = str(error)`
   - `completed_at`
   - crear tracelog de error si aplica.

## 9. Docker Compose

Agregar servicio Redis:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "127.0.0.1:6379:6379"
```

Agregar servicio worker:

```yaml
worker:
  build:
    context: ./backend
  command: uv run celery -A app.workers.celery_app worker --loglevel=info
  environment:
    DATABASE_URL: ...
    CELERY_BROKER_URL: redis://redis:6379/0
    CELERY_RESULT_BACKEND: redis://redis:6379/1
    STORAGE_PROVIDER_TYPE: ${STORAGE_PROVIDER_TYPE:-local}
    ...
  volumes:
    - content-storage:/app/.content-storage
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started
```

Si se usa `STORAGE_PROVIDER_TYPE=local`, backend y worker deben compartir el
mismo volumen `content-storage`. Para ambientes reales se recomienda S3/MinIO.

## 10. Seguridad y consistencia

- El worker no debe recibir bearer tokens.
- El worker opera sobre `issuance_id`, no sobre payload arbitrario completo.
- El Backend autentica/autorizara la creacion de la emision antes de encolar.
- El worker debe re-leer todo desde Postgres.
- No registrar datos sensibles completos en logs.
- Limitar tamano de error persistido en `error_message`.
- El task debe ser idempotente: si una task duplicada llega cuando la emision ya
  esta `success` o `failure`, no debe regenerar.

## 11. Estrategia de retry

Primera version:

- Celery retry automatico solo para errores transitorios de storage/DB.
- Errores funcionales de plantilla o payload deben marcar `failure` sin retry.

Ejemplos transitorios:

- Timeout al guardar en S3/MinIO.
- Conexion temporal a Postgres.
- Redis redelivery por worker caido.

Ejemplos no transitorios:

- Template Jinja invalido.
- Payload incompleto.
- PDF estatico inexistente.

## 12. Impacto frontend/BFF

El frontend/BFF debe tratar la generacion como asincrona:

1. Usuario hace click en generar.
2. API retorna `issuance_id` con `status = queued`.
3. UI navega al detalle de emision o muestra estado.
4. UI consulta `GET /api/issuances/{id}` hasta `success` o `failure`.
5. Cuando `success`, habilita descarga/preview.

Polling inicial recomendado:

```text
cada 2 segundos hasta 60 segundos
luego cada 5 segundos
detener al llegar a success/failure
```

## 13. Criterios de aceptacion

1. `POST /api/document-designs/{design_id}/generate` responde `202 Accepted` sin
   generar el PDF dentro del request.
2. Se crea una fila `DocumentIssuance` con `status = queued`.
3. Se registra `celery_task_id`.
4. El worker toma la tarea y cambia estado a `processing`.
5. Al finalizar correctamente, la emision queda `success` y con `storage_key`.
6. Si la generacion falla, la emision queda `failure` con `error_message`.
7. `GET /api/issuances/{id}` refleja el estado actual.
8. `GET /api/issuances/{id}/download` rechaza estados no listos con `409`.
9. El flujo sigue funcionando con storage local compartido en Docker Compose.
10. El flujo sigue funcionando con MinIO/S3.
11. Tests cubren encolado, procesamiento exitoso, fallo funcional y descarga
    antes de completion.

## 14. Plan de implementacion sugerido

### Fase A: Modelo y API

- Migracion de `document_issuances`.
- Actualizar schemas de salida.
- Cambiar `generate` para encolar y retornar `202`.
- Ajustar download para estados no listos.

### Fase B: Celery/Redis

- Agregar dependencias `celery` y `redis`.
- Crear `celery_app.py`.
- Crear task `generate_document_pdf`.
- Agregar servicios `redis` y `worker` en Compose.

### Fase C: Tests

- Tests unitarios con `CELERY_TASK_ALWAYS_EAGER=true`.
- Test de enqueue sin ejecutar render pesado.
- Test de worker exitoso.
- Test de worker failure.
- Test download `queued/processing`.

### Fase D: UI/BFF

- Ajustar UI para estados async.
- Agregar polling o refresco manual.
- Mostrar errores de generacion.

## 15. Riesgos

- Duplicacion de tareas si Redis re-entrega: mitigar con idempotencia por estado.
- Storage local no compartido entre backend y worker: mitigar con volumen comun o S3.
- Jobs atascados en `processing` si worker muere: agregar tarea futura de recovery.
- Backpressure: configurar concurrencia y prefetch bajo para PDFs grandes.
- Migracion de `storage_key` nullable puede afectar endpoints existentes si no
  manejan estados no finales.

## 16. Fuera de alcance inicial

- Barra de progreso por porcentaje.
- Cancelacion de jobs.
- Priorizacion de colas.
- Retry manual desde UI.
- WebSockets/SSE para notificaciones en tiempo real.
- Separar preview asincrono.
