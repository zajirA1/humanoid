"""Po nasazení porovná přihlášenou aplikaci a soukromé tiskové soubory s vydáním."""
import hashlib
import http.cookiejar
from html.parser import HTMLParser
import json
import os
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request
from zipfile import ZipFile
from io import BytesIO


class Formular(HTMLParser):
    csrf = None
    action = None

    def handle_starttag(self, tag, atts):
        data = dict(atts)
        if tag == "form" and data.get("method") == "post":
            self.action = data.get("action")
        if tag == "input" and data.get("name") == "csrf":
            self.csrf = data.get("value")


def over_karty(url, manifest, cookies=()):
    from playwright.sync_api import expect, sync_playwright

    parts = {p["id"]: p for p in manifest["parts"] if p["printable"]}
    if len(parts) != 54:
        raise ValueError("Katalog R16 nemá 54 tiskových dílů.")
    with sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=shutil.which("google-chrome"))
        context = browser.new_context()
        context.add_cookies([{"name": c.name, "value": c.value, "url": url,
                              "secure": True, "httpOnly": True} for c in cookies])
        page = context.new_page()
        page.goto(url)
        page.locator("#r16PartCatalog").click()
        page.locator("#r16PartFilter").select_option("print")
        choices = page.locator("#r16PartList")
        expect(choices.locator("option")).to_have_count(len(parts))
        for ident, part in parts.items():
            choices.select_option(ident)
            expect(page.locator("#r16PartTitle")).to_have_text(part["name"])
            facts = page.locator("#r16PartFacts")
            for label, value in [
                ("Příprava tiskových drah", "Prošlo · Bambu Studio"),
                ("Spotřeba filamentu", format(part["slice"]["gramy"], ".2f").replace(".", ",") + " g"),
            ]:
                field = facts.get_by_text(label, exact=True).locator("xpath=following-sibling::dd")
                expect(field).to_be_visible()
                expect(field).to_have_text(value)
            kobra = part["kobra"]
            link = page.get_by_role("link", name="Stáhnout G-code · Kobra S1 Max · 0,4 mm · " + kobra["material"], exact=True)
            expect(link).to_be_visible()
            filename = Path(kobra["file"]).name
            expect(link).to_have_attribute("download", filename)
            target = urljoin(page.url, link.get_attribute("href"))
            if urlsplit(target).netloc != urlsplit(url).netloc:
                raise ValueError(f"Odkaz mimo web u {ident}.")
            response = context.request.get(target, timeout=120000, max_redirects=0)
            if not response.ok:
                raise ValueError(f"Stažení {ident} skončilo HTTP {response.status}.")
            if cookies and response.headers.get("content-disposition") != f'attachment; filename="{filename}"':
                raise ValueError(f"Server neposlal soubor {filename} jako přílohu.")
            digest = hashlib.sha256(response.body()).hexdigest()
            response.dispose()
            if digest != kobra["sha256"] or digest != manifest["file_checksums"][kobra["file"]]:
                raise ValueError(f"Stažený G-code neodpovídá dílu {ident}.")
            print(ident, kobra["material"], kobra["gramy"], "g · G-code stažen z karty a ověřen", flush=True)
        browser.close()
    print(f"Ověřeno všech {len(parts)} zobrazených karet na {url}", flush=True)


def mistni_kontrola():
    base = Path("web/app")
    manifest = json.loads((base/"tisk/R16/catalog.json").read_bytes())
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=base)) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            over_karty(f"http://127.0.0.1:{server.server_port}/emil-h22.html", manifest)
        finally:
            server.shutdown()


def main():
    url = os.environ["URL"].rstrip("/") + "/"
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "robot.caribhaus.com":
        raise ValueError("Živou kontrolu lze provést jen na HTTPS doméně humanoida.")
    cookies = http.cookiejar.CookieJar()
    client = build_opener(HTTPCookieProcessor(cookies))
    def get(path, form=None):
        request = Request(url+path, data=urlencode(form).encode() if form else None)
        with client.open(request, timeout=45) as response:
            if response.status != 200 or urlsplit(response.url).netloc != urlsplit(url).netloc:
                raise ValueError("Neočekávaná odpověď webu.")
            return response.read()

    def endpoint(name, katalog="tisk-r16"):
        return "index.php?" + urlencode({"data": katalog, "file": name})

    def denied(name, code, katalog="tisk-r16"):
        try:
            get(endpoint(name, katalog))
        except HTTPError as err:
            if err.code == code:
                return
            raise
        raise ValueError(f"Neočekávané zpřístupnění souboru {name}")

    base = Path("web/app")
    form = Formular()
    form.feed(get("?model=emil").decode())
    if not form.csrf or form.action != "./?model=emil":
        raise ValueError("Přihlášení do Emila nezachovalo cílovou záložku.")
    denied("catalog.json", 403)
    denied("miska.stl", 403, "tisk-emil")
    emil = get(form.action, {"csrf": form.csrf, "heslo": os.environ["ROBOT_HESLO"]})
    css = b'<link rel="stylesheet" href="./modely.css">'
    if get("modely.css") != Path("web/modely.css").read_bytes():
        raise ValueError("Styly záložek neodpovídají vydání.")
    for model, odpoved in [("emil-eta", emil), ("emil-h22", get(""))]:
        aktivni = ' aria-current="page"'
        prvni = aktivni if model == "emil-h22" else ""
        druhy = aktivni if model == "emil-eta" else ""
        nav = (f'<nav id="robot-modely" aria-label="Model robota"><a href="./"{prvni}>Humanoid H22</a>'
               f'<a href="./?model=emil"{druhy}>Emil na vysavači</a></nav>').encode()
        zdroj = (base / f"{model}.html").read_bytes().replace(b"</head>", css + b"</head>", 1)
        zdroj = re.sub(br"<body\b[^>]*>", lambda match: match.group() + nav, zdroj, count=1, flags=re.I)
        bez_relace = re.sub(br'<meta name="robot-(?:csrf|api)" content="[^"]*">', b'', odpoved)
        if zdroj != bez_relace:
            raise ValueError(f"Model {model} nebo jeho přepínač neodpovídá vydání.")
    tisk = base / "tisk/emil"
    soubory = {cesta.name for cesta in tisk.iterdir() if cesta.suffix in {".stl", ".3mf"}}
    if not {"miska.stl", "koule.stl", "sablona.stl", "miska.3mf", "koule.3mf", "sablona.3mf"}.issubset(soubory):
        raise ValueError("Ve vydání chybí tiskové modely Emila.")
    for nazev in sorted(soubory):
        with client.open(url + endpoint(nazev, "tisk-emil"), timeout=45) as odpoved:
            if (odpoved.headers.get_content_type() != "model/" + Path(nazev).suffix[1:]
                    or odpoved.headers.get_filename() != nazev
                    or odpoved.read() != (tisk / nazev).read_bytes()):
                raise ValueError(f"Stažený tiskový model {nazev} neodpovídá vydání.")
    denied("neznamy.stl", 404, "tisk-emil")
    if get("index.php?data=kondo") != (base/"kondo-data.json").read_bytes():
        raise ValueError("Podklady Kondo na webu neodpovídají vydání.")
    catalog_path = base/"tisk/R16/catalog.json"
    if catalog_path.is_file():
        raw = get(endpoint("catalog.json"))
        if raw != catalog_path.read_bytes():
            raise ValueError("Server vrátil rozdílný tiskový katalog.")
        manifest = json.loads(raw)
        over_karty(url, manifest, cookies)
        for name, wanted in manifest["file_checksums"].items():
            if name.endswith(".gcode"):
                continue  # Obsah souboru už ověřilo stažení přímo z karty v prohlížeči.
            payload = get(endpoint(name))
            if hashlib.sha256(payload).hexdigest() != wanted:
                raise ValueError(f"Nesouhlasí SHA-256 souboru {name}")
            if name.endswith(".3mf"):
                with ZipFile(BytesIO(payload)) as archive:
                    if "3D/3dmodel.model" not in archive.namelist():
                        raise ValueError(f"Chybí obsah modelu {name}")
        denied("neplatny-soubor.json",404)
        print(f"Přihlášená aplikace, data Kondo a {len(manifest['file_checksums'])} souborů prošly živou kontrolou.")
    else:
        print("Přihlášená aplikace a data Kondo prošly živou kontrolou.")

if __name__ == "__main__":
    if sys.argv[1:] == ["--mistni"]:
        mistni_kontrola()
    else:
        main()
