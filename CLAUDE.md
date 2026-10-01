# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`rms-vicar` (import name `vicar`) reads and writes JPL VICAR image and label files. Single
package, `src/` layout: `VicarLabel` (`vicarlabel.py`) parses and edits labels via the pyparsing
grammar in `_LABEL_GRAMMAR.py`; `VicarImage` (`vicarimage.py`) wraps a label plus the data array,
prefix bytes, and binary header.

## Detailed rules

`.claude/rules/*.md` hold the authoritative standards (Python style, testing, documentation,
dependencies, environment) and load automatically; the `doc_*` and `how_to` rules load only when
you touch `README.md` or `docs/`. Process standards live in `.claude/skills/` (`git-workflow`,
`pull-request`, `bug-report`, `run-all-checks`, ...). This file records only what you would
otherwise get wrong.

## Verifying changes

`scripts/run-all-checks.sh` is the single source of truth for the checks that gate a merge;
`.github/workflows/run-tests.yml` runs the same set. Run it after any change.

- It needs a virtualenv at `./venv` (override with `VENV`); create it with
  `./scripts/setup-venv.sh`. Never install into system Python.
- Single checks: `--pytest`, `--ruff-check`, `--flake8-cont`, `--mypy`, `--sphinx`,
  `--pymarkdown`; or `-c` (code) / `-d` (docs).
- `ruff format`, `bandit`, and `vulture` are disabled. Leave them off; the codebase uses
  column-aligned assignments and imports that the formatter would destroy.

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
  it is unannotated, and `pyproject.toml` keeps mypy off the `vicar` package. mypy runs strict on
  `tests/`, so every test function and fixture needs annotations, including `-> None`.
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

Sphinx runs with `-W` and `nitpicky = True`, so an unresolved cross-reference fails the build.
Napoleon's `napoleon_type_aliases` in `docs/conf.py` resolve short names (`np.ndarray`, `Path`,
`FCPath`, `file`, `iterator`) in **parameter** types only. In `Returns:` blocks write the
resolvable spelling: `numpy.ndarray`, `collections.abc.Iterator`,
`filecache.file_cache_path.FCPath`. Add to `nitpick_ignore_regex` only for informal type words
that name no Python object. Write union types as `(str, Path, or FCPath)`, not `str | Path`.

PyMarkdown scans `docs/`, `.claude/`, `README.md`, and `CONTRIBUTING.md` in both CI and the
check script; keep the two lists in step.

`docs-dev/` is a second Sphinx tree that also documents private members; it is not built in CI.

## Repo etiquette

- Commit subjects: plain capitalized imperative sentence, no type prefix, no trailing period.
  PRs are squash-merged onto `main`, which appends `(#N)`.
- Branch names: `<initials>_<YYMMDD>_<topic>`, e.g. `rf_251125_filecache`.
- Dependencies go in `pyproject.toml` only; `requirements.txt` is just `-e .`. Minimum-version
  constraints, never `==` pins.
- Versions come from `setuptools_scm`; never hand-edit `src/vicar/_version.py`.
