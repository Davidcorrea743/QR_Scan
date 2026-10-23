# 🪪 Sistema de Carnets con Código QR

Sistema para generar **carnets de empleados con código QR**. Al escanear el QR se abre una
página pública con la foto del trabajador, su cargo, correo, WhatsApp y las redes de la empresa.
Incluye panel de administración con roles (super administrador, administrador y editor),
**soporte multi-empresa** (cada usuario solo ve y gestiona su empresa) y generación de
carnets imprimibles.

> Desarrollado con **FastAPI, SQLite, Chart.js y Bootstrap**.

## 🚀 Características

### Empleados y Carnets
- ✅ Carnet imprimible con: nombre de la empresa, foto, nombre y apellido, cédula, cargo y QR.
- ✅ QR con el **logo de la empresa** en el centro.
- ✅ Perfil público al escanear: foto, cargo, correo (mailto), WhatsApp (wa.me) y redes de la empresa.
- ✅ Fondo e imagen de la empresa configurables.
- ✅ Baja lógica (soft delete): los empleados se desactivan, no se borran.

### Panel de administración
- ✅ Login con usuarios y contraseñas (hash PBKDF2 + token JWT).
- ✅ Roles: **administrador** (crea y edita todo, incluye cargo y cédula) y **editor**
  (solo puede modificar teléfono y correo).
- ✅ Primer acceso: el admin inicial debe cambiar su contraseña.
- ✅ Gestión de usuarios (crear editores/administradores, resetear contraseñas, activar/desactivar).
- ✅ Formulario amigable en español, validado, con carga de foto.

### Seguimiento de escaneos (se mantiene de la versión anterior)
- ✅ Registro automático de escaneos con IP, User Agent y Referer.
- ✅ Filtros por día, mes, hora y año.
- ✅ Dashboard con gráficos (servidor de estadísticas en el puerto 8001, requiere iniciar sesión).

## 🛠️ Instalación

### Prerrequisitos
- Python 3.8+
- Navegador web moderno

### 1. Crear entorno virtual e instalar dependencias
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

### 2. Ejecutar (usa el Python del venv)
```bash
# Terminal 1 - aplicación principal (puerto 8000)
./.venv/bin/python -m uvicorn main:app --reload --port 8000

# Terminal 2 - estadísticas (puerto 8001)
cd estadisticas && ../.venv/bin/python -m uvicorn main:app --reload --port 8001
```

### 2b. Compartir en la red interna (LAN)
Para que el equipo interno escanee los QR desde sus celulares, el servidor debe
escuchar en todas las interfaces y el QR debe usar la **IP local** de la máquina:

```bash
# Terminal 1 - expuesto a la red
BASE_URL=http://TU_IP_LOCAL:8000 ./.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

1. Averigua tu IP local (ej. `hostname -I` en Linux/WSL, o `ipconfig` en Windows).
2. Usa esa IP como `BASE_URL` (los QR que generes la codificarán).
3. Genera/imprime los carnets y comparte la IP con el equipo para que escaneen.
4. Asegúrate de que el firewall permita el puerto 8000 en la red local.

### 3. Primer acceso
- Abre `http://localhost:8000`
- Usuario inicial: **`admin`** / **`admin123`**
- El sistema te pedirá **cambiar la contraseña** en el primer acceso.

> ⚠️ **Importante antes de un despliegue real:** define la variable de entorno
> `SECRET_KEY` (una cadena larga y aleatoria). Si no está definida, el servidor
> genera una clave efímera al arrancar y **todos los tokens caducan al reiniciar**.
>
> ```bash
> export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
> ```

## 📖 Uso

1. **Super administrador**: gestiona todas las empresas, crea empresas y usuarios de cualquier
   empresa, y puede filtrar empleados, registros y configuración por empresa.
2. **Administrador**: entra a *Configuración empresa* para cargar nombre, logo (centro del QR),
   imagen de fondo y redes sociales (LinkedIn, X, Instagram, web, etc.).
3. **Administrador**: crea empleados desde *+ Nuevo empleado* (nombre, apellido, cédula, cargo,
   correo, teléfono y foto).
4. Abre el **carnet** de un empleado (botón *Carnet*) e imprímelo o guárdalo como PDF.
5. **Editor**: puede editar empleados existentes, pero **solo teléfono y correo**.

> Los usuarios pertenecen a una empresa; admin y editor solo ven los datos de la suya
> (empleados, usuarios, escaneos y configuración).

### URL base del QR
El QR codifica `{BASE_URL}/perfil/{id}`. Define la variable de entorno `BASE_URL` según el
despliegue:

```bash
# Pruebas locales
export BASE_URL=http://localhost:8000

# Servidor de la empresa con IP fija
export BASE_URL=http://192.168.1.50:8000
```

## 📂 Estructura

```
├── main.py              # App principal (monta routers y endpoint /scan)
├── database.py          # Conexión SQLite y creación de tablas
├── auth.py              # Hash PBKDF2, JWT, política de contraseñas y roles
├── config.py            # Settings (BASE_URL)
├── media.py             # Guardado, validación y normalización de imágenes
├── rate_limit.py        # Limitador de peticiones en memoria (ventana deslizante)
├── respaldar.py         # Copia de seguridad de la BD (API SQLite backup)
├── limpiar_uploads.py   # Purga de fotos huérfanas de uploads/ (dry-run por defecto)
├── templating.py        # Renderizado de plantillas
├── routers/
│   ├── auth.py          # Login, /api/me, cambio de contraseña
│   ├── usuarios.py      # Gestión de usuarios (admin)
│   ├── empleados.py     # CRUD empleados con permisos por rol
│   ├── empresa.py       # Configuración de la empresa (admin)
│   └── paginas.py       # Páginas: login, admin, formulario, carnet, perfil
├── templates/           # HTML (login, admin, formulario, config, carnet, perfil, generador)
├── static/              # CSS/JS/logo
├── uploads/             # Fotos e imágenes subidas
├── estadisticas/        # Dashboard de estadísticas (servidor 8001, requiere login)
└── tests/               # Suite pytest (130 pruebas)
```

## 🔒 Seguridad

- Contraseñas con **PBKDF2** (salt aleatorio, 120k iteraciones) y **política mínima de 8 caracteres** en el backend.
- Autenticación por **token JWT** con expiración; `SECRET_KEY` obligatoria en producción (si no, clave efímera con aviso).
- **`debe_cambiar_password` forzado en el backend**: hasta cambiar la clave, la API solo permite `/api/me` y `/api/password`.
- Permisos por rol en el backend (no confía solo en el frontend).
- Validación de imágenes por **contenido real** (Pillow), límite de 8 MB y **protección anti path-traversal** en `uploads/`.
- **Rate limit** en memoria (por IP): `/scan`, login y generación de PDF/ZIP (configurable por entorno).
- **Sin CORS** (la app es same-origin) y **headers de seguridad** (`nosniff`, `X-Frame-Options`, `Referrer-Policy`).
- Los errores internos no exponen detalles al cliente (se registran en el servidor).
- El dashboard de estadísticas (8001) **requiere iniciar sesión** y escapa los datos mostrados.

## 🔧 Mantenimiento

### Respaldos de la BD

```bash
# Crea respaldos/qr_tracker_AAAAMMDD_HHMMSS.db (copia consistente aunque
# la app esté escribiendo; usa la API backup de SQLite)
./.venv/bin/python respaldar.py

# O a una ruta concreta
./.venv/bin/python respaldar.py --destino /ruta/copia.db
```

La carpeta `respaldos/` está en `.gitignore`.

### Limpieza de fotos huérfanas

```bash
# Dry-run: informa cuántos archivos de uploads/ ya no usa la BD
./.venv/bin/python limpiar_uploads.py

# Elimina los que no están referenciados (empleados.foto y tabla empresa)
./.venv/bin/python limpiar_uploads.py --borrar
```

## 🧪 Pruebas

```bash
./.venv/bin/python -m pytest tests -q
```

## Endpoints principales

### Públicos
- `GET /login`, `GET /perfil/{id}`, `GET /scan` (con rate limit)
- `GET /carnet/{id}`, `GET /carnet/{id}/trasero`, `GET /vcard/{id}`

### Autenticados (Bearer token)
- `POST /api/login` (con rate limit), `GET /api/me`, `POST /api/password`
- `GET /api/empleados`, `GET /api/empleados/{id}`
- `PUT /api/empleados/{id}` — editor: solo `telefono` y `correo`; admin: todos los campos
- `GET /api/empleados/{id}/carnet-pdf` (con rate limit)

### Solo administrador
- `POST /api/empleados`, `DELETE /api/empleados/{id}`, `POST /api/empleados/{id}/restaurar`
- `POST /api/empleados/carga-masiva`, `GET /api/empleados/carnets/zip`
- `GET|PUT /api/empresa`
- `GET|POST /api/usuarios`, `PUT /api/usuarios/{id}/password`, `PUT /api/usuarios/{id}/estado`

### Solo super administrador (multi-empresa)
- `GET /api/empresas` — lista empresas; `POST /api/empresas`, `PUT /api/empresas/{id}`
- Listados con `?empresa_id=` (`/api/empleados`, `/api/usuarios`, `/registros`, `/estadisticas`)

### Dashboard de estadísticas (puerto 8001, requiere login)
- `POST /api/login`, `GET /registros`, `GET /estadisticas`

> Nota: `GET /registros` y `GET /estadisticas/*` **ya no existen en el puerto 8000**;
> se sirven únicamente desde el dashboard del 8001, protegidos con token de administrador.
