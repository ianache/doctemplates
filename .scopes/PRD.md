# Documento de Requisitos del Producto (PRD)
## Módulo: Diseñador de Maquetas de Documentos Digitales (DocManagement)
## 1. Visión General del Producto
El objetivo es permitir a los usuarios operativos de **DocManagement** diseñar visualmente maquetas de documentos contractuales o actas de instalación. El sistema debe componer documentos combinando de manera ordenada páginas de **PDFs estáticos** (ej. términos y condiciones) y **plantillas dinámicas** escritas en HTML con marcadores (tokens) que se reemplazan automáticamente con los datos de las tramas operativas integradas en la plataforma.
## 2. Reglas de Negocio Críticas (VibeCoding Context)
 1. **Asociación Estricta:** Cada maqueta pertenece exclusivamente a una combinación única de **Canal de Venta** y **Servicio Específico** registrada dentro del ecosistema de **DocManagement**.
 2. **Filtrado Dinámico de Marcadores:** * Si el servicio seleccionado es **Básico** (B2C / Personas Naturales), el sistema debe deshabilitar y ocultar del panel de marcadores los atributos avanzados de flota.
   * Los marcadores autorizados para el **Servicio Básico** son exclusivamente: ubicación, parqueos seguros y bloqueo de unidades (corte de motor).
   * Si el servicio seleccionado es de **Flota** (B2B / Personas Jurídicas), se habilitan los marcadores avanzados: gestión de convoy, geo-cercas avanzadas, rutas, controles de rutas, bloqueo de puertas y controles de temperatura.
## 3. Especificaciones del BFF (Backend For Frontend)
El BFF simplificará la interfaz de usuario formateando los datos y gestionando la composición previa antes de transferir las solicitudes al módulo central.
### Endpoints del BFF
#### 1. Configuración Inicial
 * **Endpoint:** GET /api/bff/maquetas/configuracion-inicial
 * **Propósito:** Retornar los catálogos para los selectores obligatorios en la cabecera.
 * **Response (200 OK):**
```json
{
  "canales_venta": [
    { "id": "CANAL-FIN-01", "nombre": "Financiera BCP" },
    { "id": "CANAL-FIN-02", "nombre": "Financiera Efectiva" }
  ],
  "servicios": [
    { "id": "SERV-SAT-BASICO", "nombre": "Servicio Básico", "tipo": "B2C" },
    { "id": "SERV-SAT-FLOTA", "nombre": "Servicio de Flota", "tipo": "B2B" }
  ]
}

```
#### 2. Filtrado de Marcadores Contextuales
 * **Endpoint:** GET /api/bff/maquetas/marcadores?canal_venta_id={id}&servicio_id={id}
 * **Propósito:** Interceptar la matriz de datos completa y retornar únicamente las variables autorizadas para la UI según el tipo de servicio seleccionado.
 * **Response (200 OK) - Caso Servicio Básico:**
```json
{
  "cliente": ["cliente.nombre", "cliente.documento", "cliente.telefono"],
  "unidad": ["unidad.marca", "unidad.modelo", "unidad.placa", "unidad.chasis"],
  "cita": ["cita.fecha", "cita.hora", "cita.tecnico_asignado"],
  "canal": ["canal.nombre_financiera", "canal.plazo_credito"]
}

```
*(Nota para la IA: Si servicio_id es SERV-SAT-BASICO, el BFF remueve estrictamente del alcance variables como unidad.sensor_temperatura y unidad.bloqueo_puertas).*
#### 3. Persistencia de la Estructura de la Maqueta
 * **Endpoint:** POST /api/bff/maquetas
 * **Payload de entrada:**
```json
{
  "nombre_maqueta": "Contrato Vehicular Básico - Financiera Efectiva",
  "canal_venta_id": "CANAL-FIN-02",
  "servicio_id": "SERV-SAT-BASICO",
  "paginas": [
    {
      "orden": 1,
      "tipo_contenido": "PLANTILLA_DINAMICA",
      "html_contenido": "<h1>CONTRATO</h1><p>Cliente: {{cliente.nombre}} con DNI {{cliente.documento}}</p>",
      "pdf_estatico_path": null,
      "pagina_origen_especifica": null
    },
    {
      "orden": 2,
      "tipo_contenido": "PDF_ESTATICO",
      "html_contenido": null,
      "pdf_estatico_path": "storage/repositorio/terminos_legales.pdf",
      "pagina_origen_especifica": 1
    }
  ]
}

```
#### 4. Previsualización con Datos Simulados (Mocking Express)
 * **Endpoint:** POST /api/bff/maquetas/previsualizar
 * **Propósito:** Recibe el JSON actual del diseñador frontend, inyecta datos mock contextualizados y devuelve el PDF binario consolidado.
## 4. Pipeline de Procesamiento y Fusión del Backend (DocManagement Core)
Al recibir la orden de generación de PDF (POST a previsualizar o emisión real gatillada por el ingreso de una trama operativa autorizada), el núcleo de **DocManagement** debe ejecutar de manera síncrona el siguiente flujo de renderizado:
### Paso 1: Resolución de Variables (Interpolación)
 * **Acción:** Evaluar las cadenas de texto encontradas en el atributo html_contenido.
 * **Lógica:** Utilizar un motor ligero de plantillas (ej. Handlebars o Mustache) para sustituir los tokens {{...}} por los valores reales o mock provistos por la plataforma.
### Paso 2: Conversión HTML a PDF
 * **Acción:** Instanciar un renderizador headless (ej. Puppeteer o Weasyprint).
 * **Lógica:** Tomar el HTML resuelto del Paso 1 y generar en memoria un buffer PDF independiente para cada registro de tipo PLANTILLA_DINAMICA.
### Paso 3: Segmentación de PDFs Estáticos
 * **Acción:** Localizar los archivos del almacenamiento indicados en pdf_estatico_path.
 * **Lógica:** Si pagina_origen_especifica no es nula, extraer únicamente el index de página requerido y descartar el resto del buffer del documento base para ahorrar recursos.
### Paso 4: Fusión Final (Merge)
 * **Acción:** Unificar todas las piezas de páginas resultantes mediante una librería de manipulación de PDF (ej. pdf-lib en Node o PyPDF2 en Python).
 * **Lógica:** Insertar ordenadamente las páginas respetando la propiedad secuencial de la llave "orden". Retornar el archivo unificado en formato binario (application/pdf).
## 5. Criterios de Aceptación Técnicos
 1. El lienzo de arrastrar y soltar de **DocManagement** debe forzar el bloqueo inicial si no se seleccionan Canal y Servicio en la cabecera.
 2. El reordenamiento en la interfaz debe actualizar la propiedad indexada "orden" numéricamente en la estructura del array antes de despachar el payload al BFF.
 3. Cualquier intento de inyectar variables de telemetría de flota avanzada en un entorno configurado como Servicio Básico debe retornar error 400 Bad Request de manera inmediata en el backend.