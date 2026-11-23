#!/usr/bin/env python3
"""Apuntes en markdown con LaTeX -> HTML con KaTeX -> PDF (Chrome sin cabeza).
Uso: python3 herramientas/pdf.py produccion/clase-05/notes.md   (deja notes.pdf al lado)
Las fórmulas se sacan antes de pasar el markdown y se devuelven después, para
que el markdown no toque guiones bajos ni barras invertidas dentro de ellas."""
import html, os, re, subprocess, sys, tempfile
import markdown

md_path = os.path.abspath(sys.argv[1])
texto = open(md_path, encoding="utf-8").read()
guardadas = []
def guardar(m):
    guardadas.append(m.group(0))
    return f"@@MATH{len(guardadas) - 1}@@"
texto = re.sub(r"\$\$.+?\$\$|\$[^$\n]+?\$", guardar, texto, flags=re.S)
cuerpo = markdown.markdown(texto, extensions=["tables"])
def devolver(m):
    f = html.escape(guardadas[int(m.group(1))])
    # una fórmula de bloque va en su propio contenedor, que no se parte entre páginas
    return f'<div class="eq">{f}</div>' if f.startswith("$$") else f
cuerpo = re.sub(r"<p>\s*@@MATH(\d+)@@\s*</p>", devolver, cuerpo)
cuerpo = re.sub(r"@@MATH(\d+)@@", devolver, cuerpo)
# Limitación conocida (1 nov 2026): Chrome no garantiza que el título quede con
# las primeras filas de una tabla larga; puede quedar solo con el encabezado al pie.
# Un título seguido de un párrafo y una tabla viaja con la tabla: Chrome no
# respeta break-after ante una tabla, así que se vuelven el caption de la tabla.
cuerpo = re.sub(r"(<h2>(?:(?!</h2>).)*</h2>)\s*(<p>(?:(?!</p>).)*</p>)\s*<table>",
                lambda m: f'<table><caption>{m.group(1)}{m.group(2)}</caption>', cuerpo, flags=re.S)
# Una tabla corta no se parte (no deja una fila sola al pie); una larga sí, por filas.
cuerpo = re.sub(r"<table>((?:(?!</table>).)*)</table>",
                lambda m: f'<table class="{"corta" if m.group(1).count("<tr>") <= 12 else "larga"}">{m.group(1)}</table>',
                cuerpo, flags=re.S)
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
pagina = f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script src="{KATEX}/katex.min.js"></script>
<script src="{KATEX}/contrib/auto-render.min.js"></script>
<style>
@page {{ size: A4; margin: 22mm 20mm; }}
body {{ font-family: 'Latin Modern Roman', 'Georgia', serif; font-size: 11pt; line-height: 1.5; color: #1F2937; }}
h1 {{ color: #1F3A5F; font-size: 20pt; margin-bottom: 0; }}
h2 {{ color: #1F3A5F; font-size: 14pt; border-bottom: 1px solid #D1D5DB; padding-bottom: 3px; margin-top: 22px; break-after: avoid; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 10pt; }}
tr {{ break-inside: avoid; }}
table.corta {{ break-inside: avoid; }}
caption {{ text-align: left; caption-side: top; break-after: avoid; }}
caption h2 {{ margin-top: 0; }}
h2 {{ break-after: avoid; }}
h2 + p {{ break-before: avoid; }}
.eq {{ break-inside: avoid; page-break-inside: avoid; display: block; overflow: hidden; padding: 2px 0; }}
th, td {{ border: 1px solid #D1D5DB; padding: 5px 7px; text-align: left; }}
th {{ background: #F3F4F6; }}
hr {{ border: none; border-top: 1px solid #D1D5DB; margin: 18px 0; }}
code {{ font-size: 9.5pt; }}
.katex-display {{ margin: 0.7em 0; break-inside: avoid; }}
h2 + p, h2 + table {{ break-before: avoid; }}
h2 {{ break-after: avoid-page; }}
</style></head><body>{cuerpo}
<script>
renderMathInElement(document.body, {{delimiters: [{{left: "$$", right: "$$", display: true}}, {{left: "$", right: "$", display: false}}], throwOnError: true}});
document.title = "done";
</script></body></html>"""
with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(pagina)
pdf = md_path[:-3] + ".pdf"
subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", "file://" + f.name],
               check=True, capture_output=True)
os.unlink(f.name)
# Si KaTeX no cargó (sin red), Chrome imprime el LaTeX crudo sin dar error: se comprueba.
texto_pdf = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
if re.search(r"\$\$|\\frac|\\int|\\omega", texto_pdf):
    sys.exit(f"FALLA: el PDF tiene LaTeX sin dibujar (¿KaTeX no cargó?): {pdf}")
print(pdf)
