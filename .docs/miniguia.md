# Miniguia: consumo del API Backend y configuracion de Keycloak

Esta guia resume el flujo local para consumir directamente el Backend en
`http://localhost:8001` usando tokens Bearer emitidos por Keycloak.

## URLs locales

| Servicio | URL |
| --- | --- |
| Frontend | `http://localhost:5173` |
| BFF | `http://localhost:8000` |
| Backend directo | `http://localhost:8001` |
| Backend Swagger | `http://localhost:8001/docs` |
| Keycloak | `http://localhost:8080` |
| Realm OIDC | `http://localhost:8080/realms/docmanagement` |

Levantar o reconstruir el stack:

```powershell
docker compose up --build --force-recreate -d
docker compose ps
```

## Configuracion esperada del Backend

En Docker Compose, el Backend usa estas variables:

```yaml
OIDC_ISSUER: http://localhost:8080/realms/docmanagement
OIDC_ISSUER_ALIASES: http://keycloak:8080/realms/docmanagement
OIDC_JWKS_URL: http://keycloak:8080/realms/docmanagement/protocol/openid-connect/certs
OIDC_API_AUDIENCE: docmanagement-backend
```

Puntos importantes:

- `OIDC_ISSUER` debe coincidir con el claim `iss` del token usado desde Postman/curl.
- `OIDC_JWKS_URL` usa el hostname interno de Docker (`keycloak`) para que el Backend descargue las llaves publicas.
- `OIDC_API_AUDIENCE` debe estar presente en el claim `aud` del access token.
- El Backend valida tokens `RS256`, audience e issuer antes de resolver el usuario.

## Configuracion esperada de Keycloak

Realm:

```text
docmanagement
```

Cliente para usuarios/BFF:

```text
client_id: docmanagement-backend
client_secret: <KEYCLOAK_BACKEND_CLIENT_SECRET>
redirect_uri: http://localhost:8000/auth/callback
web_origin: http://localhost:5173
standardFlowEnabled: true
serviceAccountsEnabled: false
```

Cliente para consumo directo del API Backend:

```text
client_id: docmanagement-api-client
client_secret: <KEYCLOAK_API_CLIENT_SECRET>
standardFlowEnabled: false
serviceAccountsEnabled: true
```

Ambos clientes deben tener un protocol mapper de audiencia:

```text
name: audience-mapper
protocolMapper: oidc-audience-mapper
included.client.audience: docmanagement-backend
access.token.claim: true
id.token.claim: false
```

Si Keycloak ya tenia el realm creado antes del cambio, `--import-realm` no
sobrescribe la configuracion existente. En ese caso, revisar manualmente en la
consola admin que `docmanagement-api-client` tenga el audience mapper anterior.

Consola admin:

```text
URL: http://localhost:8080
usuario: admin
password: <KEYCLOAK_ADMIN_PASSWORD>
```

## Obtener token M2M para consumir el Backend

PowerShell:

```powershell
$tokenResponse = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8080/realms/docmanagement/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{
    grant_type = "client_credentials"
    client_id = "docmanagement-api-client"
    client_secret = "<KEYCLOAK_API_CLIENT_SECRET>"
  }

$accessToken = $tokenResponse.access_token
```

Validar token contra el Backend:

```powershell
curl.exe -i `
  -H "Authorization: Bearer $accessToken" `
  http://localhost:8001/api/health
```

Respuesta esperada:

```json
{
  "sub": "<service-account-sub>",
  "email": "service-account-docmanagement-api-client"
}
```

Si la respuesta es `{"detail":"Invalid bearer token"}`, revisar:

- Token expirado: generar uno nuevo.
- `aud` no contiene `docmanagement-backend`: falta el audience mapper.
- `iss` no coincide con `OIDC_ISSUER`: revisar `OIDC_ISSUER` y origen del token.
- Backend no puede leer JWKS: revisar `OIDC_JWKS_URL` y que Keycloak este arriba.

## Endpoints principales del Backend

Todos los endpoints protegidos requieren:

```http
Authorization: Bearer <access_token>
```

Rutas principales:

| Recurso | Metodo | Ruta |
| --- | --- | --- |
| Health protegido | GET | `/api/health` |
| Tipos documentales | GET/POST | `/api/document-types` |
| Plantillas HTML | GET/POST | `/api/content/templates` |
| PDFs estaticos | GET/POST | `/api/content/static-pdfs` |
| Disenos de documento | GET/POST | `/api/document-designs` |
| Agregar pagina template | POST | `/api/document-designs/{design_id}/pages/template` |
| Activar diseno | POST | `/api/document-designs/{design_id}/activate` |
| Previsualizar PDF | POST | `/api/document-designs/{design_id}/preview` |
| Generar documento | POST | `/api/document-designs/{design_id}/generate` |
| Biblioteca de emisiones | GET | `/api/issuances` |
| Descargar emision | GET | `/api/issuances/{issuance_id}/download` |

La ruta correcta de plantillas es:

```text
/api/content/templates
```

No usar `/api/content-templates`.

## Flujo minimo: crear documento desde un nuevo diseno

### 1. Crear tipo documental

```powershell
$docType = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/api/document-types" `
  -Headers @{ Authorization = "Bearer $accessToken" } `
  -ContentType "application/json" `
  -Body '{
    "name": "Contrato API",
    "description": "Tipo documental de prueba",
    "fields": [
      { "name": "cliente.nombre", "type": "string" },
      { "name": "fecha", "type": "date" }
    ],
    "metadata_definitions": []
  }'
```

### 2. Crear plantilla HTML

```powershell
$templateBody = @{
  document_type_id = $docType.id
  name = "Plantilla Contrato API"
  html = "<h1>Contrato</h1><p>Cliente: {{ cliente.nombre }}</p><p>Fecha: {{ fecha }}</p>"
  css = ""
} | ConvertTo-Json

$template = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/api/content/templates" `
  -Headers @{ Authorization = "Bearer $accessToken" } `
  -ContentType "application/json" `
  -Body $templateBody
```

### 3. Crear nuevo diseno

```powershell
$designBody = @{
  document_type_id = $docType.id
  name = "Diseno Contrato API"
  description = "Diseno creado desde API"
} | ConvertTo-Json

$design = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/api/document-designs" `
  -Headers @{ Authorization = "Bearer $accessToken" } `
  -ContentType "application/json" `
  -Body $designBody
```

El diseno nuevo queda en estado `draft`.

### 4. Agregar pagina de plantilla al diseno

```powershell
$pageBody = @{
  template_id = $template.id
  title = "Pagina principal"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/api/document-designs/$($design.id)/pages/template" `
  -Headers @{ Authorization = "Bearer $accessToken" } `
  -ContentType "application/json" `
  -Body $pageBody
```

### 5. Previsualizar PDF

```powershell
$dataBody = @{
  data = @{
    "cliente.nombre" = "ACME SAC"
    fecha = "2026-07-12"
  }
} | ConvertTo-Json -Depth 5

curl.exe -L `
  -H "Authorization: Bearer $accessToken" `
  -H "Content-Type: application/json" `
  -d $dataBody `
  -o preview.pdf `
  "http://localhost:8001/api/document-designs/$($design.id)/preview"
```

### 6. Generar documento definitivo

```powershell
$issuance = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/api/document-designs/$($design.id)/generate" `
  -Headers @{ Authorization = "Bearer $accessToken" } `
  -ContentType "application/json" `
  -Body $dataBody

$issuance
```

Al generar desde un diseno `draft`, el Backend valida el diseno y lo activa si
es valido. Si el diseno no tiene paginas o tiene contenido incompatible, la API
responde `400`.

### 7. Descargar documento generado

```powershell
curl.exe -L `
  -H "Authorization: Bearer $accessToken" `
  -o documento.pdf `
  "http://localhost:8001/api/issuances/$($issuance.id)/download"
```

## Checklist de troubleshooting

- `401 Missing bearer token`: falta header `Authorization`.
- `401 Invalid bearer token`: token vencido, audience/issuer incorrecto o JWKS inaccesible.
- `401 Invalid token claims`: token valido pero sin `sub` ni identidad resoluble.
- `404 Not Found`: revisar ruta exacta; usar Swagger en `http://localhost:8001/docs`.
- `400` al generar: revisar campos requeridos del tipo documental y que el diseno tenga al menos una pagina valida.
- Keycloak no refleja cambios del JSON importado: el realm ya existia; aplicar cambios manualmente o recrear el volumen `keycloak-data` si es aceptable perder datos locales.
