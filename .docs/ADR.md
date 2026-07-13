# Registro de Decisiones Arquitectónicas (ADRs)

Este documento detalla las decisiones arquitectónicas clave tomadas durante el desarrollo de la plataforma **DocManagement**.

---

## ADR 01: Introducción del Patrón Backend-For-Frontend (BFF)

### Estado
**Aceptado**

### Contexto
Originalmente, la aplicación Frontend (React SPA) se comunicaba directamente con el Backend (FastAPI Core) y administraba los tokens JWT emitidos por Keycloak directamente en el almacenamiento local del navegador (`localStorage`). Esto presentaba vulnerabilidades de seguridad ante ataques de tipo Cross-Site Scripting (XSS) y obligaba a duplicar lógica de parseo, cabeceras y control de autenticación en el cliente.

### Decisión
Introducir una capa intermedia siguiendo el patrón **BFF (Backend-For-Frontend)** utilizando FastAPI.
* El BFF actúa como el único punto de contacto expuesto para el Frontend.
* Maneja el flujo OIDC con Keycloak de forma segura y almacena la información de sesión en cookies cifradas firmadas, con propiedades de seguridad `HttpOnly`, `Secure` y `SameSite=Lax`.
* El BFF intercepta las solicitudes del Frontend, valida las cookies de sesión, extrae/propaga los tokens necesarios hacia el Backend Core en una red privada y devuelve las respuestas.

### Consecuencias
* **Positivas**: Mayor seguridad (los tokens JWT nunca están expuestos al Javascript del navegador), simplificación drástica de la seguridad en el Frontend y aislamiento del backend en una red interna protegida.
* **Negativas**: Aumento de latencia mínima debido al salto de red adicional del proxy y necesidad de desplegar un contenedor de servicio extra.

---

## ADR 02: Adopción del Enfoque "Atomic Design" en el Frontend

### Estado
**Aceptado**

### Contexto
A medida que la aplicación crecía, los componentes visuales del Frontend se creaban de manera ad-hoc dentro de un directorio plano. Esto generaba duplicidad en estilos Tailwind, inconsistencia visual en márgenes, botones y elementos comunes de formulario, y dificultaba la reutilización de código entre páginas de administración.

### Decisión
Reorganizar y tipificar la estructura de componentes del Frontend utilizando la metodología **Atomic Design**:
* **Átomos (Atoms)**: Elementos HTML básicos y puros sin dependencias (ej. `InputText`, `Button`, `Select`, `Checkbox`, `Badge`, `StatusDot`).
* **Moléculas (Molecules)**: Agrupaciones sencillas de átomos que forman una unidad funcional (ej. `PageHeader`, `Pagination`, `TableHeader`, `IssuanceProperties`).
* **Organismos (Organisms)**: Estructuras complejas y autónomas con lógica integrada o que interactúan con APIs (ej. `PagedTable`, `SchemaFieldEditor`, `AddContentModal`).
* **Páginas (Pages)**: Vistas completas de la SPA que orquestan organismos y moléculas para formar los flujos de usuario.

### Consecuencias
* **Positivas**: Estructura de archivos limpia y predecible, consistencia en la interfaz de usuario, y facilidad para crear nuevas vistas reutilizando átomos y moléculas previamente auditados.
* **Negativas**: Mayor granularidad de archivos y necesidad de refactorizar múltiples declaraciones de importaciones en la base de código heredada.

---

## ADR 03: Abstracción y Desacoplamiento de Almacenamiento (Storage Decoupling)

### Estado
**Aceptado**

### Contexto
La plataforma almacenaba los archivos PDF de páginas estáticas y los PDF generados de las emisiones directamente en el sistema de archivos del servidor (rutas absolutas locales). Esto impedía desplegar múltiples instancias del backend de forma elástica en arquitecturas de nube (como Kubernetes) y acoplaba fuertemente los modelos de datos PostgreSQL a rutas físicas locales específicas de la máquina de desarrollo.

### Decisión
Independizar y abstraer la capa de almacenamiento de archivos binarios:
1. **Migración de Base de Datos**: Renombrar las columnas de rutas absolutas locales (`stored_path`, `file_path`) en los modelos a claves lógicas independientes (`storage_key`).
2. **Capa de Abstracción**: Crear la clase abstracta `StorageProvider` que exponga firmas para guardar, obtener bytes, transmitir flujos (streaming) y eliminar archivos.
3. **Proveedores concretos**:
   * `LocalStorageProvider`: Mantiene compatibilidad con el sistema de archivos de desarrollo usando directorios configurados.
   * `S3StorageProvider`: Consume clientes `boto3` para leer y escribir de forma nativa en buckets de almacenamiento de objetos compatibles con S3 (MinIO, AWS S3, Oracle, etc.).
4. **Propiedades de Compatibilidad**: Mantener en los modelos propiedades virtuales (`stored_path` / `file_path`) mapeadas a getters/setters dinámicos para asegurar compatibilidad total con suites de pruebas unitarias heredadas.

### Consecuencias
* **Positivas**: Capacidad de escalar el backend horizontalmente, compatibilidad nativa con arquitecturas Cloud-Native mediante almacenamiento de objetos, y mantenimiento de retrocompatibilidad con la suite de pruebas locales sin romper base de código.
* **Negativas**: Introducción de dependencias de red y latencia al consultar S3 en producción.
