# Documento de Requisitos del Producto (PRD) MVP2

En este MVP 2 se requiere realizar mejoras al diseño de las plantillas de documentos, en los documents types

En este MVP 2 se requiere incorporar capacidad para consultar la biblioteca de documento generados a partir de las plantillas de documentos.


## Document Types

- permitir que los tokens pueden ser objetos ((por ejemplo, `cliente`)) con atributos (por ejemplo, `codigo`) simples accesibles en formato `{{cliente.codigo}}` y que sean case insensitive.
- permitir que los tokens puedan incluir atributos que representen listados de objetos para poder renderizar estructuras de tipos tablas, por ejemplo una cita puede tener un listado de articulos a instalar en un vehiculo, o una Orden de Venta puede tener un listado de articulos con codigo, cantidad, precio.

## Search Documents Library

- Cuando se especifique los datos para busqueda simple por nombre, id, estado o rango de fecha entonces se recuperan los documentos y se presenta un listado con todos los documentos que cumplen los criterios de búsqueda bajo AND condition (@.design\mvp2\search_repository.html)
- Cuando se seleccione un documento enonces se debe poder visualizar el contenido del documento seleccionado conforme @.design\mvp2\document_view.html
- Cuando se seleccione ver detalle de log de cambio del documento visualizado conforme a @.design\mvp2\document_tracelog.html
- Cuando se seleccione `Exportar PDF` entonces se debe permitir la descarga del documento.
- Cuando se seleccione `Share` entonces se debe copiar al clickboard la URL hacia el contenido del documento (en este MVP no se establece protección de acceso a los documentos, pero en MVP posteriores deben existir restricciones de acceso al contenido para las URL compartidas)

## UX/UI aplicados

- Busqueda de documentos: @.design\mvp2\search_repository.html
- Visualización del documento: @.design\mvp2\document_view.html
- Document tracelog: @.design\mvp2\document_tracelog.html
- Document Types con campos complejos: @.design\mvp2\plantilla_objetos_campos_complejos_previsualiazcion.html