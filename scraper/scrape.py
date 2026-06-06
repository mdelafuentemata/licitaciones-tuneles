#!/usr/bin/env python3
"""
Scraper semanal del BOE para licitaciones de túneles (obra civil + ingeniería).

Estrategia: doble barrido
1. Léxico amplio: cualquier anuncio con palabras clave de túnel en el título/objeto.
2. CPV: cualquier anuncio con CPV específico de túnel u obra paraguas + palabra clave.

Une, deduplica por expediente, aplica exclusiones (edificación, instalaciones electromecánicas),
clasifica en obra / ingeniería / revisar manual, y actualiza data.json en la raíz del repo.

Ejecutado por GitHub Actions cada lunes 10:00 hora Madrid.
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

# =====================================================================
# CONFIGURACIÓN
# =====================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = REPO_ROOT / "data.json"

BOE_USER_AGENT = "tunnel-tenders-bot/1.0 (+https://github.com/)"
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_REQS = 0.3   # cortesía con el BOE

# Palabras clave en el objeto del anuncio
KEYWORDS = [
    "tunel", "tuneles",
    "galeria", "galerias",
    "subterraneo", "subterranea", "subterraneos", "subterraneas",
    "emboquille", "emboquilles",
    "caverna", "cavernas",
    "falso tunel",
    "boca de mina",
]

# Palabras que indican obra civil de túnel propiamente
TUNNEL_WORK_HINTS = [
    "tunel", "galeria", "subterraneo", "emboquille",
    "revestimiento", "sostenimiento", "tratamiento tunel",
    "rehabilitacion tunel", "reparacion tunel",
]

# CPV específicos de túnel (obra)
CPV_OBRA_SPECIFIC = {
    "45221240", "45221241", "45221242", "45221243",
    "45221245", "45221246", "45221247", "45221248",
    "45221250", "45252124", "45262650",
}
# CPV paraguas de obra (necesitan refuerzo léxico)
CPV_OBRA_UMBRELLA = {"45000000", "45200000", "45220000", "45223000"}
CPV_OBRA = CPV_OBRA_SPECIFIC | CPV_OBRA_UMBRELLA

# CPV de ingeniería (servicios)
CPV_INGENIERIA = {
    "71242000", "71247000", "71300000", "71311000", "71322000", "71520000",
}

# Términos que indican que debemos EXCLUIR el anuncio
EXCLUSIONS = [
    "senalizacion", "balizamiento", "iluminacion", "luminarias",
    "cctv", "megafonia", "telecomunicaciones",
    "tren tierra", "tren-tierra",
    "proteccion al tren",
    "edificio anejo", "edificios anejos", "edificios exteriores",
    "edificio taller",
    "centro de mantenimiento", "centros de mantenimiento",
    "responsable de seguridad",
    "vigilancia presencial",
    "suministro de luminarias", "suministro y sustitucion",
    "deteccion de incendios",
    "sai", "alimentacion ininterrumpida",
    "fibra optica",
    "red contraincendios", "contraincendios",
    "ventilacion electromecanica",
]

# Mapeo de organismos a "orgGroup" para el frontend
ORG_GROUP_MAP = {
    "adif": "adif",
    "adif alta velocidad": "adif",
    "adif-alta velocidad": "adif",
    "direccion general de carreteras": "dgc",
    "confederacion hidrografica": "chs",
}


# =====================================================================
# UTILIDADES
# =====================================================================

def strip_accents(text: str) -> str:
    """Quita tildes/diéresis para hacer match case- y accent-insensitive."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def fetch(url: str) -> str:
    """GET con headers educados; devuelve texto o lanza."""
    r = requests.get(url, headers={"User-Agent": BOE_USER_AGENT}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    time.sleep(SLEEP_BETWEEN_REQS)
    return r.text


def parse_xml(text: str) -> ET.Element:
    """Parsea XML del BOE, tolerando errores menores."""
    text = text.strip()
    if not text:
        raise ValueError("XML vacío")
    return ET.fromstring(text)


# =====================================================================
# DESCARGA DE LOS ANUNCIOS DEL BOE
# =====================================================================

def daily_summary_url(date: datetime) -> str:
    return f"https://www.boe.es/diario_boe/xml.php?id=BOE-S-{date.strftime('%Y%m%d')}"


def anuncio_xml_url(anuncio_id: str) -> str:
    return f"https://www.boe.es/diario_boe/xml.php?id={anuncio_id}"


def anuncio_txt_url(anuncio_id: str) -> str:
    return f"https://www.boe.es/diario_boe/txt.php?id={anuncio_id}"


def list_anuncios_for_date(date: datetime) -> list[dict]:
    """Devuelve los anuncios de Sección V·A para una fecha dada.

    El sumario diario del BOE tiene la estructura:
      <sumario>
        <diario>
          <seccion num="5" nombre="V. Anuncios">
            <departamento nombre="...">
              <epigrafe nombre="...">
                <item id="BOE-B-2026-XXXXX">
                  <titulo>...</titulo>
                  <url_pdf>...</url_pdf>
                  <url_html>...</url_html>
                  <url_xml>...</url_xml>
                </item>
              </epigrafe>
            </departamento>
          </seccion>
        </diario>
      </sumario>
    """
    out = []
    try:
        xml_text = fetch(daily_summary_url(date))
        root = parse_xml(xml_text)
    except Exception as e:
        print(f"  ! No se pudo obtener sumario {date:%Y-%m-%d}: {e}", file=sys.stderr)
        return out

    # Buscar todas las secciones; nos interesa la V (num=5)
    for seccion in root.iter("seccion"):
        num = seccion.attrib.get("num", "")
        if num != "5":
            continue
        # Cualquier item dentro de la sección 5 es candidato
        for item in seccion.iter("item"):
            anuncio_id = item.attrib.get("id", "")
            titulo_el = item.find("titulo")
            titulo = (titulo_el.text or "").strip() if titulo_el is not None else ""
            if not anuncio_id or not titulo:
                continue
            out.append({"id": anuncio_id, "titulo": titulo})
    return out


# =====================================================================
# DETALLE DE UN ANUNCIO
# =====================================================================

def parse_anuncio_detail(anuncio_id: str) -> dict | None:
    """Devuelve un dict con los campos relevantes del anuncio o None si falla.

    Extrae del XML del BOE:
      - titulo
      - departamento / órgano
      - texto plano (para detectar objeto, plazo, importe, CPV)
    """
    try:
        xml_text = fetch(anuncio_xml_url(anuncio_id))
    except Exception as e:
        print(f"  ! Detalle {anuncio_id}: {e}", file=sys.stderr)
        return None

    try:
        root = parse_xml(xml_text)
    except Exception as e:
        print(f"  ! XML inválido {anuncio_id}: {e}", file=sys.stderr)
        return None

    # Título y departamento
    titulo = ""
    departamento = ""
    txt_el = root.find(".//metadatos")
    if txt_el is not None:
        for tag, target in [("titulo", "titulo"), ("departamento", "departamento")]:
            el = txt_el.find(tag)
            if el is not None and el.text:
                if target == "titulo":
                    titulo = el.text.strip()
                else:
                    departamento = el.text.strip()

    # Cuerpo en texto plano
    texto = ""
    texto_el = root.find(".//texto")
    if texto_el is not None:
        # Concatena todo el contenido textual
        texto = " ".join("".join(texto_el.itertext()).split())

    return {
        "id": anuncio_id,
        "titulo": titulo,
        "departamento": departamento,
        "texto": texto,
    }


# =====================================================================
# CLASIFICACIÓN
# =====================================================================

def has_keyword(text: str) -> bool:
    """¿El texto (normalizado) contiene alguna palabra clave de túnel?"""
    norm = strip_accents(text)
    return any(kw in norm for kw in KEYWORDS)


def has_exclusion(text: str) -> bool:
    """¿El texto contiene términos que excluyen la licitación?"""
    norm = strip_accents(text)
    # Solo aplica si el objeto principal es uno de los excluidos.
    # Heurística: contamos coincidencias y, si hay coincidencia con la primera línea
    # / título, lo damos por excluido. Una más permisiva podría no descartar tan fuerte.
    return any(ex in norm for ex in EXCLUSIONS)


def extract_cpvs(text: str) -> list[str]:
    """Saca todos los códigos CPV (8 dígitos) que aparecen en el texto."""
    return list(dict.fromkeys(re.findall(r"\b(\d{8})\b", text)))


def extract_expediente(text: str) -> str:
    """Intenta sacar el número de expediente del texto del anuncio."""
    m = re.search(r"Expediente[:\s]+([A-Z0-9.\-/]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_importe(text: str) -> float | None:
    """Valor estimado en euros."""
    m = re.search(r"Valor estimado[:\s]+([\d.,]+)\s*euros", text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_plazo(text: str) -> tuple[str, str]:
    """Devuelve (deadline_iso, deadline_text) si lo encuentra."""
    # Patrón típico: "Hasta las 11:00 horas del 29 de mayo de 2026"
    m = re.search(
        r"Hasta las (\d{1,2}):(\d{2}) horas? del (\d{1,2}) de (\w+) de (\d{4})",
        text, re.IGNORECASE,
    )
    if not m:
        return "", ""
    hh, mm, dd, mes_es, yyyy = m.groups()
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
        "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    mes_num = meses.get(strip_accents(mes_es), 0)
    if mes_num == 0:
        return "", ""
    try:
        dt = datetime(int(yyyy), mes_num, int(dd), int(hh), int(mm))
    except ValueError:
        return "", ""
    deadline_text = f"{int(dd)} {mes_es.lower()[:3]} {yyyy}, {hh}:{mm}"
    return dt.isoformat(), deadline_text


def extract_tipo_contrato(text: str) -> str:
    """Determina si es 'Obras' o 'Servicios' a partir del texto."""
    norm = strip_accents(text)
    if "tipo de procedimiento" in norm:
        # No es discriminante; busca por sección 'Tipo'
        pass
    # Heurística simple: si contiene "obras de" en el primer kB es obras;
    # si contiene "servicios de" es servicios
    head = norm[:1500]
    if "obras de" in head or "ejecucion de las obras" in head:
        return "Obras"
    if "servicios de" in head or "asistencia tecnica" in head or "redaccion de proyecto" in head:
        return "Servicios"
    return ""


def org_group_for(departamento: str) -> str:
    norm = strip_accents(departamento)
    if "adif" in norm:
        return "adif"
    if "carreteras" in norm:
        return "dgc"
    if "confederacion hidrografica" in norm or "chs" in norm:
        return "chs"
    return ""


def classify(detail: dict) -> dict | None:
    """Aplica las reglas y devuelve el registro listo para data.json, o None si se descarta."""
    titulo = detail["titulo"]
    texto  = detail["texto"]
    combo  = f"{titulo} {texto}"

    # ¿Tiene palabras clave en el título?
    kw_hit = has_keyword(combo)

    # Extraemos CPVs y vemos en qué lista caen
    cpvs   = extract_cpvs(combo)
    has_cpv_obra_specific = any(c in CPV_OBRA_SPECIFIC for c in cpvs)
    has_cpv_obra_umbrella = any(c in CPV_OBRA_UMBRELLA for c in cpvs)
    has_cpv_ing           = any(c in CPV_INGENIERIA for c in cpvs)

    # Si no entra por léxico ni por CPV, descartar
    if not kw_hit and not has_cpv_obra_specific and not has_cpv_ing:
        return None

    # Exclusiones — descarte fuerte
    if has_exclusion(titulo):
        return None

    # Determina tipo y CPV principal
    cpv_principal = cpvs[0] if cpvs else ""

    if has_cpv_obra_specific and kw_hit:
        type_ = "obra"
        confidence = "alta"
    elif has_cpv_obra_specific:
        type_ = "obra"
        confidence = "media"
    elif has_cpv_ing and kw_hit:
        type_ = "ingenieria"
        confidence = "alta"
    elif kw_hit and has_cpv_obra_umbrella:
        type_ = "obra"
        confidence = "media"
    elif kw_hit:
        # Texto menciona túnel pero CPV atípico → revisar manual
        type_ = "revisar"
        confidence = "baja"
    else:
        return None

    deadline_iso, deadline_text = extract_plazo(texto)
    # Si plazo ya pasado, marcar como cerrado (igualmente lo devolvemos; el frontend filtra)
    importe = extract_importe(texto)
    expediente = extract_expediente(texto) or detail["id"]

    return {
        "id": detail["id"].lower(),
        "type": type_,
        "title": titulo,
        "org": detail["departamento"],
        "orgGroup": org_group_for(detail["departamento"]),
        "expediente": expediente,
        "location": "",  # se podría afinar parseando texto
        "deadline": deadline_iso or None,
        "deadlineText": deadline_text or "—",
        "importe": importe,
        "duracion": "",
        "proc": "Abierto",
        "cpv": cpv_principal,
        "obj": titulo,
        "historical": False,
        "confidence": confidence,
        "boeUrl": anuncio_txt_url(detail["id"]),
        "placspUrl": "https://contrataciondelestado.es/wps/portal/licRecientes",
    }


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("== Scraper BOE — licitaciones de túneles ==")
    today = datetime.now(tz=timezone.utc).astimezone()
    print(f"Hoy: {today.isoformat()}")

    # 1. Carga data.json existente
    if DATA_JSON.exists():
        existing = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    else:
        existing = {"lastUpdate": "", "tenders": []}
    existing_by_id = {t["id"]: t for t in existing.get("tenders", [])}
    print(f"data.json existente: {len(existing_by_id)} licitaciones")

    # 2. Barrido de los últimos 7 días
    new_results = []
    for delta in range(0, 8):
        d = today - timedelta(days=delta)
        print(f"-- Sumario {d:%Y-%m-%d} --")
        anuncios = list_anuncios_for_date(d)
        print(f"   {len(anuncios)} anuncios en V·A")
        for a in anuncios:
            # Filtro rápido por título antes de descargar el detalle
            if not has_keyword(a["titulo"]):
                # Si el título no menciona túnel, igualmente puede tener CPV específico.
                # Pero por economía de red descartamos aquí.
                continue
            detail = parse_anuncio_detail(a["id"])
            if not detail:
                continue
            record = classify(detail)
            if record:
                new_results.append(record)
                print(f"   + {record['id']} [{record['type']}/{record['confidence']}] {record['title'][:80]}")

    # 3. Merge con datos existentes (los nuevos sustituyen si coinciden por id)
    merged = dict(existing_by_id)
    for r in new_results:
        merged[r["id"]] = r
    final_list = list(merged.values())

    # 4. Guardar
    payload = {
        "lastUpdate": today.isoformat(timespec="seconds"),
        "tenders": final_list,
    }
    DATA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"data.json escrito: {len(final_list)} licitaciones totales, {len(new_results)} nuevas/actualizadas.")


if __name__ == "__main__":
    main()
