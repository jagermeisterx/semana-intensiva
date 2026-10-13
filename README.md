# Análisis de Resultados

Web estática para visualizar resultados de pruebas: tabulación de preguntas por alumno
(`C` = correcta, `I` = incorrecta), indicadores de logro por habilidad y distribución de
estudiantes por nivel (semáforo Verde / Amarillo / Rojo).

La página tiene **dos pestañas**:

1. **Unidad III · Actualización** (pestaña principal, por defecto): resultados de la carpeta
   `actualizacion/`, con cursos **1A, 1B, 1C** (1º Medio, 32 preguntas) y **2A, 2B**
   (2º Medio, 44 preguntas), más vistas de grupo por nivel (1º Medio = 1A+1B+1C, 2º Medio = 2A+2B).
2. **Revisión anterior**: contenido histórico generado desde `analisis/data.json`
   (hoy: SIMCE Lenguaje Oct 2025 de 2º Medio) y su sección Comparativa.

## Requisitos

- [Python 3.8+](https://www.python.org/) (sólo para regenerar los datos desde los `.xlsx`; no usa librerías externas)
- Un navegador moderno (la web usa Chart.js vía CDN)

## Estructura

```
.
├── index.html                        # Web con gráficos (Chart.js) y pestañas
├── 2A TABULACION 4.xlsx              # Tabulación curso 2A (entrada, pestaña anterior)
├── TABULACION 2B 4.xlsx              # Tabulación curso 2B (entrada, pestaña anterior)
├── TABLA ESPECIFICACIONES UNIDAD II.xlsx  # Pregunta -> habilidad (entrada, pestaña anterior)
├── actualizacion/                    # Entradas de la Unidad III (pestaña principal)
│   ├── 1A U3.xlsx                    # Tabulación curso 1A (32 preguntas)
│   ├── 1B U3.xlsx                    # Tabulación curso 1B (32 preguntas)
│   ├── U3 1C.xlsx                    # Tabulación curso 1C (32 preguntas)
│   ├── U3 2A.xlsx                    # Tabulación curso 2A (44 preguntas)
│   ├── U3 2B.xlsx                    # Tabulación curso 2B (44 preguntas)
│   ├── TABLA ESPECIFICACIÓN U3 1ºMEDIO.docx      # Pregunta -> habilidad (1º Medio)
│   └── TABLA ESPECIFICACIONES PRUEBS .docx       # Pregunta -> habilidad (2º Medio)
├── cami/                             # Otras entradas (modo --cami)
└── analisis/
    ├── build.py                      # Lee los .xlsx/.docx y genera los data.json
    ├── nombres.json                  # Nombres editables pestaña anterior
    ├── data.json                     # Datos procesados pestaña anterior (consume la web)
    ├── data_anterior.json            # Backup / comparativa pestaña anterior
    ├── nombres_u3.json               # Nombres editables Unidad III
    └── data_u3.json                  # Datos procesados Unidad III (consume la web)
```

## Cómo usar

### 1. Generar / regenerar los datos

**Unidad III (pestaña principal)** — lee los `.xlsx` y `.docx` de `actualizacion/` y produce
`analisis/data_u3.json`:

```bash
python3 analisis/build.py --actualizacion
```

Aplica la tabla de 1º Medio (`TABLA ESPECIFICACIÓN U3 1ºMEDIO.docx`, 32 preguntas) a 1A/1B/1C
y la de 2º Medio (`TABLA ESPECIFICACIONES PRUEBS .docx`, 44 preguntas) a 2A/2B. No modifica
`analisis/data.json`. La **primera vez** también crea `analisis/nombres_u3.json`.

**Pestaña anterior** — modo original (Prueba Unidad II de 2º Medio):

```bash
python3 analisis/build.py
```

Lee los `.xlsx` de la raíz y produce `analisis/data.json`. La **primera vez** también crea
`analisis/nombres.json` con los nombres crudos del Excel como punto de partida editable.

> Modo `--cami`: `python3 analisis/build.py --cami` regenera `data.json` desde la carpeta `cami/`.

### 2. Editar nombres de estudiantes

Los nombres viven en `analisis/nombres.json`, separados por curso y número de lista:

```json
{
  "2A": { "1": "Cata Gómez", "2": "Ambar Moreno", ... },
  "2B": { "1": "Leonardo", ... }
}
```

- Unidad III usa `analisis/nombres_u3.json` (claves `1A`, `1B`, `1C`, `2A`, `2B`).
- Edita el archivo a mano y vuelve a ejecutar el script correspondiente.
- Si una clave existe en el JSON de nombres, se usa esa; si falta, se conserva el del Excel.

### 3. Levantar la web en local

La página carga `analisis/data_u3.json` y `analisis/data.json` por `fetch`, así que debe servirse por HTTP (no abre con `file://`):

```bash
python3 -m http.server 8000
```

Abre http://127.0.0.1:8000/index.html

## ¿Qué muestra la web?

Cada pestaña incluye:

- **Selector de vista**: en Unidad III, grupo por nivel (1º Medio, 2º Medio) y cada curso
  (1A/1B/1C/2A/2B); en la pestaña anterior, General (2A + 2B) / Curso 2A / Curso 2B.
- **Indicadores**: N° de estudiantes, % Logro General, % Localizar, % Relacionar, % Reflexionar (con color semáforo).
- **Gráfico** de % por habilidad y **donut** de niveles por logro general.
- **Barras apiladas** con la distribución Verde / Amarillo / Rojo por cada habilidad.
- **Tabla de especificación**: pregunta -> habilidad, con conteo.
- **Detalle de estudiantes por nivel**: tabla con columna **Curso** y filtro por curso, ordenada por % de logro y con nivel global y por habilidad.

## Tablas de especificación

- **Pestaña anterior (Unidad II, 40 preguntas)**: Localizar 17, Relacionar 20, Reflexionar 3.
- **Unidad III — 1º Medio (32 preguntas)** `TABLA ESPECIFICACIÓN U3 1ºMEDIO.docx`: Localizar 19, Relacionar 11, Reflexionar 2.
- **Unidad III — 2º Medio (44 preguntas)** `TABLA ESPECIFICACIONES PRUEBS .docx`: Localizar 14, Relacionar 27, Reflexionar 3.

## Niveles (semáforo)

| Nivel    | Rango        |
|----------|--------------|
| Verde    | ≥ 70%        |
| Amarillo | 40% – 69%    |
| Rojo     | < 40%        |

## Formato de los archivos de entrada

Todas las tabulaciones comparten el mismo formato: col A = n° de lista, col B = nombre,
y a partir de la col C las respuestas por pregunta con valores `C` (correcta) o `I`
(incorrecta). Se ignoran filas vacías y otros valores.

- **Pestaña anterior**:
  - `TABLA ESPECIFICACIONES UNIDAD II.xlsx`: `Nº PREG | habilidad`.
  - `2A TABULACION 4.xlsx` / `TABULACION 2B 4.xlsx`: preguntas 1..40.
- **Unidad III** (`actualizacion/`):
  - `.xlsx`: `1A U3`/`1B U3`/`U3 1C` (preguntas 1..32), `U3 2A`/`U3 2B` (preguntas 1..44).
  - `.docx` con tabla: n° de pregunta, alternativa correcta y **habilidad** (se detecta la
    columna de habilidad por contenido, no por posición).

Habilidades reconocidas: `LOCALIZAR`, `RELACIONAR/INTERPRETAR`, `REFLEXIONAR`.

## Activar cambios

```bash
# Unidad III (pestaña principal)
python3 analisis/build.py --actualizacion   # usa/crea analisis/nombres_u3.json

# Pestaña anterior
python3 analisis/build.py                   # usa/crea analisis/nombres.json

# 3. Recarga el navegador
```