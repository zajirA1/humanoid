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
echo "Kontrola prošla"
