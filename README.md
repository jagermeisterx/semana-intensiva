# Análisis de Resultados

Web estática para visualizar resultados de pruebas: tabulación de preguntas por alumno
(`C` = correcta, `I` = incorrecta), indicadores de logro por habilidad y distribución de
estudiantes por nivel (semáforo Verde / Amarillo / Rojo).

La página tiene **cuatro pestañas**:

1. **Semana Intensiva 3** (principal, por defecto): datos de `actualizacion/`, cursos
   **2A** y **2B** (2º Medio, 38 preguntas), más la vista combinada de 2º Medio.
2. **Comparativa Intensiva 2 → 3**: compara la Semana Intensiva 2 (`cami/`, 32 preguntas)
   con la Semana Intensiva 3, de forma agregada por curso y estudiante por estudiante.
3. **Unidad III · Histórico**: snapshot de la Unidad III (1A/1B/1C/2A/2B, 32/44
   preguntas) conservado en `analisis/data_u3.json`. Sus archivos fuente originales ya
   no están en `actualizacion/`, por lo que esta pestaña no se regenera.
4. **Semana Intensiva 2**: contenido histórico generado desde `cami/` (SIMCE Lenguaje
   Oct 2025, 2A/2B, 32 preguntas).

## Requisitos

- [Python 3.8+](https://www.python.org/) (sólo para regenerar los datos desde los
  `.xlsx`/`.docx`; no usa librerías externas)
- Un navegador moderno (la web usa Chart.js vía CDN)

## Estructura

```
.
├── index.html                              # Web con gráficos (Chart.js) y pestañas
├── actualizacion/                          # Entradas de la Semana Intensiva 3
│   ├── SEM INT 3 2A.xlsx                   # Hojas "2 A" (34) y "2 B" (26), 38 preguntas
│   └── TABLA PRUEBA SEM 3.docx             # Pregunta -> habilidad (38 preguntas)
├── cami/                                   # Entradas de la Semana Intensiva 2
│   ├── 2A INTENSIVA 2.xlsx
│   ├── 2B SEM INTEN 2.xlsx
│   └── Tabla de especificaciones y respuestas simce lenguaje octubre 2025 (1) (1).docx
├── 2A TABULACION 4.xlsx                    # Entradas de la Prueba Unidad II (legacy)
├── TABULACION 2B 4.xlsx
├── TABLA ESPECIFICACIONES UNIDAD II.xlsx
└── analisis/
    ├── build.py                            # Lee los .xlsx/.docx y genera los data.json
    ├── data.json                           # Semana Intensiva 2 (2A/2B, 32 preguntas)
    ├── data_sem3.json                      # Semana Intensiva 3 (2A/2B, 38 preguntas)
    ├── data_comparativa.json               # Comparativa Intensiva 2 vs 3
    ├── data_u3.json                        # Unidad III histórica (snapshot)
    ├── data_anterior.json                  # Backup de data.json
    ├── nombres_cami.json                   # Nombres editables Semana Intensiva 2
    ├── nombres_sem3.json                   # Nombres editables Semana Intensiva 3
    ├── alias_intensivas.json               # Alias para emparejar estudiantes entre semanas
    ├── nombres.json                        # Nombres editables Prueba Unidad II
    └── nombres_u3.json                     # Nombres editables Unidad III
```

## Cómo usar

### 1. Generar / regenerar los datos

**Semana Intensiva 3 + comparativa**:

```bash
python3 analisis/build.py --sem3
```

Lee `actualizacion/SEM INT 3 2A.xlsx` (hojas `2 A` y `2 B`) y
`actualizacion/TABLA PRUEBA SEM 3.docx`. Genera:

- `analisis/data_sem3.json`
- `analisis/data_comparativa.json` (contra `analisis/data.json`)
- `analisis/nombres_sem3.json` la primera vez
- `analisis/alias_intensivas.json` la primera vez

**Semana Intensiva 2**:

```bash
python3 analisis/build.py --cami
```

Lee los `.xlsx` de `cami/` y produce `analisis/data.json` (y actualiza
`analisis/data_anterior.json` como backup). Si editas los nombres o los archivos de la
Semana 2, vuelve a ejecutar este comando y después `--sem3` para refrescar la comparativa.

**Prueba Unidad II (legacy)**:

```bash
python3 analisis/build.py
```

Lee los `.xlsx` de la raíz y produce `analisis/data.json`. **No** es la ruta que usa la
pestaña de Semana Intensiva 2; sirve para el modo original de la Prueba Unidad II. Ojo:
escribe el mismo `data.json`, así que si lo ejecutas deberás correr después `--cami` para
volver a la Semana Intensiva 2.

**Unidad III histórica**: `python3 analisis/build.py --actualizacion` depende de los
archivos originales de la Unidad III, que ya no están en `actualizacion/`. El resultado
actual se conserva en `analisis/data_u3.json`; no ejecutes ese modo salvo que restaures
esos archivos.

### 2. Editar nombres y emparejamientos

Los nombres viven en archivos JSON separados por curso y número de lista:

```json
{
  "2A": { "1": "KARLA ARA", "2": "CATA GONZALEZ" }
}
```

- Semana Intensiva 3: `analisis/nombres_sem3.json` (claves `2A`, `2B`).
- Semana Intensiva 2: `analisis/nombres_cami.json` (claves `2A`, `2B`).
- Unidad III: `analisis/nombres_u3.json`.
- Prueba Unidad II: `analisis/nombres.json`.

Para el detalle por estudiante de la comparativa, los nombres se emparejan entre semanas
por nombre normalizado (mayúsculas, sin tildes ni puntuación). Si un estudiante aparece
con un nombre abreviado o distinto, agrégalo a `analisis/alias_intensivas.json`:

```json
{
  "2A": {
    "LIKAN": "LIKAN COMULAI"
  },
  "2B": {
    "DEVORA": "DEBORA"
  }
}
```

La clave es el nombre en la Semana Intensiva 3 y el valor es el nombre en la Semana
Intensiva 2. Después vuelve a ejecutar `python3 analisis/build.py --sem3`.

> **Caso pendiente:** `BENJAMIN` (2B) quedó sin emparejar a propósito porque no se pudo
> determinar si corresponde a `BENJA R` (BENJA REBOLLEDO) o a `BENJA V` (BENJA VALDI).
> Aparece en la tabla de estudiantes sin pareja. Para resolverlo, agrega en
> `alias_intensivas.json` la clave `"BENJAMIN"` con el nombre exacto que aparece en la
> Semana 2 (`"BENJA R"` o `"BENJA V"`) y regenera.

### 3. Levantar la web en local

La página carga los JSON de `analisis/` por `fetch`, así que debe servirse por HTTP
(no abre con `file://`):

```bash
python3 -m http.server 8000
```

Abre http://127.0.0.1:8000/index.html

## ¿Qué muestra la web?

### Semana Intensiva 3

- **Selector de vista**: 2º Medio (2A+2B), 2A y 2B.
- **Indicadores**: N° de estudiantes, % Logro General, % Localizar, % Relacionar,
  % Reflexionar (con color semáforo).
- **Gráfico** de % por habilidad y **donut** de niveles por logro general.
- **Barras apiladas** con la distribución Verde / Amarillo / Rojo por habilidad.
- **Tabla de especificación**: pregunta -> habilidad, con conteo.
- **Detalle de estudiantes** por nivel, con filtro por curso.

### Comparativa Intensiva 2 → 3

- **Selector**: 2º Medio (2A+2B), 2A y 2B.
- **Resumen agregado**: preguntas, N° de estudiantes, logro general, habilidades y
  semáforo, con la variación entre semanas.
- **Gráficos** comparativos de logro general y por habilidad.
- **Tabla por estudiante**: % y nivel en cada semana, variación general y por habilidad.
- **Estudiantes sin pareja**: quienes sólo tienen datos en una de las dos semanas,
  incluyendo el caso ambiguo `BENJAMIN`.

La comparación usa porcentajes, pero las pruebas no son idénticas:

- Semana 2: 32 preguntas (Localizar 10, Relacionar 21, Reflexionar 1).
- Semana 3: 38 preguntas (Localizar 15, Relacionar 21, Reflexionar 2).

Por eso la variación de **Reflexionar** es especialmente sensible: pasa de 1 a 2
preguntas. Además, la composición de estudiantes cambió entre semanas (77 → 60 en 2º
Medio), así que los agregados oficiales no son una comparación de la misma cohorte.

### Pestañas históricas

- **Unidad III · Histórico** y **Semana Intensiva 2** mantienen sus datos y visualizaciones
  (indicadores, gráficos, tabla de especificación y detalle de estudiantes).

## Tablas de especificación

- **Semana Intensiva 2 (32 preguntas)**: Localizar 10, Relacionar 21, Reflexionar 1.
- **Semana Intensiva 3 (38 preguntas)**: Localizar 15, Relacionar 21, Reflexionar 2.
- **Unidad III — 1º Medio (32 preguntas)**: Localizar 19, Relacionar 11, Reflexionar 2.
- **Unidad III — 2º Medio (44 preguntas)**: Localizar 14, Relacionar 27, Reflexionar 3.
- **Prueba Unidad II (40 preguntas)**: Localizar 17, Relacionar 20, Reflexionar 3.

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

- **Semana Intensiva 3**:
  - `SEM INT 3 2A.xlsx`: hojas `2 A` y `2 B`, preguntas 1..38.
  - `TABLA PRUEBA SEM 3.docx`: tabla con n° de pregunta, respuesta correcta y
    **habilidad** (se detecta la columna de habilidad por contenido).
- **Semana Intensiva 2** (`cami/`): `2A INTENSIVA 2.xlsx`, `2B SEM INTEN 2.xlsx` y el
  `.docx` de especificaciones SIMCE.
- **Unidad III** (`actualizacion/`, histórico): 1A/1B/1C (32 preguntas) y 2A/2B
  (44 preguntas).
- **Prueba Unidad II** (raíz): `2A TABULACION 4.xlsx`, `TABULACION 2B 4.xlsx` y
  `TABLA ESPECIFICACIONES UNIDAD II.xlsx`.

Habilidades reconocidas: `LOCALIZAR`, `RELACIONAR/INTERPRETAR`, `REFLEXIONAR`.

## Activar cambios

```bash
# Semana Intensiva 2 (si cambió cami/ o nombres_cami.json)
python3 analisis/build.py --cami

# Semana Intensiva 3 + comparativa
python3 analisis/build.py --sem3

# Servir la web
python3 -m http.server 8000
```

La Unidad III se mantiene como snapshot en `analisis/data_u3.json`; no se regenera con
estos comandos.
