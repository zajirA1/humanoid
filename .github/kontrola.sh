#!/usr/bin/env bash
# Kontrola před commitem i v GitHubu: žádná hesla v repozitáři, PHP bez chyb, výpočet sil sedí s referencí.
set -euo pipefail
cd "$(dirname "$0")/.."
if git ls-files | grep -E '(^|/)(tajne\.php|pokusy\.json|\.env)$|soukrome/relace/'; then echo "V repozitáři je soubor s heslem nebo daty ze serveru"; exit 1; fi
php -l web/index.php
grep -q 'Require all denied' web/app/.htaccess
grep -q 'Require all denied' web/soukrome/.htaccess
grep -q 'Disallow: /' web/robots.txt
test -s web/app/emil-h22.html
(cd testy && node t_engine.js)
python3 -I -m py_compile kontrola/prepocet.py kontrola/doladeni.py .github/over_upravu.py zdroj/uprava-kloubu/revize.py zdroj/revize/nova_revize.py zdroj/r15/stranka_r15.py zdroj/r15/dynamika.py zdroj/uprava-kloubu/audit_upravy.py zdroj/uprava-kloubu/build_r14.py
cmp -s kontrola/r14engine.js zdroj/uprava-kloubu/r14engine.js || { echo "kontrola/r14engine.js se liší od zdroj/uprava-kloubu/r14engine.js"; exit 1; }
echo "Kontrola prošla"
