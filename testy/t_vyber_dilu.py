"""Prohlížeč součástí R16. Vstupem je adresa spuštěného soukromého náhledu nebo offline HTML s katalogem."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright


def otisk(download):
    return hashlib.sha256(Path(download.path()).read_bytes()).hexdigest()


def over(url, chromium, test_offline):
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as temp:
        browser = pw.chromium.launch(executable_path=chromium, args=[
            '--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle',
            '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
        ])
        page = browser.new_page(viewport={'width': 1100, 'height': 800}, accept_downloads=True)
        chyby = []
        page.on('pageerror', lambda error: chyby.append(str(error)))
        page.goto(url, timeout=90000)
        page.wait_for_selector('html[data-ready="true"]', state='attached', timeout=90000)
        page.locator('[data-mode="home"]').click()
        page.locator('[data-look="front"]').click()
        canvas = page.locator('#canvas')
        canvas.scroll_into_view_if_needed()
        b = canvas.bounding_box()
        # Čelní pohled na základní sestavu; měřítko závisí na výšce kreslicí plochy.
        x = b['x'] + b['width']/2 - b['height']*.116
        y = b['y'] + b['height']*.25
        page.mouse.move(x,y)
        page.mouse.down()
        page.mouse.move(x+30,y+17,steps=4)
        page.mouse.up()
        dialog = page.locator('#r16PartDialog')
        assert not dialog.is_visible(), 'Tažení má otáčet celým modelem.'
        page.locator('[data-look="front"]').click()
        canvas.scroll_into_view_if_needed()
        b = canvas.bounding_box()
        page.mouse.click(b['x']+b['width']/2-b['height']*.116, b['y']+b['height']*.25)
        dialog.wait_for()
        page.get_by_role('heading', name='Rám trupu').wait_for()
        assert 'r12_trup_ram' in page.locator('#r16PartFacts').inner_text()
        detail = page.locator('#r16PartCanvas')
        pred = detail.screenshot()
        detail.press('ArrowRight')
        assert pred != detail.screenshot(), 'Detail musí reagovat na otočení.'
        page.locator('#r16PartFilter').select_option('print')
        assert page.locator('#r16PartList option').count() == 54
        with page.expect_download() as event:
            page.get_by_role('link', name='Stáhnout díl · 3MF', exact=True).click()
        expected = otisk(event.value)
        page.locator('#r16PartClose').click()
        page.locator('#r8Assembly').select_option('original')
        assert page.locator('#r16PartCatalog').is_disabled()
        page.locator('#r8Assembly').select_option('r9')
        assert page.locator('#r16PartCatalog').is_enabled()
        if test_offline:
            with page.expect_download(timeout=120000) as event:
                page.locator('#save').click()
            file = Path(temp)/'model.html'
            event.value.save_as(file)
            context = browser.new_context(offline=True,accept_downloads=True)
            offline = context.new_page()
            offline.on('pageerror', lambda error: chyby.append(str(error)))
            offline.goto(file.as_uri())
            offline.locator('#r16PartCatalog').click()
            offline.locator('#r16PartList').select_option('ram-22')
            with offline.expect_download() as event:
                offline.get_by_role('link', name='Stáhnout díl · 3MF', exact=True).click()
            assert otisk(event.value) == expected, 'Offline export se liší od katalogového dílu.'
            bundle = json.loads(offline.locator('#r16PartBundle').text_content())
            assert bundle['catalog']['file_checksums']['parts/ram-22.3mf'] == expected
            offline.locator('#r16PartClose').click()
            with offline.expect_download(timeout=120000) as event:
                offline.locator('#save').click()
            again = Path(event.value.path()).read_text()
            assert again.count('<script type="application/json" id="r16PartBundle">') == 1
        assert not chyby, chyby
        browser.close()
        print('Výběr povrchu, otáčení, katalog a soubor správné revize ověřeny.')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stranka')
    cli.add_argument('--chromium')
    cli.add_argument('--offline',action='store_true',help='Uloží, znovu otevře a opět uloží celý model bez sítě.')
    args = cli.parse_args()
    address = args.stranka if '://' in args.stranka else Path(args.stranka).resolve().as_uri()
    over(address,args.chromium,args.offline)
