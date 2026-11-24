"""Kontrola kompletních úloh a rychlostí přehrávače R16 v prohlížeči Chromium."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("stranka", help="Adresa stránky nebo místní HTML")
parser.add_argument("--chromium", help="Cesta ke spustitelnému Chromiu")
args = parser.parse_args()
url = args.stranka if "://" in args.stranka else Path(args.stranka).resolve().as_uri()

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=args.chromium, args=[
        "--no-sandbox", "--disable-dev-shm-usage", "--use-gl=angle",
        "--use-angle=swiftshader", "--enable-unsafe-swiftshader"
    ])
    page = browser.new_page(viewport={"width": 1180, "height": 840})
    chyby = []
    page.on("pageerror", lambda error: chyby.append(str(error)))
    page.clock.install(time=1_700_000_000_000)
    page.clock.pause_at(1_700_000_002_000)
    page.goto(url, timeout=90000)
    assert page.locator("html").get_attribute("data-ready") == "true", chyby
    assert not page.locator("#error").inner_text(), page.locator("#error").inner_text()

    # Hodiny prohlížeče ovládáme bez zásahu do kódu simulátoru.
    def click(selector):
        page.locator(selector).evaluate("(e) => e.click()")

    def change(selector, value):
        page.locator(selector).evaluate("""(e,v) => {
            e.value=v; e.dispatchEvent(new Event('change',{bubbles:true}));
        }""", str(value))

    def frame():
        return int(page.locator("#slider").input_value())

    def seek(i):
        page.locator("#slider").evaluate("""(e,i) => {
            e.value=i; e.dispatchEvent(new Event('input',{bubbles:true}));
        }""", i)

    plan = json.loads(page.locator("#h22TempoData").text_content())
    for mode in ["walk", "sit", "home", "turn", "pickup", "stairs", "dance", "climb"]:
        click(f'[data-mode="{mode}"]')
        end = int(page.locator("#slider").get_attribute("max"))
        if mode == "home":
            assert end == 0 and page.locator("#play").is_disabled()
            print("Výchozí postoj OK", flush=True)
            continue
        click("#play")
        page.clock.fast_forward(4000)
        mid = frame()
        assert 0 < mid < end, (mode, mid, end)
        click("#play")
        page.clock.fast_forward(1000)
        assert frame() == mid
        click("#play")
        page.clock.fast_forward(200000)
        assert frame() == end and page.locator("#play").inner_text() != "Pauza", (mode,frame(),end)
        click("#play")
        assert frame() == 0
        click("#play")
        print(f"{mode} · pohyb, pauza, dokončení i restart OK", flush=True)

    assert page.locator("#h22Tempo").input_value() == "vybrany"
    for key in [k for k in ["vybrany","rychly_210","cil_10_s","reference"] if k in plan or k == "reference"]:
        interval=1000
        change("#h22Tempo", key)
        for multiplier in [".1", "1", "10"]:
            seek(0)
            change("#speed", multiplier)
            click("#play")
            page.clock.fast_forward(interval)
            clock_s = (interval / 1000) * float(multiplier)
            times = plan[key]["casy_s"] if key in plan else [i/6 for i in range(1141)]
            wanted = max(i for i,t in enumerate(times) if t <= clock_s + 1e-8)
            assert abs(frame()-wanted) <= 1, (key,multiplier,frame(),wanted)
            if page.locator("#play").inner_text() == "Pauza":
                click("#play")
        print(f"{key} · čas odpovídá při 0,1×, 1× i 10×", flush=True)
    change("#h22Tempo", "cil_10_s")
    seek(1100)
    assert "záznam" in page.locator("#h22TrackNote").inner_text().lower()
    def model_picture():
        box = page.locator("#canvas").bounding_box()
        assert box and box["height"] > 0
        return page.screenshot(clip=box, animations="allow")
    simulated = model_picture()
    change("#h22Track","planned")
    assert simulated != model_picture(), "Povelový plán a pád v simulaci musí dát různý obraz."
    change("#h22Track","measured")
    print("Kamera vykresluje rozdíl mezi skutečným záznamem z MuJoCo a povely", flush=True)
    change("#h22Tempo", "vybrany")
    seek(0)
    click("#r11StairFault")
    click("#play")
    page.clock.fast_forward(12000)
    assert frame() == 57 and page.locator("#play").inner_text() != "Pauza"
    click("#r11StairFault")
    click("#play")
    page.clock.fast_forward(12000)
    assert frame() == 1140
    change("#r14Height", 220)
    assert page.locator("#h22Tempo").is_disabled() and "190,0" in page.locator("#time").inner_text()
    change("#r14Height", 210)
    assert not page.locator("#h22Tempo").is_disabled()
    assert not chyby, chyby
    print("Čidlo opory, změna výšky a návrat do ověřené geometrie OK", flush=True)
    browser.close()
