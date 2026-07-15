# PRD5: Selector de registros por pagina en PagedTable

## 1. Vision general

El componente reutilizable `PagedTable` debe permitir que el usuario seleccione
cuantos registros se muestran por pagina. La seleccion debe estar disponible de
forma consistente en todas las paginas que usan `PagedTable`, sin duplicar el
control de UI en cada pagina.

Objetivo principal: convertir el tamano de pagina de una constante fija por
pagina (`PAGE_SIZE`) a un estado configurable por el usuario, usando un selector
reutilizable basado en el atomo `Select`.

## 2. Contexto actual

Actualmente `PagedTable` recibe:

- `page`
- `pageSize`
- `total`
- `onChangePage`

Pero `pageSize` solo se usa para calcular el rango visible en `Pagination`.
El componente no expone una forma de cambiar la cantidad de registros por
pagina.

Las paginas consumidoras calculan el paginado localmente con constantes fijas:

- `frontend/src/pages/content/StaticPdfsPage.tsx`: `PAGE_SIZE = 8`
- `frontend/src/pages/content/TemplatesPage.tsx`: `PAGE_SIZE = 8`
- `frontend/src/pages/document-types/DocumentTypeListPage.tsx`: `PAGE_SIZE = 10`

No existe un componente reutilizable llamado `ComboBox`. El componente
reutilizable disponible para este caso es:

- `frontend/src/components/atoms/Select.tsx`

## 3. Objetivo funcional

Agregar un selector "registros por pagina" en el area de paginacion de
`PagedTable` para que el usuario pueda elegir entre opciones predefinidas.

Opciones estandar requeridas:

```text
5, 10, 20, 50
```

El valor seleccionado debe aplicarse inmediatamente y la tabla debe volver a la
pagina 1 para evitar que el usuario quede en una pagina fuera de rango.

## 4. Diferencia entre props

### `pageSize`

Valor actual seleccionado.

Ejemplo:

```tsx
pageSize={10}
```

Significa que la tabla muestra 10 registros por pagina.

### `pageSizeOptions`

Lista de valores disponibles para seleccionar.

Ejemplo:

```tsx
pageSizeOptions={[5, 10, 20, 50]}
```

### `onChangePageSize`

Callback ejecutado cuando el usuario elige otra cantidad de registros por
pagina.

Ejemplo:

```tsx
onChangePageSize={(nextSize) => {
  setPageSize(nextSize);
  setPage(1);
}}
```

## 5. Cambios propuestos

### 5.1 `PagedTable`

Extender las props:

```tsx
pageSizeOptions?: number[];
onChangePageSize?: (pageSize: number) => void;
```

Mantener compatibilidad hacia atras:

- Si no se pasa `pageSizeOptions`, no se muestra selector.
- Si no se pasa `onChangePageSize`, no se muestra selector.
- Si ambos se pasan, `PagedTable` delega el selector a `Pagination`.

### 5.2 `Pagination`

Extender las props:

```tsx
pageSizeOptions?: number[];
onChangePageSize?: (pageSize: number) => void;
```

Renderizar un `Select` junto al texto de rango o junto a los controles de
navegacion.

Comportamiento:

- El valor del `Select` debe ser `pageSize`.
- Las opciones deben venir de `pageSizeOptions`.
- Al cambiar, convertir `event.target.value` a numero y llamar
  `onChangePageSize(nextSize)`.

Texto sugerido:

```text
Rows per page
```

Se mantiene en ingles para conservar consistencia con el texto actual
`Showing X-Y of Z`.

### 5.3 Paginas consumidoras

Actualizar todas las paginas que usan `PagedTable`.

#### Static PDFs

Archivo:

```text
frontend/src/pages/content/StaticPdfsPage.tsx
```

Cambios:

- Reemplazar `const PAGE_SIZE = 8` por:

```tsx
const [pageSize, setPageSize] = useState(8);
```

- Usar `pageSize` en el calculo `slice`.
- Pasar a `PagedTable`:

```tsx
pageSize={pageSize}
pageSizeOptions={[5, 10, 20, 50]}
onChangePageSize={(nextSize) => {
  setPageSize(nextSize);
  setPage(1);
}}
```

#### Templates

Archivo:

```text
frontend/src/pages/content/TemplatesPage.tsx
```

Cambios:

- Reemplazar `const PAGE_SIZE = 8` por estado `pageSize`.
- Usar `pageSize` en el calculo `slice`.
- Pasar `pageSizeOptions` y `onChangePageSize` a `PagedTable`.

#### Document Types

Archivo:

```text
frontend/src/pages/document-types/DocumentTypeListPage.tsx
```

Cambios:

- Reemplazar `const PAGE_SIZE = 10` por estado `pageSize`.
- Usar `pageSize` en el calculo `slice`.
- Pasar `pageSizeOptions` y `onChangePageSize` a `PagedTable`.

## 6. Criterios de aceptacion

1. `PagedTable` sigue funcionando en modo actual si no recibe
   `pageSizeOptions` ni `onChangePageSize`.
2. `PagedTable` muestra un selector de registros por pagina cuando recibe ambas
   props.
3. `Pagination` usa el atomo reutilizable `Select`.
4. Static PDFs permite cambiar entre 5, 10, 20 y 50 registros por pagina.
5. Templates permite cambiar entre 5, 10, 20 y 50 registros por pagina.
6. Document Types permite cambiar entre 5, 10, 20 y 50 registros por pagina.
7. Al cambiar el tamano de pagina, la pagina actual vuelve a 1.
8. El texto de rango `Showing X-Y of Z` se recalcula correctamente.
9. Los botones de pagina se recalculan correctamente.
10. El build frontend finaliza sin errores.

## 7. Verificacion

Comando requerido:

```powershell
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Verificacion manual:

- Abrir Static PDFs, Templates y Document Types.
- Cambiar el selector entre 5, 10, 20 y 50.
- Confirmar que la tabla cambia la cantidad visible de filas.
- Confirmar que el rango mostrado cambia.
- Confirmar que la pagina vuelve a 1.
- Confirmar que la navegacion siguiente/anterior sigue funcionando.

## 8. Fuera de alcance

- Persistir la preferencia en `localStorage`.
- Configurar opciones distintas por usuario.
- Crear un nuevo componente `ComboBox`.
- Cambiar el contrato de backend.
- Convertir el paginado local a paginado server-side.

## 9. Supuestos

- Se usara `Select` como control reutilizable.
- Las opciones estandar seran `[5, 10, 20, 50]`.
- El texto del control puede permanecer en ingles para mantener consistencia
  con `Pagination`.
- Las paginas consumidoras mantendran paginado local con `slice`.
