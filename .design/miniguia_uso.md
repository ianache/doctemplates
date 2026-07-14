# Guía de Uso: API de Generación y Previsualización de Documentos

Esta guía detalla el funcionamiento y uso de los endpoints de la API para la generación de documentos de producción, previsualización en memoria y descarga de PDFs emitidos.

---

## 🔑 Autenticación

Todos los endpoints de la API están protegidos. Requieren que las solicitudes incluyan la cookie de sesión en las cabeceras HTTP:

* **Nombre de la Cookie:** `docmanagement_session`
* **Cabecera HTTP:** `Cookie: docmanagement_session=<VALOR_TOKEN>`

Si una solicitud no incluye esta cookie, o si la sesión ha expirado, la API responderá con un error `401 Unauthorized` o `{"detail": "Not authenticated"}`.

---

## 🛠️ Endpoints de la API

### 1. Generación de PDF de Producción
Genera un PDF final, escribe el archivo físico en el almacenamiento del servidor y guarda un registro de auditoría en la base de datos.

* **Ruta:** `POST /api/document-designs/{design_id}/generate`
* **Reglas de Negocio:**
  * Solo se permiten diseños en estado `active` o `superseded` (rechaza diseños en estado `draft` con `400 Bad Request`).
  * Valida que los datos provistos cumplan con el esquema del tipo de documento asociado. Si faltan campos requeridos o hay tipos inválidos, devuelve un error `400`.
  * Los campos adicionales no definidos en el tipo de documento son ignorados.
* **Ejemplo de Cuerpo de la Petición (JSON):**
  ```json
  {
    "codigo": "C001",
    "Nombre": "Juan Pérez",
    "correo": "juan@example.com"
  }
  ```
* **Ejemplo de Respuesta (`201 Created`):**
  ```json
  {
    "id": "194fb8f4-d090-486d-adc2-d11b5bd44906",
    "design_version_id": "dd0f0d77-0b2c-4ddf-a310-ff6d960420f8",
    "file_path": "../.content-storage/issuances/194fb8f4-d090-486d-adc2-d11b5bd44906.pdf",
    "user_id": "e56a30e5-d7cb-4d67-8303-5815fde33844",
    "input_data": {
      "codigo": "C001",
      "Nombre": "Juan Perez",
      "correo": "juan@example.com"
    },
    "created_at": "2026-07-08T19:43:26.529440"
  }
  ```

---

### 2. Previsualización de Diseño en Memoria
Genera un PDF temporal en memoria para que el usuario pueda visualizar la maqueta.

* **Ruta:** `POST /api/document-designs/{design_id}/preview`
* **Reglas de Negocio:**
  * Solo se permiten diseños en estado `draft` o `active`.
  * **Datos Mock / Fallback:** Si envías un JSON vacío `{}` o incompleto, el servidor autogenera valores mock de prueba basándose en los tipos de campo especificados en el diseño (por ejemplo, genera un string aleatorio para tipos string, números para tipo number, etc.).
  * **Sin persistencia:** No guarda registros en la base de datos ni crea archivos físicos en el servidor.
* **Respuesta (`200 OK`):**
  * Retorna directamente el flujo de bytes binarios del PDF.
  * **Content-Type:** `application/pdf`

---

### 3. Descarga de PDF Emitido
Descarga un documento PDF que fue generado previamente en producción.

* **Ruta:** `GET /api/issuances/{issuance_id}/download`
* **Reglas de Negocio:**
  * Requiere estar autenticado.
  * Recupera el archivo usando el UUID de emisión (`issuance_id`).
  * Si la emisión no existe o el archivo PDF fue eliminado físicamente del disco del servidor, devuelve un error `404 Not Found`.
* **Respuesta (`200 OK`):**
  * Retorna el flujo de bytes binarios del PDF.
  * **Content-Type:** `application/pdf`

---

## 💻 Ejemplos de Código de Integración

### 1. Ejecutar desde la Consola del Navegador (JavaScript Fetch)
Si ya has iniciado sesión en la aplicación frontend, tu navegador ya posee la cookie en su almacén de cookies. Puedes hacer llamadas directas ejecutando esto en la consola web:

```javascript
// Reemplaza con tu UUID de diseño activo
const designId = "dd0f0d77-0b2c-4ddf-a310-ff6d960420f8";

fetch(`/api/document-designs/${designId}/generate`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    "codigo": "C001",
    "Nombre": "Juan Pérez",
    "correo": "juan@example.com"
  })
})
.then(res => res.json())
.then(data => console.log("Documento Emitido:", data))
.catch(err => console.error("Error:", err));
```

### 2. Ejecutar desde un Script de Python (Httpx / Requests)
Útil para integraciones Machine-to-Machine o scripts de prueba automatizados:

```python
import httpx

# Reemplaza con la dirección de tu backend local
url = "http://127.0.0.1:8000/api/document-designs/dd0f0d77-0b2c-4ddf-a310-ff6d960420f8/generate"

# Reemplaza con el token de tu cookie activa
cookies = {
    "docmanagement_session": "qf-6L6-OZcDxD6ZFwQ7iDGSw7i8_rTVPiEaVhfM_aoA"
}

payload = {
    "codigo": "C001",
    "Nombre": "Juan Pérez",
    "correo": "juan@example.com"
}

response = httpx.post(url, cookies=cookies, json=payload)

if response.status_code == 201:
    print("PDF generado correctamente:")
    print(response.json())
else:
    print(f"Error {response.status_code}:", response.text)
```

### 3. Ejecutar desde la terminal (cURL en Linux/macOS)
```bash
curl -X POST http://127.0.0.1:8000/api/document-designs/dd0f0d77-0b2c-4ddf-a310-ff6d960420f8/generate \
  -H "Content-Type: application/json" \
  -b "docmanagement_session=qf-6L6-OZcDxD6ZFwQ7iDGSw7i8_rTVPiEaVhfM_aoA" \
  -d '{
    "codigo": "C001",
    "Nombre": "Juan Pérez",
    "correo": "juan@example.com"
  }'
```

---

## 📓 Configuración en Postman

Para realizar pruebas en Postman enviando la cookie de sesión:

1. Ve a la pestaña **Headers** de tu petición.
2. Agrega una nueva cabecera con los siguientes datos:
   * **Key:** `Cookie`
   * **Value:** `docmanagement_session=qf-6L6-OZcDxD6ZFwQ7iDGSw7i8_rTVPiEaVhfM_aoA` (reemplaza con tu cookie activa).
3. Presiona **Send** para ejecutar la petición.
