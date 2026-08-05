# 📱 Sistema de Generación y Seguimiento de Códigos QR

Sistema completo para generar códigos QR personalizados y realizar seguimiento detallado de escaneos con estadísticas avanzadas.

## 🚀 Características

### Generación de QR
- ✅ Generación de códigos QR personalizables
- ✅ Opciones de tamaño, colores y corrección de errores
- ✅ Logo personalizado integrado (SENA)
- ✅ **Descarga funcional de códigos QR** (CORREGIDO)

### Seguimiento y Estadísticas
- ✅ **Registro automático de escaneos** con información detallada
- ✅ **Filtros avanzados por día, mes, hora y año** (IMPLEMENTADO)
- ✅ **Estadísticas en tiempo real** con gráficos interactivos
- ✅ **Dashboard completo** con métricas clave
- ✅ Captura de IP, User Agent y Referer
- ✅ Campos calculados automáticamente (año, mes, día, hora)

## 🛠️ Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- Navegador web moderno

### 1. Instalar Dependencias Python
```bash
pip install fastapi "uvicorn[standard]"
```

### 2. Configurar Conexión a Base de Datos
El proyecto usa **SQLite** (no requiere servidor externo). La base de datos `qr_tracker.db`
se crea automáticamente al arrancar el servidor principal.

Opcionalmente puedes indicar una ruta diferente de la base de datos con la variable de entorno
`QR_DB_PATH` (útil para pruebas):

## 🚀 Ejecución

### Servidor Principal (Puerto 8000)
```bash
uvicorn main:app --reload --port 8000
```

### Servidor de Estadísticas (Puerto 8001)
```bash
cd estadisticas
uvicorn main:app --reload --port 8001
```

### Acceso a la Aplicación
- **Generador QR**: `http://localhost:8000` (servido por el servidor principal)
- **Estadísticas**: `http://localhost:8001` (servido por el servidor de estadísticas)

> Ambos servidores sirven ahora su interfaz HTML directamente, ya no hace falta abrir
> los archivos `.html` como `file://`.

### Inicio (usando el Python del venv)
```bash
# Terminal 1 - generador (puerto 8000)
./.venv/bin/python -m uvicorn main:app --reload --port 8000

# Terminal 2 - estadísticas (puerto 8001)
./.venv/bin/python -m uvicorn main:app --reload --port 8001
```

## 📊 Funcionalidades de Estadísticas

### Filtros Disponibles
- **Por fecha específica**: Seleccionar día exacto
- **Por mes**: Filtrar por mes específico
- **Por año**: Filtrar por año específico
- **Por rango de horas**: Desde hora X hasta hora Y
- **Límite de registros**: 50, 100, 200, 500 registros

### Métricas Disponibles
- Total de escaneos históricos
- Escaneos por día (últimos 7 días)
- Escaneos por hora del día actual
- Días con actividad
- Horas más activas

### Endpoints API

#### Servidor Principal (Puerto 8000)
- `GET /scan` - Registrar escaneo
- `GET /registros` - Obtener registros con filtros
- `GET /estadisticas/por-dia` - Estadísticas diarias
- `GET /estadisticas/por-mes` - Estadísticas mensuales
- `GET /estadisticas/por-hora` - Estadísticas por hora
- `GET /estadisticas/por-año` - Estadísticas anuales
- `GET /estadisticas/resumen` - Resumen general

#### Servidor de Estadísticas (Puerto 8001)
- `GET /registros` - Registros con filtros avanzados
- `GET /estadisticas` - Estadísticas resumidas

## 🔧 Estructura del Proyecto

```
QR/
├── main.py                 # Servidor principal con APIs
├── app.js                  # Lógica del generador QR
├── index.html              # Interfaz del generador
├── styles.css              # Estilos del generador
├── scans.sql              # Estructura de base de datos
├── estadisticas/
│   ├── main.py            # Servidor de estadísticas
│   ├── registros.html     # Dashboard de estadísticas
│   └── estilos.css        # Estilos del dashboard
└── README.md              # Este archivo
```

## 🐛 Problemas Solucionados

### ✅ Descarga de QR
- **Problema**: La función `downloadQR()` no funcionaba correctamente
- **Solución**: Implementado método `toDataURL()` más compatible con manejo de errores

### ✅ Estadísticas Limitadas
- **Problema**: Solo filtros básicos por fecha y hora
- **Solución**: Filtros avanzados por día, mes, año, rangos de hora

### ✅ Base de Datos Básica
- **Problema**: Campos limitados para estadísticas
- **Solución**: Agregados campos calculados automáticamente y metadatos

### ✅ Interfaz de Estadísticas
- **Problema**: Interfaz básica sin gráficos
- **Solución**: Dashboard completo con Chart.js y métricas en tiempo real

## 📈 Nuevas Funcionalidades

1. **Gráficos Interactivos**: Visualización de datos con Chart.js
2. **Filtros Avanzados**: Múltiples criterios de filtrado
3. **Métricas en Tiempo Real**: Estadísticas actualizadas automáticamente
4. **Información Detallada**: Captura de User Agent, IP, Referer
5. **Campos Calculados**: Año, mes, día, hora extraídos automáticamente
6. **API Completa**: Endpoints para todas las estadísticas
7. **Interfaz Mejorada**: Design moderno con Bootstrap 5

## 🔒 Seguridad

- CORS configurado para desarrollo
- Validación de parámetros en endpoints
- Manejo de errores en frontend y backend
- Límites en consultas para evitar sobrecarga

## 📝 Notas de Desarrollo

- Los servidores deben ejecutarse en puertos diferentes (8000 y 8001)
- La base de datos se recrea automáticamente con datos de ejemplo
- Los gráficos se actualizan automáticamente al cargar la página
- Todos los filtros son opcionales y se pueden combinar

---

**Desarrollado con FastAPI, SQLite, Chart.js y Bootstrap 5**


