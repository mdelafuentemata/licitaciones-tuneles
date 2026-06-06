# Cómo poner esto en marcha (paso a paso)

Sigue los pasos en orden. Tardas ~10 minutos. Todo es gratis.

## 1. Crear el repositorio en GitHub

1. Entra en https://github.com con tu cuenta (`mdelafuentemataia@gmail.com`).
2. Arriba a la derecha, pulsa **+** → **New repository**.
3. Rellena:
   - **Repository name:** `licitaciones-tuneles`
   - **Description:** `Web automática de licitaciones de túneles (obra civil + ingeniería) en España`
   - **Public** (déjalo marcado).
   - **NO** marques "Add a README", "Add .gitignore" ni "Choose a license" — esos archivos los traemos nosotros.
4. Pulsa **Create repository**.

## 2. Subir los archivos

Tienes los archivos en la carpeta `licitaciones-tuneles-github` que te ha generado Claude. Súbelos al repo:

### Opción A — Arrastrar y soltar desde la web (sin Git instalado)

1. En la página recién creada del repo, verás la frase **"…or upload an existing file"**. Haz clic en ese enlace.
2. Abre la carpeta `licitaciones-tuneles-github` en tu explorador de archivos.
3. Selecciona TODO el contenido (Ctrl+A): `index.html`, `data.json`, `.nojekyll`, `README.md`, `INSTRUCCIONES.md`, y las carpetas `scraper/` y `.github/`.
4. Arrástralo todo a la página de GitHub.

   ⚠️ **Importante:** GitHub a veces no muestra los archivos ocultos (los que empiezan por `.`) en el arrastrado. Si no aparecen `.github/workflows/scrape.yml` ni `.nojekyll`, tendrás que subirlos con la Opción B, o crearlos manualmente desde GitHub (ver más abajo).

5. Abajo, en "Commit changes", pon como mensaje: `Versión inicial`.
6. Pulsa **Commit changes**.

### Opción B — Con Git instalado en tu PC

```bash
cd ruta/a/licitaciones-tuneles-github
git init
git add .
git commit -m "Versión inicial"
git branch -M main
git remote add origin https://github.com/mdelafuentemataia/licitaciones-tuneles.git
git push -u origin main
```

### Si los archivos ocultos no se subieron por Opción A

Para `.github/workflows/scrape.yml`:
1. En el repo, pulsa **Add file** → **Create new file**.
2. En el campo del nombre escribe: `.github/workflows/scrape.yml` (con las barras; GitHub creará las subcarpetas automáticamente).
3. Pega el contenido del archivo que tienes localmente.
4. **Commit changes**.

Para `.nojekyll`:
1. **Add file** → **Create new file**.
2. Nombre: `.nojekyll`.
3. Déjalo en blanco.
4. **Commit changes**.

## 3. Activar GitHub Pages

1. En el repo, ve a **Settings** (arriba) → **Pages** (menú lateral izquierdo).
2. En **Source**, elige **Deploy from a branch**.
3. En **Branch**, selecciona `main` y carpeta `/ (root)`.
4. Pulsa **Save**.
5. Espera 1-2 minutos. Vuelve a la página y verás un cartel verde con la URL:

   `https://mdelafuentemataia.github.io/licitaciones-tuneles/`

6. Ábrela en el navegador. Deberías ver tu web con los datos iniciales.

## 4. Activar Actions y probar el scraper

1. Ve a la pestaña **Actions** del repo (arriba, junto a Code, Issues, etc.).
2. La primera vez GitHub te pide confirmación: **I understand my workflows, go ahead and enable them**. Pulsa.
3. En el menú lateral verás **Scrape BOE semanal**. Haz clic.
4. A la derecha, pulsa **Run workflow** → **Run workflow** (botón verde).
5. Espera 1-2 minutos. Aparecerá un círculo verde si todo va bien (rojo si falla).
6. Si va bien, el scraper habrá actualizado `data.json` y la web se redesplegará sola en otros 30 segundos.

## 5. Listo

A partir de ahora, **cada lunes a las 10:00 hora Madrid**, el scraper se ejecutará solo, actualizará `data.json` y la web se redesplegará automáticamente. Tú solo tienes que abrir la URL para consultarla.

## Cómo mejorar la web en el futuro

Cualquier cambio (en `index.html`, en el scraper, en los estilos):

1. Editas el archivo directamente desde la web de GitHub (icono del lápiz arriba a la derecha del archivo) o desde tu PC.
2. **Commit changes**.
3. La web se redesplega automáticamente en ~30 segundos.

No hay que reinstalar nada. Si la siguiente vez quieres que yo te ayude con un cambio, dímelo y te paso el archivo modificado para que lo pegues, o te explico exactamente qué línea cambiar.

## Si algo falla

- **El workflow da error rojo en Actions:** abre la ejecución, mira el log, copia el error y pásamelo.
- **La web carga vacía:** abre la consola del navegador (F12), mira si hay error de carga de `data.json`. Suele ser un fallo de JSON malformado.
- **No se actualiza la web tras un cambio:** comprueba en Settings → Pages que el despliegue está activo y que el último commit aparece. A veces tarda 1-2 minutos.
