"""
Configuración de pytest (fixtures compartidos).

Nota: el entorno de pruebas (DEBUG, DATABASE_URL) se fija en el módulo
`testenv` (paquete editable `devtools/`), registrado como plugin `-p`
en `pytest.ini`, porque en pytest >= 9 los conftest se cargan después de
que pytest-django inicia Django.
"""
