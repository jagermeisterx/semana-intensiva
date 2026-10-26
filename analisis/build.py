#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesa los archivos .xlsx de tabulación y la tabla de especificaciones
y genera data.json con los indicadores y distribuciones por nivel
para la web de resultados.

Modos:
  python build.py                 Procesa archivos de Prueba Unidad II (raíz)
  python build.py --cami          Procesa archivos de la carpeta cami/
                                  (Semana Intensiva 2)
  python build.py --sem3          Procesa la carpeta actualizacion/
                                  (Semana Intensiva 3, 2A/2B) y genera la
                                  comparativa contra data.json
  python build.py --actualizacion Procesa la carpeta actualizacion/ (Unidad III
                                  histórica; requiere los archivos originales)

Salida:
  - analisis/data.json          (Semana Intensiva 2 / datos actuales)
  - analisis/data_anterior.json (backup previo, si existía data.json)
  - analisis/data_sem3.json     (Semana Intensiva 3; sólo con --sem3)
  - analisis/data_comparativa.json (Intensiva 2 vs 3; sólo con --sem3)
  - analisis/data_u3.json       (Unidad III; sólo con --actualizacion)
  - analisis/nombres_sem3.json  (nombres editables Semana 3)
  - analisis/alias_intensivas.json (alias editables Intensiva 2 -> 3)
  - analisis/nombres_u3.json    (nombres editables Unidad III)
"""

import json
import os
import re
import shutil
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

# ---------------------------------------------------------------------------
# Utilidades para leer .xlsx sin dependencias externas
# ---------------------------------------------------------------------------

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _read_xlsx(path, sheet=1):
    """Devuelve una lista de filas; cada fila es un dict {letra_col: valor}.

    sheet: número de hoja (1 = primera hoja del libro).
    """
    z = zipfile.ZipFile(path)
    # shared strings
    ss = []
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            txt = "".join(t.text or "" for t in si.iter(f"{NS}t"))
            ss.append(txt)
    except KeyError:
        pass
    # hoja solicitada
    root = ET.fromstring(z.read(f"xl/worksheets/sheet{sheet}.xml"))
    rows = []
    for row in root.iter(f"{NS}row"):
        cells = {}
        for c in row.findall(f"{NS}c"):
            ref = c.get("r")
            col = re.match(r"[A-Z]+", ref).group()
            t = c.get("t")
            v = c.find(f"{NS}v")
            isn = c.find(f"{NS}is")
            if t == "s" and v is not None:
                val = ss[int(v.text)]
            elif t == "inlineStr" and isn is not None:
                val = "".join(x.text or "" for x in isn.iter(f"{NS}t"))
            elif v is not None:
                val = v.text
            else:
                val = ""
            cells[col] = val
        rows.append(cells)
    return rows


def _col_to_index(col):
    """'A' -> 0, 'B' -> 1, ..., 'AA' -> 26 ..."""
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


# ---------------------------------------------------------------------------
# Utilidades para leer .docx (tablas Word)
# ---------------------------------------------------------------------------

DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _read_docx_table(path):
    """Devuelve lista de filas (cada fila = lista de strings) desde la primera tabla del .docx."""
    z = zipfile.ZipFile(path)
    content = z.read("word/document.xml")
    root = ET.fromstring(content)
    tables = root.findall(".//w:tbl", DOCX_NS)
    if not tables:
        return []
    rows_out = []
    for row in tables[0].findall(".//w:tr", DOCX_NS):
        cells = row.findall(".//w:tc", DOCX_NS)
        fila = []
        for cell in cells:
            texts = cell.findall(".//w:t", DOCX_NS)
            texto = " ".join(t.text or "" for t in texts).strip()
            fila.append(texto)
        rows_out.append(fila)
    return rows_out


# ---------------------------------------------------------------------------
# Lectura de la tabla de especificaciones
# ---------------------------------------------------------------------------

def leer_especificaciones(path):
    """Devuelve dict {n_pregunta: habilidad_normalizada} y conteo por habilidad."""
    rows = _read_xlsx(path)
    preg = {}
    for r in rows:
        a = (r.get("A") or "").strip()
        b = (r.get("B") or "").strip()
        # La fila 0 tiene encabezados; saltamos textos no numéricos
        if not a.isdigit():
            continue
        n = int(a)
        # Normalizar habilidad
        hab = b.upper()
        if "LOCALIZAR" in hab:
            hab = "LOCALIZAR"
        elif "RELACIONAR" in hab or "INTERPRETAR" in hab:
            hab = "RELACIONAR"
        elif "REFLEXIONAR" in hab:
            hab = "REFLEXIONAR"
        preg[n] = hab
    # Ordenar por número
    preg = {k: preg[k] for k in sorted(preg)}
    conteo = defaultdict(int)
    for h in preg.values():
        conteo[h] += 1
    return preg, dict(conteo)


def leer_especificaciones_docx(path):
    """Lee especificaciones desde un .docx con tabla: N° Pregunta | Habilidad | Respuesta."""
    filas = _read_docx_table(path)
    preg = {}
    for fila in filas[1:]:  # saltar encabezado
        if len(fila) < 2:
            continue
        a = fila[0].strip()
        b = fila[1].strip()
        if not a.isdigit():
            continue
        n = int(a)
        hab = b.upper()
        if "LOCALIZAR" in hab:
            hab = "LOCALIZAR"
        elif "RELACIONAR" in hab or "INTERPRETAR" in hab:
            hab = "RELACIONAR"
        elif "REFLEXIONAR" in hab:
            hab = "REFLEXIONAR"
        preg[n] = hab
    preg = {k: preg[k] for k in sorted(preg)}
    conteo = defaultdict(int)
    for h in preg.values():
        conteo[h] += 1
    return preg, dict(conteo)


def _normalizar_habilidad(texto):
    """Convierte un texto de habilidad a LOCALIZAR / RELACIONAR / REFLEXIONAR (o None)."""
    hab = (texto or "").upper()
    if "LOCALIZAR" in hab:
        return "LOCALIZAR"
    if "RELACIONAR" in hab or "INTERPRETAR" in hab:
        return "RELACIONAR"
    if "REFLEXIONAR" in hab:
        return "REFLEXIONAR"
    return None


def leer_especificaciones_docx_generico(path):
    """
    Lee una spec desde un .docx con tabla cuyo encabezado puede variar.
    Detecta la columna de habilidad por contenido y el n° de pregunta como
    la primera celda numérica de la fila. Funciona con las tablas de la
    carpeta actualizacion/ (N° | Respuesta | Habilidad | ...).
    """
    filas = _read_docx_table(path)
    preg = {}
    for fila in filas:
        n = None
        hab = None
        for celda in fila:
            cs = celda.strip()
            if n is None and cs.isdigit():
                n = int(cs)
            if hab is None:
                hab = _normalizar_habilidad(cs)
        if n is None or hab is None:
            continue
        preg[n] = hab
    preg = {k: preg[k] for k in sorted(preg)}
    conteo = defaultdict(int)
    for h in preg.values():
        conteo[h] += 1
    return preg, dict(conteo)


def _buscar_archivo(carpeta, *claves):
    """Devuelve la ruta del primer archivo de la carpeta que contenga todas las claves."""
    for nombre in os.listdir(carpeta):
        bajo = nombre.lower()
        if all(k.lower() in bajo for k in claves):
            return os.path.join(carpeta, nombre)
    return None


# ---------------------------------------------------------------------------
# Lectura de una tabulación
# ---------------------------------------------------------------------------

def leer_tabulacion(path, sheet=1):
    """
    Devuelve lista de estudiantes:
      [{"numero": str, "nombre": str, "respuestas": {1:'C', 2:'I', ...}}]
    Se asume: col A = número de lista, col B = nombre, cols C..AP = preguntas 1..40.
    Valores válidos: 'C' o 'I'. Se ignoran filas vacías y otros valores.
    sheet: número de hoja del libro (1 = primera).
    """
    rows = _read_xlsx(path, sheet=sheet)
    # Mapeo letra columna -> número de pregunta (1..40)
    # C=1, D=2, ..., AP=40
    # Construir el mapeo a partir de la fila de encabezado (row 0).
    header = rows[0] if rows else {}
    col_to_preg = {}
    for col, val in header.items():
        if col in ("A", "B"):
            continue
        try:
            n = int(val)
        except (ValueError, TypeError):
            continue
        col_to_preg[col] = n

    # Si no hay encabezado numérico útil, calcular mapeo por posición
    if not col_to_preg:
        # C=1 ... AP=40
        letters = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        all_letters = list(letters) + ["A" + c for c in letters]
        for i in range(40):
            col = all_letters[i + 2]  # saltar A y B
            col_to_preg[col] = i + 1

    estudiantes = []
    for r in rows[1:]:
        numero = (r.get("A") or "").strip()
        nombre = (r.get("B") or "").strip()
        if not nombre:
            continue
        respuestas = {}
        for col, val in r.items():
            if col not in col_to_preg:
                continue
            v = (val or "").strip().upper()
            if v not in ("C", "I"):
                continue
            respuestas[col_to_preg[col]] = v
        # Debe tener al menos una respuesta válida
        if not respuestas:
            continue
        estudiantes.append({
            "numero": numero,
            "nombre": nombre,
            "respuestas": respuestas,
        })
    return estudiantes


# ---------------------------------------------------------------------------
# Gestión de nombres editables (nombres.json)
# ---------------------------------------------------------------------------

def cargar_nombres(path):
    """Carga nombres.json si existe; devuelve dict o None."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generar_nombres(path, est_a, est_b):
    """
    Genera nombres.json inicial a partir de los nombres crudos del Excel,
    usando como clave el número de lista (col A) por курсor.
    """
    data = {
        "2A": {e["numero"]: e["nombre"] for e in est_a},
        "2B": {e["numero"]: e["nombre"] for e in est_b},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def aplicar_nombres(estudiantes, curso, nombres):
    """
    Sobrescribe el campo 'nombre' de cada estudiante usando nombres.json
    cuando exista la clave {curso: numero}. Si falta, conserva el del Excel.
    """
    nom_curso = (nombres or {}).get(curso, {})
    for e in estudiantes:
        if e["numero"] in nom_curso and nom_curso[e["numero"]]:
            e["nombre"] = nom_curso[e["numero"]]


# ---------------------------------------------------------------------------
# Cálculo de indicadores
# ---------------------------------------------------------------------------

umb_verde = 70.0
umb_amarillo = 40.0


def nivel_porcentaje(pct):
    if pct >= umb_verde:
        return "Verde"
    if pct >= umb_amarillo:
        return "Amarillo"
    return "Rojo"


def calcular_indicadores(estudiantes, especificaciones, preguntas_por_habilidad):
    """
    estudiantes: lista de {"nombre", "respuestas": {n:'C'/'I'}}
    especificaciones: {n: habilidad}
    preguntas_por_habilidad: {habilidad: n_preguntas}

    Devuelve dict con:
      n_estudiantes, logro_general (%),
      por_habilidad: {hab: %}, correctas_por_habilidad: {hab: int},
      niveles_logro: {"Verde": int, "Amarillo": int, "Rojo": int},
      niveles_por_habilidad: {hab: {"Verde":..,"Amarillo":..,"Rojo":..}},
      detalle_estudiantes: [{nombre, numero, curso, pct_general, nivel,
                            por_habilidad:{hab:pct}, nivel_por_habilidad:{hab:nivel}}]
    """
    n = len(estudiantes)
    if n == 0:
        return {
            "n_estudiantes": 0,
            "logro_general": 0.0,
            "por_habilidad": {},
            "correctas_por_habilidad": {},
            "niveles_logro": {"Verde": 0, "Amarillo": 0, "Rojo": 0},
            "niveles_por_habilidad": {},
            "detalle_estudiantes": [],
        }

    total_preg = len(especificaciones)
    total_respuestas = n * total_preg

    # Correctas globales por estudiante
    correctas_globales = 0
    detalle = []
    for e in estudiantes:
        resp = e["respuestas"]
        # correctas totales del estudiante
        c_total = sum(1 for p, v in resp.items() if v == "C")
        # correctas por habilidad
        c_hab = defaultdict(int)
        preg_hab = defaultdict(int)
        for p, v in resp.items():
            hab = especificaciones.get(p)
            if hab is None:
                continue
            preg_hab[hab] += 1
            if v == "C":
                c_hab[hab] += 1
        pct_general = (c_total / total_preg * 100) if total_preg else 0
        pct_hab = {}
        nivel_hab = {}
        for hab, n_preg in preguntas_por_habilidad.items():
            respondidas = preg_hab.get(hab, 0)
            # Para % usamos denominador = n_preguntas de la habilidad (asumiendo que respondió todas)
            denom = n_preg if n_preg else 1
            pct = (c_hab.get(hab, 0) / denom) * 100
            pct_hab[hab] = round(pct, 1)
            nivel_hab[hab] = nivel_porcentaje(pct)
        detalle.append({
            "nombre": e["nombre"],
            "numero": e.get("numero", ""),
            "curso": e.get("curso", ""),
            "correctas": c_total,
            "pct_general": round(pct_general, 1),
            "nivel": nivel_porcentaje(pct_general),
            "por_habilidad": pct_hab,
            "nivel_por_habilidad": nivel_hab,
        })
        correctas_globales += c_total

    # % logro general
    logro_general = (correctas_globales / total_respuestas * 100) if total_respuestas else 0

    # Correctas totales por habilidad
    correctas_por_habilidad = defaultdict(int)
    for e in estudiantes:
        for p, v in e["respuestas"].items():
            if v != "C":
                continue
            hab = especificaciones.get(p)
            if hab:
                correctas_por_habilidad[hab] += 1

    por_habilidad = {}
    for hab, n_preg in preguntas_por_habilidad.items():
        denom = n * n_preg if n and n_preg else 1
        por_habilidad[hab] = round((correctas_por_habilidad.get(hab, 0) / denom) * 100, 1)

    # Distribución por nivel (logro general)
    niveles_logro = {"Verde": 0, "Amarillo": 0, "Rojo": 0}
    for d in detalle:
        niveles_logro[d["nivel"]] += 1

    # Distribución por nivel por habilidad
    niveles_por_habilidad = {}
    for hab in preguntas_por_habilidad:
        niveles_por_habilidad[hab] = {"Verde": 0, "Amarillo": 0, "Rojo": 0}
    for d in detalle:
        for hab in preguntas_por_habilidad:
            niveles_por_habilidad[hab][d["nivel_por_habilidad"][hab]] += 1

    return {
        "n_estudiantes": n,
        "logro_general": round(logro_general, 1),
        "por_habilidad": por_habilidad,
        "correctas_por_habilidad": dict(correctas_por_habilidad),
        "niveles_logro": niveles_logro,
        "niveles_por_habilidad": niveles_por_habilidad,
        "detalle_estudiantes": detalle,
    }


# ---------------------------------------------------------------------------
# Modo actualizacion/: Unidad III - 1º Medio y 2º Medio
# ---------------------------------------------------------------------------

# Curso -> archivo Excel dentro de actualizacion/
ACT_CURSOS = [
    ("1A", "1A U3.xlsx"),
    ("1B", "1B U3.xlsx"),
    ("1C", "U3 1C.xlsx"),
    ("2A", "U3 2A.xlsx"),
    ("2B", "U3 2B.xlsx"),
]

# Grupo (nivel) -> cursos que lo componen
ACT_GRUPOS = [
    ("1M", "1º Medio", ["1A", "1B", "1C"]),
    ("2M", "2º Medio", ["2A", "2B"]),
]


def _guardar_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build_actualizacion(base, out_dir):
    """
    Procesa la carpeta actualizacion/ (Unidad III):

    - 1A/1B/1C (32 preguntas) usan "TABLA ESPECIFICACIÓN U3 1ºMEDIO.docx".
    - 2A/2B (44 preguntas) usan "TABLA ESPECIFICACIONES PRUEBS .docx".

    Genera analisis/data_u3.json sin tocar analisis/data.json.
    """
    act_dir = os.path.join(base, "actualizacion")

    esp_1m_path = _buscar_archivo(act_dir, "u3", "1º")
    esp_2m_path = _buscar_archivo(act_dir, "pruebs")
    if not esp_1m_path or not esp_2m_path:
        print("[error] No se encontraron los .docx de especificaciones en actualizacion/")
        return

    print(f"[Modo actualizacion] Spec 1º Medio: {os.path.basename(esp_1m_path)}")
    esp_1m, conteo_1m = leer_especificaciones_docx_generico(esp_1m_path)
    print(f"  Preguntas: {len(esp_1m)}  Por habilidad: {conteo_1m}")

    print(f"[Modo actualizacion] Spec 2º Medio: {os.path.basename(esp_2m_path)}")
    esp_2m, conteo_2m = leer_especificaciones_docx_generico(esp_2m_path)
    print(f"  Preguntas: {len(esp_2m)}  Por habilidad: {conteo_2m}")

    specs_por_curso = {}
    for curso, archivo in ACT_CURSOS:
        specs_por_curso[curso] = (esp_1m, conteo_1m) if curso.startswith("1") else (esp_2m, conteo_2m)

    # --- Leer tabulaciones ---
    est = {}
    for curso, archivo in ACT_CURSOS:
        ruta = os.path.join(act_dir, archivo)
        estudiantes = leer_tabulacion(ruta)
        for e in estudiantes:
            e["curso"] = curso
        est[curso] = estudiantes
        print(f"  Leyendo {curso}: {len(estudiantes)} estudiantes ({os.path.basename(ruta)})")

    # --- Nombres editables ---
    nombres_path = os.path.join(out_dir, "nombres_u3.json")
    nombres = cargar_nombres(nombres_path)
    if nombres is None:
        nombres = {c: {e["numero"]: e["nombre"] for e in est[c]} for c in est}
        _guardar_json(nombres_path, nombres)
        print(f"\n[info] Generado {nombres_path} (editable).")
    else:
        print(f"\n[info] Usando nombres desde: {nombres_path}")

    for curso in est:
        aplicar_nombres(est[curso], curso, nombres)

    # --- Construir vistas (grupo por nivel + cada curso) ---
    prueba_general = "Unidad III - Actualización"
    vistas = []

    def crear_vista(key, label, grupo, grupo_label, cursos):
        esp, conteo = specs_por_curso[cursos[0]]
        alumnos = [e for c in cursos for e in est[c]]
        ind = calcular_indicadores(alumnos, esp, conteo)
        return {
            "key": key,
            "label": label,
            "grupo": grupo,
            "grupo_label": grupo_label,
            "tipo": "grupo" if len(cursos) > 1 else "curso",
            "cursos": cursos,
            "prueba": f"{prueba_general} - {grupo_label}",
            "total_preguntas": len(esp),
            "conteo_habilidad": conteo,
            "especificaciones": [
                {"pregunta": p, "habilidad": h}
                for p, h in sorted(esp.items())
            ],
            "indicador": ind,
        }

    for grupo, grupo_label, cursos in ACT_GRUPOS:
        vistas.append(crear_vista(
            grupo, f"{grupo_label} ({'+'.join(cursos)})", grupo, grupo_label, cursos
        ))
        for c in cursos:
            vistas.append(crear_vista(c, c, grupo, grupo_label, [c]))

    data = {
        "meta": {
            "prueba": prueba_general,
            "umbrales": {"verde": umb_verde, "amarillo": umb_amarillo},
        },
        "vistas": vistas,
    }

    out_path = os.path.join(out_dir, "data_u3.json")
    _guardar_json(out_path, data)
    print(f"\nDatos guardados en: {out_path}")

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN UNIDAD III")
    print("=" * 60)
    for v in vistas:
        ind = v["indicador"]
        print(f"\n[{v['label']}] ({v['prueba']})")
        print(f"  N° Estudiantes: {ind['n_estudiantes']}")
        print(f"  % Logro General: {ind['logro_general']}%")
        for hab, pct in ind["por_habilidad"].items():
            print(f"  % {hab.capitalize()}: {pct}%")
        print(f"  Niveles (Logro General): {ind['niveles_logro']}")


# ---------------------------------------------------------------------------
# Modo actualizacion/: Semana Intensiva 3 (2º Medio, Forma A)
# ---------------------------------------------------------------------------

SEM3_PRUEBA = "Semana Intensiva 3 - Forma A"

# Curso -> hoja del libro SEM INT 3 2A.xlsx
SEM3_CURSOS = [
    ("2A", 1),
    ("2B", 2),
]

SEM3_GRUPOS = [
    ("2M", "2º Medio", ["2A", "2B"]),
]

HABILIDADES = ["LOCALIZAR", "RELACIONAR", "REFLEXIONAR"]

# Alias editables para emparejar nombres entre Semana Intensiva 2 y 3.
# Se usan sólo cuando el nombre normalizado no coincide de forma exacta.
# "BENJAMIN" (2B) queda fuera a propósito: no se pudo determinar si es
# BENJA REBOLLEDO o BENJA VALDI.
ALIAS_INTENSIVAS_DEFAULT = {
    "2A": {
        "LIKAN": "LIKAN COMULAI",
        "CLAUDIO": "CLAUDIO N",
        "BENJAMIN ARIAS": "BENJA ARIAS",
        "VICENTE OLAVARRIA": "VICENTE O",
        "SEBASTIAN JEREZ": "SEBA JEREZ",
        "JOHN": "JHON MONJE",
        "JUAN": "JUAN ALVAREZ",
        "BLANQUITA VILLALON": "BLANQUITA",
        "YERALD OCARES": "YERALD",
        "JAVIER CATALAN": "JAVIER",
        "AMBAR MORENO": "AMBAR",
        "DANAYS ARENAS": "DANAYS",
        "SERGIO": "SERGIO ALVAREZ",
        "PAMELA MARTINEZ": "PAMELA",
        "RACHEL CABRERA": "RACHEL",
        "FCA ROA": "FRANCISCA ROA",
    },
    "2B": {
        "DEVORA": "DEBORA",
        "MONSERRAT SOLIS": "MONSE SOLIS",
        "MONSERRAT H": "MONSERRAT",
        "CAMILA": "CAMILA PAREJA",
        "DEIVY": "DEIVY AVILA",
        "FRANCISCO ORTEGA": "FCO ORTEGA",
        "JUSTIN GARNICA": "JUSTIN",
        "BASTIAN A": "BASTIAN",
        "OLIVER F": "OLIVER",
        "ANJEL CARDENAS": "ANJEL",
    },
}


def _normalizar_nombre(texto):
    """Mayúsculas, sin tildes, sin puntuación y con espacios simples."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _cargar_alias(path):
    """Carga alias_intensivas.json o crea una versión inicial editable."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    _guardar_json(path, ALIAS_INTENSIVAS_DEFAULT)
    print(f"[info] Generado {path} (editable).")
    return ALIAS_INTENSIVAS_DEFAULT


def _resumen_indicador(ind):
    return {
        "n_estudiantes": ind["n_estudiantes"],
        "logro_general": ind["logro_general"],
        "por_habilidad": ind["por_habilidad"],
        "niveles_logro": ind["niveles_logro"],
    }


def _fila_estudiante(detalle, curso):
    return {
        "curso": curso,
        "nombre": detalle["nombre"],
        "pct_general": detalle["pct_general"],
        "nivel": detalle["nivel"],
        "por_habilidad": detalle["por_habilidad"],
        "nivel_por_habilidad": detalle["nivel_por_habilidad"],
    }


def _delta(actual, anterior):
    if actual is None or anterior is None:
        return None
    return round(actual - anterior, 1)


def _fila_comparada(detalle_sem2, detalle_sem3, curso):
    row = {
        "curso": curso,
        "nombre": (detalle_sem3 or detalle_sem2)["nombre"],
        "sem2": _fila_estudiante(detalle_sem2, curso) if detalle_sem2 else None,
        "sem3": _fila_estudiante(detalle_sem3, curso) if detalle_sem3 else None,
        "delta_general": None,
        "delta_por_habilidad": {},
    }
    if detalle_sem2 and detalle_sem3:
        row["delta_general"] = _delta(
            detalle_sem3["pct_general"], detalle_sem2["pct_general"]
        )
        row["delta_por_habilidad"] = {
            h: _delta(
                detalle_sem3["por_habilidad"].get(h, 0),
                detalle_sem2["por_habilidad"].get(h, 0),
            )
            for h in HABILIDADES
        }
    return row


def _emparejar_curso(curso, ind_sem2, ind_sem3, alias_curso):
    """
    Empareja estudiantes por nombre normalizado, aplicando alias editables.
    Devuelve (filas_comparadas, sin_pareja).
    """
    mapa_sem2 = {}
    for d in ind_sem2["detalle_estudiantes"]:
        clave = _normalizar_nombre(d["nombre"])
        if clave in mapa_sem2:
            print(f"[aviso] Nombre duplicado en Semana 2 - {curso}: {d['nombre']}")
        mapa_sem2.setdefault(clave, d)

    alias_norm = {
        _normalizar_nombre(k): v for k, v in (alias_curso or {}).items()
    }

    usados = set()
    filas = []
    for d3 in ind_sem3["detalle_estudiantes"]:
        clave = _normalizar_nombre(d3["nombre"])
        objetivo = alias_norm.get(clave)
        d2 = None
        if objetivo:
            d2 = mapa_sem2.get(_normalizar_nombre(objetivo))
        if d2 is None:
            d2 = mapa_sem2.get(clave)
        if d2 is not None and id(d2) in usados:
            d2 = None
        if d2 is not None:
            usados.add(id(d2))
        filas.append(_fila_comparada(d2, d3, curso))

    for d2 in ind_sem2["detalle_estudiantes"]:
        if id(d2) not in usados:
            filas.append(_fila_comparada(d2, None, curso))

    sin_pareja = [
        {
            "curso": f["curso"],
            "nombre": f["nombre"],
            "semana": "Semana 3" if f["sem2"] is None else "Semana 2",
            "pct_general": (
                f["sem3"]["pct_general"] if f["sem3"] else f["sem2"]["pct_general"]
            ),
            "motivo": (
                "Sin coincidencia en Semana 2"
                if f["sem2"] is None
                else "Sin datos en Semana 3"
            ),
        }
        for f in filas
        if f["sem2"] is None or f["sem3"] is None
    ]
    return filas, sin_pareja


def _crear_comparativa(data_sem2, data_sem3, vistas_sem3, alias):
    vistas = {}
    pares = [
        ("2M", "2º Medio (2A+2B)", "general", "2M"),
        ("2A", "2A", "2A", "2A"),
        ("2B", "2B", "2B", "2B"),
    ]
    for key, label, key_sem2, key_sem3 in pares:
        anterior = data_sem2["indicadores"][key_sem2]
        actual = vistas_sem3[key_sem3]["indicador"]
        vistas[key] = {
            "key": key,
            "label": label,
            "anterior": _resumen_indicador(anterior),
            "actual": _resumen_indicador(actual),
        }

    estudiantes = []
    sin_pareja = []
    for curso in ["2A", "2B"]:
        filas, faltantes = _emparejar_curso(
            curso,
            data_sem2["indicadores"][curso],
            vistas_sem3[curso]["indicador"],
            alias.get(curso, {}),
        )
        estudiantes.extend(filas)
        sin_pareja.extend(faltantes)

    return {
        "meta": {
            "anterior": {
                "numero": data_sem2["meta"].get("semana", 2),
                "prueba": data_sem2["meta"]["prueba"],
                "total_preguntas": data_sem2["meta"]["total_preguntas"],
                "conteo_habilidad": data_sem2.get("conteo_habilidad", {}),
            },
            "actual": {
                "numero": 3,
                "prueba": data_sem3["meta"]["prueba"],
                "total_preguntas": data_sem3["meta"]["total_preguntas"],
                "conteo_habilidad": data_sem3["conteo_habilidad"],
            },
            "umbrales": {"verde": umb_verde, "amarillo": umb_amarillo},
        },
        "vistas": vistas,
        "estudiantes": estudiantes,
        "sin_pareja": sin_pareja,
    }


def build_sem3(base, out_dir):
    """
    Procesa la carpeta actualizacion/ (Semana Intensiva 3, 2º Medio):

    - Lee las hojas 2 A y 2 B de "SEM INT 3 2A.xlsx".
    - Lee "TABLA PRUEBA SEM 3.docx" (38 preguntas).
    - Genera analisis/data_sem3.json.
    - Genera analisis/data_comparativa.json comparando con la Semana
      Intensiva 2 (analisis/data.json).
    """
    act_dir = os.path.join(base, "actualizacion")
    xlsx_path = _buscar_archivo(act_dir, "sem", "int", "3")
    docx_path = _buscar_archivo(act_dir, "tabla", "prueba", "sem")
    if not xlsx_path or not docx_path:
        print("[error] No se encontraron los archivos de la Semana Intensiva 3 en actualizacion/")
        return

    print(f"[Modo Semana Intensiva 3] Tabulación: {os.path.basename(xlsx_path)}")
    print(f"[Modo Semana Intensiva 3] Especificaciones: {os.path.basename(docx_path)}")
    esp, conteo = leer_especificaciones_docx_generico(docx_path)
    print(f"  Preguntas: {len(esp)}  Por habilidad: {conteo}")

    est = {}
    for curso, hoja in SEM3_CURSOS:
        estudiantes = leer_tabulacion(xlsx_path, sheet=hoja)
        for e in estudiantes:
            e["curso"] = curso
        est[curso] = estudiantes
        print(f"  Leyendo {curso}: {len(estudiantes)} estudiantes (hoja {hoja})")

    nombres_path = os.path.join(out_dir, "nombres_sem3.json")
    nombres = cargar_nombres(nombres_path)
    if nombres is None:
        nombres = {c: {e["numero"]: e["nombre"] for e in est[c]} for c in est}
        _guardar_json(nombres_path, nombres)
        print(f"\n[info] Generado {nombres_path} (editable).")
    else:
        print(f"\n[info] Usando nombres desde: {nombres_path}")

    for curso in est:
        aplicar_nombres(est[curso], curso, nombres)

    vistas = []
    for grupo, grupo_label, cursos in SEM3_GRUPOS:
        alumnos = [e for c in cursos for e in est[c]]
        ind = calcular_indicadores(alumnos, esp, conteo)
        vistas.append({
            "key": grupo,
            "label": f"{grupo_label} ({'+'.join(cursos)})",
            "grupo": grupo,
            "grupo_label": grupo_label,
            "tipo": "grupo",
            "cursos": cursos,
            "prueba": f"{SEM3_PRUEBA} - {grupo_label}",
            "total_preguntas": len(esp),
            "conteo_habilidad": conteo,
            "especificaciones": [
                {"pregunta": p, "habilidad": h}
                for p, h in sorted(esp.items())
            ],
            "indicador": ind,
        })
        for c in cursos:
            alumnos_curso = est[c]
            ind_curso = calcular_indicadores(alumnos_curso, esp, conteo)
            vistas.append({
                "key": c,
                "label": c,
                "grupo": grupo,
                "grupo_label": grupo_label,
                "tipo": "curso",
                "cursos": [c],
                "prueba": f"{SEM3_PRUEBA} - {grupo_label}",
                "total_preguntas": len(esp),
                "conteo_habilidad": conteo,
                "especificaciones": [
                    {"pregunta": p, "habilidad": h}
                    for p, h in sorted(esp.items())
                ],
                "indicador": ind_curso,
            })

    data = {
        "meta": {
            "prueba": SEM3_PRUEBA,
            "semana": 3,
            "total_preguntas": len(esp),
            "umbrales": {"verde": umb_verde, "amarillo": umb_amarillo},
        },
        "conteo_habilidad": conteo,
        "vistas": vistas,
    }

    out_path = os.path.join(out_dir, "data_sem3.json")
    _guardar_json(out_path, data)
    print(f"\nDatos guardados en: {out_path}")

    # Comparativa con Semana Intensiva 2 (data.json)
    sem2_path = os.path.join(out_dir, "data.json")
    if not os.path.exists(sem2_path):
        print(f"[aviso] No existe {sem2_path}; no se generó la comparativa.")
    else:
        with open(sem2_path, "r", encoding="utf-8") as f:
            data_sem2 = json.load(f)
        alias_path = os.path.join(out_dir, "alias_intensivas.json")
        alias = _cargar_alias(alias_path)
        vistas_por_key = {v["key"]: v for v in vistas}
        comp = _crear_comparativa(data_sem2, data, vistas_por_key, alias)
        comp_path = os.path.join(out_dir, "data_comparativa.json")
        _guardar_json(comp_path, comp)
        emparejados = sum(1 for e in comp["estudiantes"] if e["sem2"] and e["sem3"])
        print(f"Comparativa guardada en: {comp_path}")
        print(
            f"  Estudiantes emparejados: {emparejados} · "
            f"sin pareja: {len(comp['sin_pareja'])}"
        )

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN SEMANA INTENSIVA 3")
    print("=" * 60)
    for v in vistas:
        ind = v["indicador"]
        print(f"\n[{v['label']}] ({v['prueba']})")
        print(f"  N° Estudiantes: {ind['n_estudiantes']}")
        print(f"  % Logro General: {ind['logro_general']}%")
        for hab, pct in ind["por_habilidad"].items():
            print(f"  % {hab.capitalize()}: {pct}%")
        print(f"  Niveles (Logro General): {ind['niveles_logro']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base, "analisis")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "data.json")

    if "--actualizacion" in sys.argv:
        build_actualizacion(base, out_dir)
        return

    if "--sem3" in sys.argv:
        build_sem3(base, out_dir)
        return

    usar_cami = "--cami" in sys.argv

    if usar_cami:
        # --- Modo CAMI: archivos de la carpeta cami/ (Semana Intensiva 2) ---
        esp_path = os.path.join(base, "cami", "Tabla de especificaciones y respuestas simce lenguaje octubre 2025 (1) (1).docx")
        a2_path = os.path.join(base, "cami", "2A INTENSIVA 2.xlsx")
        b2_path = os.path.join(base, "cami", "2B SEM INTEN 2.xlsx")
        nombre_prueba = "Semana Intensiva 2 - SIMCE Lenguaje Oct 2025"
        nombres_file = "nombres_cami.json"

        print(f"[Modo CAMI] Leyendo especificaciones (.docx): {esp_path}")
        especificaciones, conteo_hab = leer_especificaciones_docx(esp_path)
        print(f"  Preguntas: {len(especificaciones)}")
        print(f"  Por habilidad: {conteo_hab}")
    else:
        # --- Modo original: Prueba Unidad II ---
        esp_path = os.path.join(base, "TABLA ESPECIFICACIONES UNIDAD II.xlsx")
        a2_path = os.path.join(base, "2A TABULACION 4.xlsx")
        b2_path = os.path.join(base, "TABULACION 2B 4.xlsx")
        nombre_prueba = "Prueba Unidad II - 2o Medio"
        nombres_file = "nombres.json"

        print(f"Leyendo especificaciones: {esp_path}")
        especificaciones, conteo_hab = leer_especificaciones(esp_path)
        print(f"  Preguntas: {len(especificaciones)}")
        print(f"  Por habilidad: {conteo_hab}")

    print(f"\nLeyendo 2A: {a2_path}")
    est_a = leer_tabulacion(a2_path)
    print(f"  Estudiantes: {len(est_a)}")

    print(f"\nLeyendo 2B: {b2_path}")
    est_b = leer_tabulacion(b2_path)
    print(f"  Estudiantes: {len(est_b)}")

    # --- Nombres editables ---
    nombres_path = os.path.join(out_dir, nombres_file)
    nombres = cargar_nombres(nombres_path)
    if nombres is None:
        print(f"\n[info] No existe {nombres_path}; generando version inicial desde el Excel.")
        nombres = generar_nombres(nombres_path, est_a, est_b)
        print(f"       Editalo a mano y vuelve a ejecutar este script para aplicar los cambios.")
    else:
        print(f"\n[info] Usando nombres desde: {nombres_path}")

    # Aplicar nombres editables a cada curso
    aplicar_nombres(est_a, "2A", nombres)
    aplicar_nombres(est_b, "2B", nombres)

    # Marcar curso y numero en cada estudiante (para el detalle y filtros en la web)
    for e in est_a:
        e["curso"] = "2A"
    for e in est_b:
        e["curso"] = "2B"
    est_combinado = est_a + est_b

    indicadores = {
        "general": calcular_indicadores(est_combinado, especificaciones, conteo_hab),
        "2A": calcular_indicadores(est_a, especificaciones, conteo_hab),
        "2B": calcular_indicadores(est_b, especificaciones, conteo_hab),
    }

    # Lista de la tabla de especificación (pregunta -> habilidad)
    especificacion_lista = [
        {"pregunta": p, "habilidad": h}
        for p, h in sorted(especificaciones.items())
    ]

    data = {
        "meta": {
            "prueba": nombre_prueba,
            "total_preguntas": len(especificaciones),
            "umbrales": {"verde": umb_verde, "amarillo": umb_amarillo},
        },
        "especificaciones": especificacion_lista,
        "conteo_habilidad": conteo_hab,
        "cursos": ["general", "2A", "2B"],
        "nombres_cursos": {
            "general": "2º Medio (2A + 2B)",
            "2A": "Curso 2A",
            "2B": "Curso 2B",
        },
        "indicadores": indicadores,
    }
    if usar_cami:
        data["meta"]["semana"] = 2

    # Backup: si ya existe data.json, guardar como data_anterior.json
    if os.path.exists(out_path):
        anterior_path = os.path.join(out_dir, "data_anterior.json")
        shutil.copy2(out_path, anterior_path)
        print(f"\nBackup del data.json anterior guardado en: {anterior_path}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nDatos guardados en: {out_path}")

    # Resumen en consola
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for curso in ["general", "2A", "2B"]:
        ind = indicadores[curso]
        print(f"\n[{data['nombres_cursos'][curso]}]")
        print(f"  N° Estudiantes: {ind['n_estudiantes']}")
        print(f"  % Logro General: {ind['logro_general']}%")
        for hab in ["LOCALIZAR", "RELACIONAR", "REFLEXIONAR"]:
            print(f"  % {hab.capitalize()}: {ind['por_habilidad'].get(hab, 0)}%")
        print(f"  Niveles (Logro General): {ind['niveles_logro']}")
        for hab in ["LOCALIZAR", "RELACIONAR", "REFLEXIONAR"]:
            print(f"  Niveles {hab.capitalize()}: {ind['niveles_por_habilidad'].get(hab)}")


if __name__ == "__main__":
    main()