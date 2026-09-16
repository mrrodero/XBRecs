"""
Plugin de pytest (se registra con `-p testenv` en `xrecommender/pytest.ini`).

Fija las variables de entorno de desarrollo ANTES de que pytest-django
inicie Django. En pytest >= 9 los conftest.py se cargan después del hook
`pytest_load_initial_conftests`, por lo que un conftest no puede fijar
el entorno a tiempo; un plugin `-p` sí, porque se importa antes.

Este módulo se instala como paquete editable en el entorno de desarrollo
(`make install-dev` o `pip install -e devtools`), de modo que es importable
independientemente de cómo se invoque pytest (`pytest`, `python -m pytest`,
etc.): con el script de consola el directorio de trabajo no está en
`sys.path`, pero `site-packages` sí.
"""

import os

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault(
    "DATABASE_URL", "postgres://postgres@localhost:5432/xrecommender_dev"
)
