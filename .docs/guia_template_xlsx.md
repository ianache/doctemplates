# Miniguia: Crear una plantilla XLSX en Microsoft Excel

## 1. Crear el archivo base

1. Abre Microsoft Excel.
2. Disena el workbook con las hojas, tablas, estilos, formulas y celdas que quieras conservar.
3. Guarda el archivo como `.xlsx`.

No uses `.xls`, `.xlsm`, macros ni VBA.

## 2. Insertar campos dinamicos

En las celdas donde quieras valores del documento, usa tokens con doble llave:

```text
{{cliente.nombre}}
{{cliente.ruc}}
{{contrato.fecha}}
{{total}}
```

Los nombres deben coincidir con los campos definidos en el tipo de documento del sistema.

## 3. Usar listas repetibles

Para filas repetibles, usa tokens con prefijo `item.` en la fila modelo:

```text
{{item.descripcion}}
{{item.cantidad}}
{{item.precio}}
```

Luego agrega metadata en una celda auxiliar, por ejemplo `Z1`:

```json
[{"sheet":"Items","row":2,"list":"items"}]
```

Despues, en Excel:

1. Ve a **Formulas > Name Manager**.
2. Crea un nombre llamado:

```text
_docman_repeats
```

3. Haz que apunte a la celda auxiliar, por ejemplo:

```text
='Items'!$Z$1
```

Esto indica que la fila `2` de la hoja `Items` se repetira usando la lista `items`.

## 4. Definir espacios para imagenes

Si necesitas insertar imagenes desde datos, agrega metadata en una celda auxiliar, por ejemplo `Z2`:

```json
[{"sheet":"Summary","cell":"D4","field":"brand.logo"}]
```

Luego crea un nombre en **Name Manager**:

```text
_docman_images
```

Apuntando a esa celda:

```text
='Summary'!$Z$2
```

El campo `brand.logo` debe contener una imagen compatible, por ejemplo base64 PNG/JPEG.

## 5. Recomendaciones

- Usa una fila modelo clara para listas repetibles.
- Evita combinar celdas dentro de filas repetibles si no es necesario.
- Mantén las celdas auxiliares lejos del area visible, por ejemplo columna `Z`.
- Puedes ocultar columnas auxiliares, pero no borres las celdas ni los nombres definidos.
- Define el area de impresion si quieres controlar mejor la vista previa.

## 6. Subida al sistema

1. Sube el archivo `.xlsx` como plantilla XLSX.
2. Revisa los tokens detectados.
3. Corrige cualquier warning de tokens desconocidos o metadata invalida.
4. Usa la vista previa del sistema como aproximacion; el archivo descargado es la salida definitiva.
