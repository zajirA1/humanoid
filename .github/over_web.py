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
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request
from zipfile import ZipFile
from io import BytesIO


class Formular(HTMLParser):
    csrf = None

    def handle_starttag(self, tag, atts):
        data = dict(atts)
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
            print(ident, value, "· ověřeno na kartě", flush=True)
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

    def endpoint(name):
        return "index.php?" + urlencode({"data": "tisk-r16", "file": name})

    def denied(name, code):
        try:
            get(endpoint(name))
        except HTTPError as err:
            if err.code == code:
                return
            raise
        raise ValueError(f"Neočekávané zpřístupnění souboru {name}")

    base = Path("web/app")
    form = Formular()
    form.feed(get("").decode())
    if not form.csrf:
        raise ValueError("Přihlášení neobsahuje token formuláře.")
    denied("catalog.json", 403)
    app = get("", {"csrf":form.csrf, "heslo":os.environ["ROBOT_HESLO"]})
    # Server vkládá dva hlavičkové prvky s údaji aktuální relace.
    app = re.sub(br'<meta name="robot-(?:csrf|api)" content="[^"]*">', b'',app)
    if app != (base/"emil-h22.html").read_bytes():
        raise ValueError("Přihlášený web nevydal aktuální aplikaci.")
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
