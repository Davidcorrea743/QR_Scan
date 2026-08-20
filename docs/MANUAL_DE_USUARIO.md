# Manual de Usuario — Sistema de Carnets QR

Bienvenido al manual de uso del sistema de carnets con código QR. Aquí aprenderás, paso a paso, a:

1. **Registrar empleados uno por uno** (carga individual).
2. **Registrar muchos empleados a la vez** con un archivo CSV y sus fotos (carga masiva).
3. **Preparar el archivo de Excel** en el formato correcto para exportarlo a CSV.

No se requieren conocimientos técnicos. Sigue las instrucciones en orden y no tendrás dudas.

---

## 1. Acceso al sistema

1. Abre tu navegador (Chrome o Edge recomendados).
2. Entra a la dirección del sistema (te la entrega el administrador, por ejemplo: `http://192.168.183.110:8000`).
3. Se mostrará la pantalla de inicio de sesión.

![Pantalla de inicio de sesión](img/01-inicio-sesion.png)

4. Escribe tu **usuario** y tu **contraseña**.
5. Pulsa el botón **Ingresar**.

> ⚠️ **Primer acceso:** si es tu primera vez, el sistema te pedirá cambiar la contraseña. Es obligatorio hacerlo.

> ℹ️ **Rol del usuario:**
> - **Administrador:** puede crear, editar, desactivar empleados y hacer cargas masivas.
> - **Editor:** solo puede actualizar el teléfono y el correo de los empleados.

---

## 2. El panel principal

Después de ingresar verás el **Panel de Empleados**, donde aparece la lista de todos los trabajadores.

![Panel principal de empleados](img/02-panel.png)

Aquí tienes dos botones para agregar personal:

| Botón | Para qué sirve |
|---|---|
| **+ Nuevo empleado** | Registrar **uno por uno** (carga individual). |
| **Carga masiva** | Registrar **muchos a la vez** con un archivo CSV (y fotos). |

> 💡 El botón **Carga masiva** solo lo ven los administradores.

---

## 3. Carga individual de un empleado

Usa este método cuando solo necesites registrar **una o pocas personas** (ej. un nuevo ingreso).

1. En el panel, pulsa **+ Nuevo empleado**.
2. Se abre el formulario con los siguientes campos:

| Campo | ¿Obligatorio? | Qué escribir |
|---|---|---|
| **Nombre** | ✅ Sí | Nombre del trabajador, ej. `Ana` |
| **Apellido** | ✅ Sí | Apellido del trabajador, ej. `López` |
| **Cédula** | No | Número de cédula, ej. `12345678` |
| **Cargo** | No | Puesto de trabajo, ej. `Desarrollador` |
| **Correo corporativo** | No | Correo de la empresa, ej. `ana@empresa.com` |
| **Teléfono / WhatsApp** | No | Número de contacto, ej. `04121234567` |
| **Foto del empleado** | No | Foto en formato PNG, JPG o WEBP |

![Formulario de nuevo empleado](img/03-formulario.png)

3. Completa los campos y, si deseas, adjunta la foto.
4. Pulsa **Guardar**.

![Pantalla de éxito al guardar](img/04-exito.png)

5. Al guardar, el sistema te muestra tres opciones:
   - **Ver carnet imprimible:** abre el carnet listo para imprimir.
   - **Ver perfil público:** lo que verá una persona al escanear el QR del carnet.
   - **Volver al panel:** regresa a la lista de empleados.

> ℹ️ **Para editar un empleado:** en la lista del panel, pulsa **Editar** en la fila del empleado. El formulario se abre con los datos cargados.

---

## 4. Carga masiva de empleados (CSV + fotos)

Usa este método cuando tengas **muchos empleados por registrar** (ej. todo el personal nuevo de una vez). Requiere dos pasos previos: preparar el archivo **CSV** y, si tienes fotos, un **ZIP** con ellas.

### 4.1. ¿Dónde está el botón?

1. En el panel, pulsa **Carga masiva** (solo visible para administradores).
2. Se abre una ventana (modal) con dos campos:

![Ventana de carga masiva](img/05-carga-masiva.png)

- **Archivo CSV** *(obligatorio)*: el archivo con los datos de los empleados.
- **Fotos (ZIP)** *(opcional)*: el archivo comprimido con las fotos.

### 4.2. Pasos

1. Pulsa **Carga masiva**.
2. Adjunta el archivo **CSV** en el campo *Archivo CSV*.
3. Adjunta el archivo **ZIP** con las fotos en el campo *Fotos (ZIP)* (solo si vas a cargar fotos).
4. Pulsa **Cargar**.

![Reporte de resultado de la carga](img/06-resultado.png)

El sistema procesa el archivo **fila por fila** y te muestra un resumen:

| Resultado | Significado |
|---|---|
| **Importados** | Cuántos empleados se crearon correctamente. |
| **Omitidos (ya existían)** | Empleados que ya estaban registrados (por cédula) y no se volvieron a crear. |
| **Errores** | Filas con problemas y el motivo (ej. falta el nombre). |

5. Cuando termines, la lista de empleados se actualiza sola.

---

## 5. Formato del archivo Excel / CSV

El archivo de datos debe tener **una fila por empleado** y estas columnas **en este orden** (como encabezados):

```
nombre, apellido, cargo, cedula, telefono, correo, foto
```

### 5.1. Explicación de cada columna

| Columna | ¿Obligatoria? | Ejemplo | Notas |
|---|---|---|---|
| `nombre` | ✅ Sí | `Ana` | Nombre del trabajador |
| `apellido` | ✅ Sí | `López` | Apellido del trabajador |
| `cargo` | No | `Desarrollador` | Puesto de trabajo |
| `cedula` | No | `12345678` | Cédula. **Debe ser única**: si ya existe, esa fila se omite |
| `telefono` | No | `04121234567` | Número de contacto |
| `correo` | No | `ana@empresa.com` | Correo de la empresa |
| `foto` | No | `ana.jpg` | Nombre exacto del archivo de la foto dentro del ZIP (ver sección 6) |

### 5.2. Cómo se ve en Excel

![Archivo Excel con los datos de empleados](img/07-excel.png)

Ejemplo de 3 filas listas para exportar:

```
nombre,apellido,cargo,cedula,telefono,correo,foto
Ana,López,Desarrollador,12345678,04121234567,ana@empresa.com,ana.jpg
Luis,García,Analista,87654321,04169876543,luis@empresa.com,
María,Pérez,Supervisora,11223344,04241234567,maria@empresa.com,11223344.jpg
```

> 💡 Fíjate en la fila de Luis: la columna `foto` está **vacía**, así que ese empleado quedará sin foto (el carnet mostrará una imagen de respaldo). No es un error.

### 5.3. Exportar de Excel a CSV

1. En Excel, termina de llenar el archivo con los datos de todos los empleados.
2. Ve a **Archivo → Guardar como**.
3. Elige como tipo de archivo: **CSV UTF-8 (delimitado por comas)**.
   - Si tu versión de Excel no lo muestra, usa **CSV (delimitado por comas)**.
4. Nombra el archivo (ej. `empleados.csv`) y guárdalo.

> ✅ El sistema acepta separadores de **coma (`,`)** y de **punto y coma (`;`)**, y también tildes y caracteres como `ñ`, `á`, `é`. No hace falta preocuparse si el Excel de tu región usa punto y coma.

> ❌ **No uses** "Libro de Excel" (.xlsx) ni "PDF". El sistema solo lee archivos **.csv**.

---

## 6. Cómo preparar el ZIP de fotos

Las fotos no pueden ir dentro del CSV, por eso se entregan en un archivo comprimido **ZIP**. El sistema las empareja automáticamente.

### 6.1. La regla de oro: el nombre del archivo

Cada foto debe llamarse **igual que la cédula** del empleado:

- Cédula `12345678` → foto `12345678.jpg`
- Cédula `87654321` → foto `87654321.png`

Formatos permitidos: **.jpg, .jpeg, .png, .webp**.

![Carpeta de fotos nombradas por cédula](img/08-zip-fotos.png)

### 6.2. Pasos para crear el ZIP

1. Crea una carpeta en tu computadora y guarda ahí **todas las fotos**, cada una con el nombre de la cédula del empleado.
2. Selecciona todas las fotos, haz clic derecho → **Enviar a → Carpeta comprimida (zip)**.
3. Resulta un archivo como `fotos.zip`.

> 💡 **Opcional:** si una foto no tiene el nombre de la cédula, puedes indicar el nombre exacto del archivo en la columna `foto` del CSV. Por ejemplo, columna `foto` = `ana.jpg` y dentro del ZIP el archivo `ana.jpg`. Si la columna `foto` está vacía, el sistema busca la foto por cédula.

### 6.3. Recomendaciones

- Usa fotos tipo documento (fondo claro, rostro de frente).
- El sistema recorta y ajusta la foto automáticamente (formato cuadrado), así que no necesitas editarlas.
- Fotos de hasta 5 MB cada una.

---

## 7. Reglas automáticas del sistema

Para que los carnets se vean limpios y uniformes, el sistema **normaliza** los datos sin que hagas nada:

| Campo | Qué hace el sistema |
|---|---|
| **Nombre y apellido** | Convierte a mayúscula inicial: `pEpITO PEREZ` → `Pepito Perez` |
| **Cargo** | Igual: `desaRROLLAdoR` → `Desarrollador` |
| **Correo** | Lo guarda en minúsculas: `ANA@Empresa.com` → `ana@empresa.com` |
| **Cédula y teléfono** | Los deja tal como los escribiste (solo quita espacios de más) |

> ✅ Esto también se aplica a los empleados que ya estaban registrados antes.

---

## 8. Preguntas frecuentes

**¿Qué pasa si en el CSV repito una cédula que ya existe?**
Esa fila se **omite** y aparece en el resumen como *Omitidos (ya existían)*. El empleado anterior no se modifica.

**¿Puedo cargar empleados sin fotos?**
Sí. Deja la columna `foto` vacía o no adjuntes el ZIP. El carnet usará una imagen de respaldo.

**¿Qué pasa si el CSV tiene una fila con error (ej. sin nombre)?**
Solo se salta esa fila y se reporta en el resumen con su número de fila y el motivo. El resto se carga normal.

**¿Los datos en mayúsculas se ven mal en el carnet?**
No. El sistema normaliza nombre, apellido y cargo automáticamente.

**¿Puede un editor hacer cargas masivas?**
No. Solo el administrador. El editor solo actualiza teléfono y correo.

**¿Qué formatos de foto acepta el sistema?**
PNG, JPG, JPEG y WEBP.

---

## Anexo: imágenes para completar el manual

Cada imagen está en la carpeta `img/` junto a este manual, con el nombre indicado. Para que el manual se vea completo, toma las capturas y reemplaza (con el mismo nombre) los archivos de la tabla:

| # | Nombre del archivo | Qué debe mostrar la captura |
|---|---|---|
| 01 | `01-inicio-sesion.png` | Pantalla de inicio de sesión (usuario, contraseña, botón Ingresar). |
| 02 | `02-panel.png` | Panel de empleados con los botones **+ Nuevo empleado** y **Carga masiva** visibles. |
| 03 | `03-formulario.png` | Formulario de nuevo empleado con algunos campos llenos. |
| 04 | `04-exito.png` | Pantalla de éxito tras guardar (con los botones Ver carnet / Ver perfil / Volver al panel). |
| 05 | `05-carga-masiva.png` | Ventana (modal) de carga masiva con los campos CSV y ZIP. |
| 06 | `06-resultado.png` | Resumen de resultados tras cargar (importados / omitidos / errores). |
| 07 | `07-excel.png` | Archivo de Excel con las columnas llenas (una fila por empleado). |
| 08 | `08-zip-fotos.png` | Carpeta con fotos nombradas por cédula (ej. `12345678.jpg`). |

> 📌 El manual se puede entregar junto con la carpeta `img/` para que las imágenes se vean correctamente.