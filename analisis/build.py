#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesa los archivos .xlsx de tabulación y la tabla de especificaciones
de la Prueba Unidad II (2o Medio) y genera data.json con los indicadores
y distribuciones por nivel para la web de resultados.

Entradas (en la carpeta padre):
  - TABLA ESPECIFICACIONES UNIDAD II.xlsx  (pregunta -> habilidad)
  - 2A TABULACION 4.xlsx                   (curso 2A)
  - TABULACION 2B 4.xlsx                   (curso 2B)

Salida:
  - analisis/data.json
"""

import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

# ---------------------------------------------------------------------------
# Utilidades para leer .xlsx sin dependencias externas
# ---------------------------------------------------------------------------

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _read_xlsx(path):
    """Devuelve una lista de filas; cada fila es un dict {letra_col: valor}."""
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
    # hoja 1
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
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


# ---------------------------------------------------------------------------
# Lectura de una tabulación
# ---------------------------------------------------------------------------

def leer_tabulacion(path):
    """
    Devuelve lista de estudiantes:
      [{"numero": str, "nombre": str, "respuestas": {1:'C', 2:'I', ...}}]
    Se asume: col A = número de lista, col B = nombre, cols C..AP = preguntas 1..40.
    Valores válidos: 'C' o 'I'. Se ignoran filas vacías y otros valores.
    """
    rows = _read_xlsx(path)
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
# Main
# ---------------------------------------------------------------------------

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    esp_path = os.path.join(base, "TABLA ESPECIFICACIONES UNIDAD II.xlsx")
    a2_path = os.path.join(base, "2A TABULACION 4.xlsx")
    b2_path = os.path.join(base, "TABULACION 2B 4.xlsx")

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

    # --- Nombres editables (nombres.json) ---
    out_dir = os.path.join(base, "analisis")
    nombres_path = os.path.join(out_dir, "nombres.json")
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
            "prueba": "Prueba Unidad II - 2o Medio",
            "total_preguntas": len(especificaciones),
            "umbrales": {"verde": umb_verde, "amarillo": umb_amarillo},
        },
        "especificaciones": especificacion_lista,
        "conteo_habilidad": conteo_hab,
        "cursos": ["general", "2A", "2B"],
        "nombres_cursos": {
            "general": "General (2A + 2B)",
            "2A": "Curso 2A",
            "2B": "Curso 2B",
        },
        "indicadores": indicadores,
    }

    out_dir = os.path.join(base, "analisis")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "data.json")
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