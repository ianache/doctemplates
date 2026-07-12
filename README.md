
# Backend 

```
uv --native-tls run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#Frontend   

```
rpm run dev
```

```
docker compose up backend frontend -d --force-recreate
```

# Usuarios:

- alice@example.com / welcome1
- bob@example.com / welcome1

# API

### Opción 1: Client Credentials Grant (Forma recomendada para desarrollo/M2M)

  Esta opción simula un cliente de integración usando las credenciales preconfiguradas del cliente de servicio  docmanagement-api-client .

  #### Paso 1: Obtener el Access Token de Keycloak

  Crea una nueva petición en Postman para solicitar el token:

  • Método:  POST
  • URL:  http://localhost:8080/realms/docmanagement/protocol/openid-connect/token
  • Headers:
      •  Content-Type: application/x-www-form-urlencoded
  • Body (x-www-form-urlencoded):
      •  grant_type  :  client_credentials
      •  client_id  :  docmanagement-api-client
      •  client_secret  :  <KEYCLOAK_API_CLIENT_SECRET>


  Presiona Send. Keycloak te devolverá un JSON similar a este:

    {
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "expires_in": 300,
      "token_type": "Bearer",
      "scope": "profile email"
    }

  #### Paso 2: Invocar los Endpoints del Backend

  Copia el valor de  access_token  y úsalo en tus peticiones de negocio (por ejemplo, para listar plantillas o diseños):

  • Método:  GET  (o el correspondiente)
  • URL:  http://localhost:8001/api/content/templates  (o a través de http://localhost:8000/api/content/templates)
  • Headers:
      •  Authorization  :  Bearer <Pega_tu_access_token_aquí>

  ──────
  ### Opción 2: Autenticación como Usuario Real (OAuth 2.0 en Postman)

  Si deseas hacer llamadas al API actuando como un usuario real ( alice@example.com  o  bob@example.com ):

  1. Crea la petición al API de negocio (ej.  http://localhost:8001/api/content/templates ).
  2. Ve a la pestaña Authorization de la petición.
  3. En Type, selecciona  OAuth 2.0 .
  4. En la sección derecha, desplázate hasta Configure New Token e ingresa:
      • Grant Type:  Authorization Code (With PKCE)
      • Callback URL: Marca Authorize using browser o coloca  http://localhost:8000/auth/callback
      • Auth URL:  http://localhost:8080/realms/docmanagement/protocol/openid-connect/auth
      • Access Token URL:  http://localhost:8080/realms/docmanagement/protocol/openid-connect/token
      • Client ID:  docmanagement-backend
      • Client Secret:  <KEYCLOAK_BACKEND_CLIENT_SECRET>
      • Code Challenge Method:  SHA-256
      • Scope:  openid email profile
  5. Haz clic en Get New Access Token.
  6. Postman abrirá una ventana emergente de Keycloak. Inicia sesión con las credenciales de prueba del proyecto:
      • Email:  alice@example.com  (o  bob@example.com )
      • Password:  <KEYCLOAK_USER_PASSWORD>
  7. Haz clic en Use Token en Postman, y éste se adjuntará automáticamente a tus peticiones subsiguientes.

## Token  

No pegar tokens estaticos en el README. Genera un access_token fresco desde Keycloak antes de consumir el API.
