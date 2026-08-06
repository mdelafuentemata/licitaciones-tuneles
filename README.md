# Licitaciones de túneles · obra civil e ingeniería

Web automática que muestra las licitaciones publicadas en la Plataforma de Contratación del Sector Público (PLACSP / BOE Sección V·A) cuyo objeto es obra civil o ingeniería de túneles y obras subterráneas.

## Cómo funciona

- Una vez por semana (lunes, 10:00 hora Madrid), un workflow de **GitHub Actions** ejecuta `scraper/scrape.py`.
- El scraper rastrea los anuncios de Sección V·A del BOE de los 7 días anteriores, aplica un doble barrido (palabras clave de túnel + códigos CPV específicos) y filtra exclusiones (edificación, instalaciones electromecánicas).
- Los resultados se vuelcan a `data.json`.
- El commit del JSON actualizado dispara automáticamente el despliegue en **GitHub Pages**.

## Estructura

```
.
├── index.html              # Página web (lee data.json al cargar)
├── data.json               # Datos de licitaciones (actualizado por el scraper)
├── scraper/
│   ├── scrape.py           # Lógica de rastreo y filtrado
│   └── requirements.txt    # Dependencias Python
└── .github/workflows/
    └── scrape.yml          # Workflow semanal
```

## Criterios de filtrado

**Incluidas:**
- Obra civil sobre la galería del túnel (excavación, sostenimiento, revestimiento, drenaje, impermeabilización, rehabilitación estructural, emboquilles, ventilación construida).
- Servicios de ingeniería sobre túnel (redacción de proyectos, dirección facultativa, asistencia técnica, supervisión).

**Excluidas:**
- Edificación, aunque sea próxima al túnel (edificios anejos al emboquille, centros de mantenimiento, talleres).
- Instalaciones electromecánicas (señalización, balizamiento, iluminación, CCTV, telecomunicaciones, redes de aguas, ventilación como suministro de equipos, detección de incendios).
- Protección genérica de plataforma ferroviaria sin mención explícita a túnel .

## Ejecutar el scraper manualmente

Localmente:

```bash
pip install -r scraper/requirements.txt
python scraper/scrape.py
```

En GitHub: pestaña **Actions** → workflow **Scrape BOE semanal** → botón **Run workflow**.

## Fuentes

- BOE Sección V·A (Contratación del Sector Público) — https://www.boe.es/
- Plataforma de Contratación del Sector Público — https://contrataciondelestado.es/

## Licencia

MIT. Los datos extraídos del BOE son públicos y de libre reutilización. 
