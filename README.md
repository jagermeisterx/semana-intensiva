# Análisis Prueba Unidad II — 2º Medio

Web estática para visualizar los resultados de la **Prueba Unidad II** de 2º Medio (cursos **2A** y **2B**): tabulación de 40 preguntas, indicadores de logro por habilidad y distribución de estudiantes por nivel (semáforo Verde / Amarillo / Rojo).

## Requisitos

- [Python 3.8+](https://www.python.org/) (sólo para regenerar los datos desde los `.xlsx`; no usa librerías externas)
- Un navegador moderno (la web usa Chart.js vía CDN)

## Estructura

```
.
├── 2A TABULACION 4.xlsx              # Tabulación curso 2A (entrada)
├── TABULACION 2B 4.xlsx              # Tabulación curso 2B (entrada)
├── TABLA ESPECIFICACIONES UNIDAD II.xlsx  # Pregunta -> habilidad (entrada)
└── analisis/
    ├── build.py                      # Lee los .xlsx y genera data.json
    ├── nombres.json                  # Nombres editables (clave = n° de lista)
    ├── data.json                     # Datos procesados (consume la web)
    └── index.html                    # Web con gráficos (Chart.js)
```

## Cómo usar

### 1. Generar / regenerar los datos

```bash
python3 analisis/build.py
```

Lee los tres `.xlsx` y produce `analisis/data.json`. La **primera vez** también crea
`analisis/nombres.json` con los nombres crudos del Excel como punto de partida editable.

### 2. Editar nombres de estudiantes

Los nombres viven en `analisis/nombres.json`, separados por curso y número de lista:

```json
{
  "2A": { "1": "Cata Gómez", "2": "Ambar Moreno", ... },
  "2B": { "1": "Leonardo", ... }
}
```

- Edita el archivo a mano y vuelve a ejecutar `python3 analisis/build.py`.
- Si una clave existe en `nombres.json`, se usa esa; si falta, se conserva el nombre del Excel.

### 3. Levantar la web en local

La página carga `data.json` por `fetch`, así que debe servirse por HTTP (no abre con `file://`):

```bash
cd analisis
python3 -m http.server 8000
```

Abre http://127.0.0.1:8000/index.html

## ¿Qué muestra la web?

- **Selector de vista**: General (2A + 2B) / Curso 2A / Curso 2B.
- **Indicadores**: N° de estudiantes, % Logro General, % Localizar, % Relacionar, % Reflexionar (con color semáforo).
- **Gráfico** de % por habilidad y **donut** de niveles por logro general.
- **Barras apiladas** con la distribución Verde / Amarillo / Rojo por cada habilidad.
- **Tabla de especificación**: pregunta -> habilidad, con conteo.
- **Detalle de estudiantes por nivel**: tabla con columna **Curso** y filtro `Todos / 2A / 2B`, ordenada por % de logro y con nivel global y por habilidad.

## Niveles (semáforo)

| Nivel    | Rango        |
|----------|--------------|
| Verde    | ≥ 70%        |
| Amarillo | 40% – 69%    |
| Rojo     | < 40%        |

## Tabla de especificación

40 preguntas distribuidas en 3 habilidades:

| Habilidad        | N° de preguntas |
|------------------|-----------------|
| Localizar        | 17              |
| Relacionar       | 20              |
| Reflexionar      | 3               |

## Formato de los archivos de entrada

- **TABLA ESPECIFICACIONES UNIDAD II.xlsx**: dos columnas (Nº PREG, habilidad). Habilidades reconocidas: `LOCALIZAR`, `RELACIONAR/INTERPRETAR`, `REFLEXIONAR`.
- **2A / 2B TABULACION**: col A = n° de lista, col B = nombre, cols C..AP = respuestas de las preguntas 1..40 con valores `C` (correcta) o `I` (incorrecta). Filas vacías u otros valores se ignoran.

## Activar cambios

```bash
# 1. (Opcional) Edita analisis/nombres.json
# 2. Regenera datos
python3 analisis/build.py
# 3. Recarga el navegador
```