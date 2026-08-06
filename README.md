# 🪪 Sistema de Carnets con Código QR

Sistema para generar **carnets de empleados con código QR**. Al escanear el QR se abre una
página pública con la foto del trabajador, su cargo, correo, WhatsApp y las redes de la empresa.
Incluye panel de administración con roles (administrador y editor) para que RRHH gestione los
empleados, y generación de carnets imprimibles.

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
- ✅ Dashboard con gráficos (servidor de estadísticas en el puerto 8001).

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

> ⚠️ Cambia también la variable `SECRET_KEY` (entorno) antes de un despliegue real.

## 📖 Uso

1. **Administrador**: entra a *Configuración empresa* para cargar nombre, logo (centro del QR),
   imagen de fondo y redes sociales (LinkedIn, X, Instagram, web, etc.).
2. **Administrador**: crea empleados desde *+ Nuevo empleado* (nombre, apellido, cédula, cargo,
   correo, teléfono y foto).
3. Abre el **carnet** de un empleado (botón *Carnet*) e imprímelo o guárdalo como PDF.
4. **Editor**: puede editar empleados existentes, pero **solo teléfono y correo**.

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
├── main.py              # App principal + endpoints de escaneo/estadísticas
├── database.py          # Conexión SQLite y creación de tablas
├── auth.py              # Hash PBKDF2, JWT y dependencias de rol
├── schemas.py           # (reservado) validación Pydantic
├── config.py            # Settings (BASE_URL)
├── media.py             # Guardado y normalización de imágenes
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
├── estadisticas/        # Dashboard de estadísticas (servidor 8001)
└── tests/               # Suite pytest (49 pruebas)
```

## 🔒 Seguridad

- Contraseñas con **PBKDF2** (salt aleatorio, 120k iteraciones) — no se almacenan en claro.
- Autenticación por **token JWT** con expiración.
- Permisos por rol en el backend (no confía solo en el frontend).
- Validación de imágenes (tipo MIME permitido) y eliminación de archivos al reemplazarlos.
- CORS abierto para desarrollo; ajustar en producción.

## 🧪 Pruebas

```bash
./.venv/bin/python -m pytest tests -q
```

## Endpoints principales

### Públicos
- `GET /login`, `GET /perfil/{id}`, `GET /scan`, `GET /registros`, `GET /estadisticas/*`

### Autenticados (Bearer token)
- `POST /api/login`, `GET /api/me`, `POST /api/password`
- `GET /api/empleados`, `GET /api/empleados/{id}`
- `PUT /api/empleados/{id}` — editor: solo `telefono` y `correo`; admin: todos los campos

### Solo administrador
- `POST /api/empleados`, `DELETE /api/empleados/{id}`, `POST /api/empleados/{id}/restaurar`
- `GET|PUT /api/empresa`
- `GET|POST /api/usuarios`, `PUT /api/usuarios/{id}/password`, `PUT /api/usuarios/{id}/estado`
