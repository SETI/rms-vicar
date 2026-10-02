# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`rms-vicar` (import name `vicar`) reads and writes JPL VICAR image and label files. Single
package, `src/` layout: `VicarLabel` (`vicarlabel.py`) parses and edits labels via the pyparsing
grammar in `_LABEL_GRAMMAR.py`; `VicarImage` (`vicarimage.py`) wraps a label plus the data array,
prefix bytes, and binary header.

## Detailed rules

`.claude/rules/*.md` hold the authoritative standards (Python style, testing, documentation,
dependencies, environment) and load automatically. The standards for each kind of document
build on `doc_python` and live in `.claude/skills/`, loaded on demand: `doc-readme`,
`doc-user-guide`, `doc-dev-guide`, `doc-how-to`. So do the process standards: `git-workflow`,
`pull-request`, `bug-report`, `run-all-checks`. This file records only what you would
otherwise get wrong.

## Verifying changes

`scripts/run-all-checks.sh` is the single source of truth for the checks that gate a merge;
`.github/workflows/run-tests.yml` runs the same set. Run it after any change.

- It needs a virtualenv at `./venv` (override with `VENV`); create it with
  `./scripts/setup-venv.sh`. Never install into system Python.
- Single checks: `--pytest`, `--ruff-check`, `--flake8-cont`, `--mypy`, `--stubtest`,
  `--pip-audit`, `--sphinx`, `--codespell`, `--pymarkdown`; or `-c` (code) / `-d` (docs) /
  `-m` (text).
- `ruff format`, `bandit`, and `vulture` are disabled. Leave them off; the codebase uses
  column-aligned assignments and imports that the formatter would destroy.
- `codespell` enforces American spelling as well as typos. A word it flags that is correct here
  goes in `ignore-words-list` in `pyproject.toml` with its reason; a one-off goes on its own
  line as `codespell:ignore <word>`.

## Python style

- Ruff is the linter of record: `ruff check src tests`. It implements no `E121`-`E133` rule, so
  `flake8 --select=E12,E13 src tests` covers continuation-line indentation, and the
  `per-file-ignores` in `.flake8` are authoritative for those codes only.
- Line length 90; tests are exempt from E501. Single quotes.
- Rules switched off in `pyproject.toml` carry their reason beside them (`RUF005`, `I001`, and
  the per-file `N999`/`E741` for `_DEFINITIONS.py` and `_LABEL_GRAMMAR.py`). Read the comment
  before re-enabling one. `_DEFINITIONS` and `_LABEL_GRAMMAR` keep their uppercase names because
  code imports them.
- No type annotations under `src/`; types go in the docstrings. **Never run mypy on `src/`** --
  it is unannotated, and the `exclude` and override in `pyproject.toml` keep mypy off its
  modules. mypy runs strict on `tests/`, so every test function and fixture needs annotations,
  including `-> None`.
- The package ships a PEP 561 `py.typed` marker, and **exactly one stub**, `__init__.pyi`, carries
  the public type information. The only supported import is `from vicar import ...`, so no other
  module has a stub and none may be added. A stub replaces its module entirely for type checkers,
  so whatever it omits is invisible downstream. `stubtest` enforces that the stub covers the
  whole public surface and runs in the check script and in CI, so adding, renaming, or
  re-signing any public member means updating `__init__.pyi` in the same change. Types come from
  the docstrings, so the two must agree. A new
  public module goes in `[tool.mypy] exclude`, the override list in `pyproject.toml`, and
  `.stubtest-allowlist`.
- Helpers such as `VicarImage._intfmt` are `@staticmethod`s called through the class; keep new
  ones that way.

## Testing

- pytest throughout: module-level `test_*` functions, no `unittest.TestCase`.
- `addopts` applies `-n auto --cov=src/vicar --strict-markers --strict-config`, so every run is
  parallel. Tests must be order-independent and must never write into `test_files/` -- copy a
  file to `tmp_path` first.
- `tests/conftest.py` provides `data_dir` (the `test_files/` directory), `geoma_path`,
  `geoma_label` (the full text of `C2069302_GEOMA.DAT`'s label), and `rng` (a seeded
  `numpy.random.Generator`). Use `rng` rather than `np.random`.
- `filterwarnings = ["error"]`: any warning fails the test. Use `pytest.warns(..., match=...)`
  when a warning is the behavior under test.
- Coverage is 100%; `fail_under = 90`. Keep new code covered.

## Documentation

Sphinx runs with `-W -n`, and `docs/conf.py` sets `nitpicky = True` so the ReadTheDocs build is
nitpicky too; an unresolved cross-reference fails the build. Napoleon's type preprocessing is
off, because it cannot split a union on `|`; the Python domain parses each type field instead.
`_TYPE_ALIASES` in `docs/conf.py` resolves the short names `np.ndarray`, `Path`, `FCPath`, and
`file` wherever they appear in a type, through a `missing-reference` handler that runs ahead of
intersphinx. Any other third-party name needs its resolvable spelling, such as `numpy.ndarray`
or `collections.abc.Iterator`. Add to `nitpick_ignore_regex` only for informal type words that
name no Python object. Write docstring types in annotation style, with `|` between alternatives,
`list[...]` and `tuple[...]` for containers, and a trailing `, optional` for a parameter with a
default: `filepath (str | Path | FCPath, optional)`.

PyMarkdown scans `docs/`, `.claude/` (recursively), `README.md`, and `CONTRIBUTING.md`, and
codespell scans `src/`, `tests/`, `docs/`, `scripts/`, `README.md`, and `CONTRIBUTING.md`, in both
CI and the check script; keep the two lists in step.

The Developer's Guide lives in `docs/dev_guide/`. Its internal reference documents the whole
package with `:private-members:` under `:no-index:`, so its entries do not compete with the
public reference in `docs/module.rst` for link targets; give a private type that docstrings
name its own `autoclass` entry there, as `_ValueFormat` and `_ListFormat` have.

## Repo etiquette

- Commit subjects: plain capitalized imperative sentence, no type prefix, no trailing period.
  PRs are squash-merged onto `main`, which appends `(#N)`.
- Branch names: `<initials>_<YYMMDD>_<topic>`, e.g. `rf_251125_filecache`.
- Dependencies go in `pyproject.toml` only; `requirements.txt` is just `-e .`. Minimum-version
  constraints, never `==` pins.
- Versions come from `setuptools_scm`; never hand-edit `src/vicar/_version.py`.
