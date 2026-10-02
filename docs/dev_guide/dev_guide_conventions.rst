==================
Coding Conventions
==================

The authoritative rules live in the repository, in ``CLAUDE.md`` and under
``.claude/rules/``. Those files are written to guide AI-assisted development, but they
apply to every contributor, and the checks enforce most of them. This chapter summarizes
the rules a developer is most likely to trip over.

Python Style
============

* Ruff is the linter of record for every rule it implements, with the rule set in
  ``pyproject.toml``. Each disabled rule has its reason beside it; read the reason before
  re-enabling one. Do not disable the ``A`` (builtins) or ``N`` (naming) categories.
* Ruff has no rule for continuation-line indentation, so flake8 checks codes E12x and
  E13x, reading the per-file exemptions in ``.flake8``.
* The maximum line length is 90 characters. Test files are exempt.
* Use single quotes.
* The code base aligns assignments, imports, and table entries in columns on purpose,
  and the whitespace rules that would object are switched off. Do not reformat that
  alignment away, and match the style of the surrounding file.
* At most five positional parameters; the rest are keyword-only after ``*``.
* No unicode smart quotes, em-dashes, or arrows inside ``.py`` files.
* Helpers that need no instance, such as ``VicarImage._intfmt``, are static methods
  called through the class. Keep new ones that way.
* Make the minimal change the task requires.

Type Information
================

The source under ``src/`` carries no type annotations; parameter and return types go in
the docstrings. The public type information lives in one stub, ``src/vicar/__init__.pyi``,
because the only supported import is ``from vicar import ...``. Do not add a stub for any
other module: it would make an import such as ``from vicar.vicarlabel import ...`` look
supported. stubtest checks that the stub declares every public name with the right
signature, so a change to the public API updates the stub in the same change.

The types in the stub come from the docstrings, so the two must agree. The tests are the
only annotated code mypy checks, and they are checked against the stub, so a test that
uses the API in a way the stub does not allow fails mypy.

Docstrings
==========

Every module, class, function, and method has a docstring in Google style, using
``Parameters:`` rather than ``Args:``, with ``Returns:`` and ``Raises:`` where they apply,
wrapped to 90 characters. A docstring must be detailed enough that a black-box test can
be written from it alone. It describes observable behavior only, never change history,
backward compatibility, or an issue number.

Types are written in annotation style: ``|`` between alternatives, ``list[...]`` and
``tuple[...]`` for containers, and a trailing ``, optional`` for a parameter with a
default, as in ``filepath (str | Path | FCPath, optional)``. The short names
``np.ndarray``, ``Path``, ``FCPath``, and ``file`` link to their documentation through a
handler in ``docs/conf.py``; any other third-party type needs the full name its
documentation exports, such as ``numpy.ndarray``.

Tests
=====

* The suite is pytest throughout: module-level ``test_*`` functions, plain ``assert``,
  fixtures, ``pytest.raises`` with ``match=``, and ``pytest.mark.parametrize``. No
  ``unittest.TestCase``.
* Every test function and fixture is annotated, including ``-> None``.
* Each test is independent and passes alone and in any order under parallel execution.
  Use the ``rng`` fixture for random values and ``tmp_path`` for any file a test
  writes; never write into ``test_files/``.
* One behavior per test function where practical, so a failure names what broke. One
  condition per ``assert``, on an exact expected value; ``pytest.approx`` for floats.
* Any warning raised during a test fails it. Use ``pytest.warns`` with ``match=`` when a
  warning is the behavior under test.
* Register any custom marker in ``pyproject.toml`` before using it.
* Coverage stays at or above 90 percent over the whole suite.

Documentation
=============

* Narrative documentation is reStructuredText under ``docs/``; Markdown is only for the
  files that must also render on GitHub.
* Builds are warning-as-error and nitpicky everywhere. Every public API symbol named in
  prose uses a Sphinx role. Private names, which have no reference entry to link to, are
  written as inline literals; otherwise an inline literal is reserved for file paths,
  label parameters, and shell tokens.
* Never add a nitpick exemption for a symbol this project owns.
* American spelling, one space after a sentence-ending period, and no time-anchored
  words such as "legacy" or "now".
* Any code change updates the affected docstrings, guide chapters, and README in the
  same change.

Repository Etiquette
====================

* Branch names follow ``<initials>_<YYMMDD>_<topic>``.
* Commit subjects are plain capitalized imperative sentences with no type prefix and no
  trailing period. Pull requests are squash-merged, which appends the pull request
  number.
* Dependencies go in ``pyproject.toml`` only, with minimum version constraints and never
  exact pins. ``requirements.txt`` contains just ``-e .``.
* Never commit ``build/``, ``.coverage``, ``.pytest_cache/``, ``htmlcov/``, or
  ``src/rms_vicar.egg-info/``, and never hand-edit ``src/vicar/_version.py``.
