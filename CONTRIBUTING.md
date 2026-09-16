# Guía de contribución

Este repositorio sigue el modelo de ramas **Git Flow**
([nvie.com](https://nvie.com/posts/a-successful-git-branching-model/)).
Esta guía describe las ramas, el ciclo de vida de una feature y de una
release, y las convenciones de commits.

## Ramas

| Rama | Origen | Destino | Contenido |
|---|---|---|---|
| `main` | — | — | **Producción.** Solo recibe merges de `release/*` y `hotfix/*`. Cada release se marca con una tag `vX.Y.Z`. |
| `develop` | — | — | **Integración.** Todas las features se integran aquí. Siempre debe ser estable y pasar CI. |
| `feature/<nombre>` | `develop` | `develop` | Trabajo de una feature concreta. |
| `release/<versión>` | `develop` | `main` + `develop` | Candidata a release: solo estabilización, sin features nuevas. |
| `hotfix/<versión>` | `main` | `main` + `develop` | Corrección urgente sobre producción. |

Convenciones de nombres: `feature/paginacion-buscador`,
`release/2.1.0`, `hotfix/2.0.1`.

## Ciclo de una feature

```bash
# 1. Crear la rama desde develop
git checkout develop
git pull origin develop
git checkout -b feature/mi-cambio

# 2. Trabajar, probar y limpiar
make test      # pytest
make lint      # ruff

# 3. Integrar en develop (pull request en GitHub)
git checkout develop
git merge --no-ff feature/mi-cambio
git branch -d feature/mi-cambio
```

Reglas:

- No se pusha directamente a `develop` ni a `main`: siempre por pull
  request con CI en verde (ruff + pytest).
- Una feature se considera lista cuando `make test` y `make lint` pasan.
- Los commits usan imperativo ("Añadir …", "Corregir …", "Eliminar …").

## Ciclo de una release

Cuando `develop` acumula cambios que se quieren publicar:

```bash
# 1. Rama candidata desde develop
git checkout develop
git checkout -b release/2.1.0

# 2. Solo estabilización: bugs, docs, CHANGELOG.md
#    (sin features nuevas; si aparece una, se vuelve a develop)

# 3. Integrar en main y marcar la versión
git checkout main
git merge --no-ff release/2.1.0
git tag -a v2.1.0 -m "Release v2.1.0"

# 4. Devolver los cambios de estabilización a develop
git checkout develop
git merge --no-ff release/2.1.0

# 5. Limpiar
git branch -d release/2.1.0
```

Antes de cerrar el paso 3:

- Actualizar `CHANGELOG.md` con la versión y la fecha.
- Confirmar que CI pasó sobre la rama de release.
- Publicar la tag y (opcionalmente) un GitHub Release con el changelog.

## Ciclo de un hotfix

Para un bug urgente en producción:

```bash
git checkout main
git checkout -b hotfix/2.0.1
# ... corrección mínima + test ...
git checkout main
git merge --no-ff hotfix/2.0.1
git tag -a v2.0.1 -m "Hotfix v2.0.1"
git checkout develop
git merge --no-ff hotfix/2.0.1
git branch -d hotfix/2.0.1
```

## Versionado

Versionado semántico (`MAJOR.MINOR.PATCH`):

- **MAJOR**: cambios incompatibles (p. ej. la modernización 2.0.0).
- **MINOR**: features nuevas compatibles.
- **PATCH**: correcciones.

El historial completo de versiones está en [`CHANGELOG.md`](CHANGELOG.md).

## Protección de ramas (GitHub)

Recomendado configurar en *Settings → Branches*:

- `main`: no aceptar push directo; exigir pull request desde
  `release/*` o `hotfix/*`; exigir CI en verde.
- `develop`: no aceptar push directo; exigir pull request desde
  `feature/*`; exigir CI en verde.

## Herramienta opcional

Los pasos anteriores son comandos `git` estándar. Si se prefiere una
herramienta que los automatice, [gitflow-avh](https://github.com/Abhijit-Varma/gitflow-avh)
ofrece `git flow feature|release|hotfix start|finish`; no es una
dependencia del proyecto y no se instala en el entorno de desarrollo.
