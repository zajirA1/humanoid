"""Sestaví samostatnou stránku z rozhraní a modelu GLB v měřítku metrů."""
import base64
from pathlib import Path


def sestav():
    src = Path(__file__).resolve().parent
    web = src.parents[1] / "web" / "app" / "emil-eta.html"
    sablona = (src / "rozhrani.html").read_text(encoding="utf-8")
    styl = (src / "styl.css").read_text(encoding="utf-8")
    scenar = "\n".join((src / soubor).read_text(encoding="utf-8")
                        for soubor in ("pohyb.js", "vykresleni.js", "ovladani.js"))
    glb = base64.b64encode((src / "Emil-V2.glb").read_bytes()).decode("ascii")
    html = sablona.replace("/* VLOZ_STYL */", styl)
    html += f'<script type="application/octet-stream" id="model">{glb}</script>\n'
    html += f"<script>\n{scenar}\n</script></body></html>\n"
    web.write_bytes(html.encode("utf-8"))


if __name__ == "__main__":
    sestav()
