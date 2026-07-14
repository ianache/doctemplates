# Propuesta y Evaluación de Atomic Design en DocManagement

Este documento presenta una propuesta estructurada para clasificar los componentes de la interfaz de usuario de **DocManagement** bajo el patrón **Atomic Design**, analizando su distribución actual y evaluando el impacto arquitectónico de su adopción formal.

---

## 1. Clasificación Actual vs. Propuesta de Descomposición

El proyecto frontend de `DocManagement` ya cuenta con directorios iniciales para `atoms`, `molecules` y `organisms`. Sin embargo, existen componentes no clasificados en la raíz de `src/components` y componentes locales dentro de las carpetas de las páginas (`src/pages/.../components`). 

A continuación se detalla la propuesta de catalogación completa en los 5 niveles del patrón:

### 1.1. Átomos (Atoms)
*Los componentes visuales e interactivos más básicos y elementales que no se pueden descomponer más sin perder su función.*

*   **Existentes:**
    *   `Button.tsx` (en `src/components/atoms`): Botón genérico con variantes de estilos.
    *   `Icon.tsx` (en `src/components/atoms`): Renderizador de iconos de material design.
    *   `Badge.tsx` (en `src/components/atoms`): Etiquetas de estado visuales (ej. B2C, B2B).
    *   `StatusDot.tsx` (en `src/components/atoms`): Punto indicador de estados (Signed, Draft, Archived).
*   **Propuestos (a extraer del código inline actual):**
    *   `InputText.tsx` / `Select.tsx`: Wrappers estilizados para campos de texto y combos de selección (ej. selectores de Canal de Venta y Servicio, actualmente definidos con Tailwind directamente en las páginas).
    *   `Checkbox.tsx` / `ToggleSwitch.tsx`: Para controles de activación/desactivación en formularios.
    *   `BreadcrumbItem.tsx`: Elemento individual de navegación de cabecera.
    *   `PageThumbnail.tsx`: Representación visual reducida (miniatura) de una página individual dentro del diseñador.

### 1.2. Moléculas (Molecules)
*Combinaciones de átomos que actúan juntos como una unidad funcional simple.*

*   **Existentes:**
    *   `TableHeader.tsx` (en `src/components/molecules`): Cabeceras para ordenamiento en tablas.
    *   `Pagination.tsx` (en `src/components/molecules`): Botones y etiquetas para la paginación.
    *   `DateRange.tsx` (en `src/components/molecules`): Selector de rango de fechas combinando dos inputs.
*   **Propuestos (para reclasificar desde la raíz o locales):**
    *   `PageHeader.tsx` (actualmente en `src/components/PageHeader.tsx`): Agrupa breadcrumbs (`BreadcrumbItem`) y el título de la página (`h2`) junto con un contenedor de acciones (`Button`s).
    *   `DesignPageCard.tsx` (actualmente en `src/pages/document-designs/components/DesignPageCard.tsx`): Tarjeta que representa una página en la maqueta, integrando el número de orden, el tipo de página y botones de acción rápida.
    *   `FormField.tsx`: Componente que une una etiqueta (`label`), un campo de entrada (`InputText`/`Select`) y un mensaje de validación o ayuda.

### 1.3. Organismos (Organisms)
*Componentes complejos integrados por moléculas y/o átomos que forman una sección distintiva y funcional de la interfaz.*

*   **Existentes:**
    *   `PagedTable.tsx` (en `src/components/organisms`): Composición de tablas que integra `TableHeader` y `Pagination`.
*   **Propuestos (para reclasificar desde la raíz o locales):**
    *   `HtmlJinjaEditor.tsx` (actualmente en `src/components/HtmlJinjaEditor.tsx`): El editor visual basado en Tiptap con extensiones para tags de Jinja y comportamiento de drag-and-drop.
    *   `TokenExplorer.tsx` (actualmente en `src/components/TokenExplorer.tsx`): Árbol jerárquico interactivo de marcadores (tokens), con lógica de colapso, iconos y drag-and-drop.
    *   `AddContentModal.tsx` (actualmente en `src/pages/document-designs/components/AddContentModal.tsx`): Diálogo modal para agregar páginas estáticas o plantillas dinámicas.
    *   `DesignPageInspector.tsx` (actualmente en `src/pages/document-designs/components/DesignPageInspector.tsx`): Formulario/panel lateral para configurar la página seleccionada en el diseñador (orden, tipo, pdf_estatico_path).
    *   `MockDataPanel.tsx` (actualmente en `src/pages/document-designs/components/MockDataPanel.tsx`): Panel con editor de JSON para la simulación de previsualización.
    *   `PreviewFrame.tsx` (actualmente en `src/pages/document-designs/components/PreviewFrame.tsx`): Contenedor de la previsualización del documento generado (iframe + loader).
    *   `SchemaFieldEditor.tsx` (actualmente en `src/pages/document-types/components/SchemaFieldEditor.tsx`): Editor de campos dinámicos para esquemas de datos del tipo de documento.
    *   `SchemaMetadataEditor.tsx` (actualmente en `src/pages/document-types/components/SchemaMetadataEditor.tsx`): Panel de metadatos del esquema.

### 1.4. Plantillas (Templates)
*Estructuras de diseño a nivel de página que distribuyen los componentes en una cuadrícula o esqueleto. No contienen lógica de negocio ni llamadas a APIs directamente, solo definen slots (children / props).*

*   **Propuestos:**
    *   `ShellLayout.tsx` (basado en `AuthenticatedShell.tsx`): Define la estructura global de la aplicación (Sidebar lateral de navegación + Barra superior de usuario + Área de scroll principal).
    *   `WorkspaceLayout.tsx`: Estructura de 3 columnas para herramientas de diseño/edición (Panel izquierdo para exploradores, Centro para el lienzo/canvas, Panel derecho para inspectores de propiedades). Utilizado por `DocumentDesignDetailPage.tsx`.
    *   `AdminListLayout.tsx`: Estructura estándar para listados (Filtros de búsqueda superiores + Tabla de datos central + Paginación inferior). Utilizado por las páginas de listado.
    *   `FormConfigLayout.tsx`: Estructura para pantallas de creación/edición tipo formulario (Cabecera simplificada con botón de retorno + Contenedor de formulario de ancho controlado).

### 1.5. Páginas (Pages)
*Instancias concretas donde las plantillas se inyectan con datos reales provenientes de la API, se conectan con hooks de estado/rutas de React, y manejan los eventos globales.*

*   **Estructura actual en `src/pages` (manteniendo su flujo):**
    *   `LoginPage.tsx` (Inicio de sesión)
    *   `AuthenticatedShell.tsx` (Shell/Wrapper autenticado)
    *   **Módulo Document Types:**
        *   `DocumentTypeListPage.tsx`
        *   `DocumentTypeCreatePage.tsx`
        *   `DocumentTypeDetailPage.tsx`
    *   **Módulo Document Designs (Maquetas):**
        *   `DocumentDesignListPage.tsx`
        *   `DocumentDesignCreatePage.tsx`
        *   `DocumentDesignDetailPage.tsx` (El diseñador principal)
        *   `VersionHistoryPage.tsx`
    *   **Módulo Document Issuances (Biblioteca / Emisiones):**
        *   `DocumentLibraryPage.tsx`
        *   `DocumentIssuanceDetailPage.tsx`
    *   **Módulo Content:**
        *   `TemplatesPage.tsx`
        *   `HtmlTemplateCreatePage.tsx`
        *   `HtmlTemplateDetailPage.tsx`
        *   `StaticPdfsPage.tsx`
        *   `StaticPdfUploadPage.tsx`
        *   `StaticPdfDetailPage.tsx`

---

## 2. Impacto en su uso en la Actual Implementación

### 2.1. Beneficios e Impacto Positivo

1.  **Eliminación de la inconsistencia en `src/components`:**
    *   *Actual:* Componentes como `HtmlJinjaEditor`, `TokenExplorer` y `PageHeader` se encuentran "sueltos" en la carpeta raíz de componentes, rompiendo la estructura de carpetas `atoms`, `molecules` y `organisms`.
    *   *Solución:* Su reubicación formal bajo `organisms` y `molecules` respectivamente clarifica la arquitectura para cualquier nuevo desarrollador.
2.  **Centralización y Estandarización de Estilos inline (Fuerza del UI/UX):**
    *   Al extraer inputs, selectores y contenedores de formularios repetidos en `DocumentTypeCreatePage` y `DocumentDesignCreatePage` hacia Átomos y Moléculas (`InputText`, `Select`, `FormField`), se garantiza que cualquier cambio de diseño (ej. bordes de foco, colores de error, tipografías) se propague uniformemente en todo el sistema.
3.  **Independencia de los Layouts (Templates) frente a la Lógica:**
    *   Actualmente, el esqueleto visual de la página de diseño `DocumentDesignDetailPage.tsx` (la distribución de los paneles laterales y el iframe central) está muy acoplada con las llamadas a la API y el estado del editor. Al abstraer un `WorkspaceLayout`, este se vuelve 100% reutilizable si en el futuro se crea un editor de plantillas HTML independiente o un diseñador de esquemas.
4.  **Testabilidad y Aislamiento:**
    *   Los átomos y moléculas se vuelven puramente presentacionales. Es mucho más sencillo probarlos con herramientas como **Storybook** o pruebas unitarias debido a la ausencia de dependencias con contextos globales de enrutamiento o estados del servidor.

### 2.2. Riesgos y Desventajas (Costos de Adopción)

1.  **Dificultad en la Búsqueda de Componentes Específicos de Dominio (Bloat en carpetas globales):**
    *   Componentes como `SchemaFieldEditor` o `DesignPageInspector` no tienen sentido en ninguna otra parte de la aplicación fuera de su respectiva página. Colocarlos en un directorio global de `organisms` (`src/components/organisms`) puede saturar la carpeta con elementos de un único uso, dificultando la navegación en el proyecto.
2.  **Complejidad en la Propagación de Estados (Props Drilling / Callbacks):**
    *   Al separar componentes de edición compleja en Átomos, Moléculas y Organismos separados del contenedor de la Página, se incrementa la cantidad de propiedades y callbacks necesarios para intercomunicar el canvas del editor (`HtmlJinjaEditor`) con el inspector lateral (`DesignPageInspector`) y el árbol de tokens (`TokenExplorer`).

---

## 3. Recomendación: Modelo Atómico Híbrido (Propuesta de Mitigación)

Para mitigar los riesgos de saturar las carpetas globales con componentes muy específicos, se propone adoptar un **Modelo Atómico Híbrido**:

```
src/
├── components/           <-- Componentes compartidos globales
│   ├── atoms/            <-- Button, Icon, Badge, StatusDot, InputText
│   ├── molecules/        <-- TableHeader, Pagination, DateRange, PageHeader
│   └── organisms/        <-- PagedTable
│
├── pages/                <-- Páginas y sus componentes específicos
│   ├── document-designs/
│   │   ├── components/   <-- Siguen el patrón pero viven a nivel de módulo
│   │   │   ├── molecules/ <-- DesignPageCard
│   │   │   └── organisms/ <-- HtmlJinjaEditor, TokenExplorer, DesignPageInspector, MockDataPanel
│   │   ├── DocumentDesignDetailPage.tsx  <-- Integra la página
│   │   └── ...
│   └── ...
```

### Justificación:
*   Mantiene los **Átomos y Moléculas transversales** en la raíz global (`src/components`), permitiendo reutilizar el sistema de diseño (botones, formularios, tablas).
*   Mantiene la **cohesión del módulo de negocio** al alojar componentes especializados (`HtmlJinjaEditor`, `TokenExplorer`) dentro de la subcarpeta del módulo correspondiente, evitando la dispersión del código.
