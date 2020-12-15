pybabel extract . -o locales/testbot.pot
pybabel init -i locales/testbot.pot -d locales -D testbot -l en
pybabel init -i locales/testbot.pot -d locales -D testbot -l ru
pybabel init -i locales/testbot.pot -d locales -D testbot -l uk
pybabel compile -d locales -D testbot