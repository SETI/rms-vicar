=======================
Development Environment
=======================

Getting a Working Checkout
==========================

Clone the repository and run the bootstrap script, which creates a virtual environment
at ``./venv`` and installs the package in editable mode with the ``dev`` extra. The
``dev`` extra includes the ``docs`` extra, so one command installs everything the checks
need. The script is safe to rerun: it reuses an existing environment and upgrades its
packages.

.. code-block:: sh

   git clone https://github.com/SETI/rms-vicar.git
   cd rms-vicar
   ./scripts/setup-venv.sh
   source venv/bin/activate

Pass ``--python`` to choose an interpreter and ``--recreate`` to rebuild the environment
from scratch:

.. code-block:: sh

   ./scripts/setup-venv.sh --python python3.13 --recreate

Never install into the system Python. If you prefer to manage the environment yourself,
the equivalent of the script is:

.. code-block:: sh

   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"

Environment Variables
=====================

The package itself reads no environment variables. The scripts read these:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Meaning
   * - ``VENV`` or ``VENV_PATH``
     - The virtual environment the scripts create or activate. Default: ``./venv``.
   * - ``ENABLE_<CHECK>``
     - Per-check switches read by the check script, such as ``ENABLE_MYPY=true``. The
       defaults define the set of checks the repository has opted into; see
       `Running the Checks`_.
   * - ``CLEANUP_GRACE_PERIOD``
     - Seconds the check script waits for a check to stop after an interrupt before
       killing it. Default: 5.

Smoke Test
==========

The package has no command-line entry points. Confirm that the editable install works by
reading one of the files in ``test_files/`` and printing part of its label:

.. code-block:: sh

   python -c "import vicar; print(vicar.__version__); \
   vic = vicar.VicarImage('test_files/C0532836239R.IMG'); print(vic.array.shape, vic['FORMAT'])"

The version is derived from the git history by ``setuptools_scm`` and written to
``src/vicar/_version.py`` at install time, so a checkout that is not a git repository
reports ``Version unspecified``.

Running the Tests
=================

The suite is pytest throughout. The options in ``pyproject.toml`` apply to every
invocation: tests run in parallel with ``pytest-xdist``, coverage is collected for
``src/vicar``, unregistered markers and misspelled options are errors, and every warning
raised during a test fails it.

.. code-block:: sh

   pytest                                     # the whole suite, in parallel, with coverage
   pytest tests/test_vicarlabel_keys.py       # one file
   pytest -k reorder                          # tests whose names match
   pytest -n 0 tests/test_vicarimage_read.py  # serially, which is easier to debug
   coverage report -m                         # missing lines, after a run

Coverage must stay at or above 90 percent, measured over the whole suite with branch
coverage on; the run fails below that. There are no slow or environment-dependent tiers
and no registered markers, so a bare ``pytest`` runs everything.

Tests must be independent and order-agnostic, because they run in parallel. Use the
fixtures in ``tests/conftest.py`` rather than building the same setup in each file:
``data_dir`` is the ``test_files/`` directory, ``geoma_path`` and ``geoma_label`` are a
tabular file with a binary header and an end-of-file label and the full text of that
label, and ``rng`` is a seeded NumPy random generator. Never write into ``test_files/``;
copy a file into pytest's ``tmp_path`` first and modify the copy.

The check script runs pytest with ``--dist loadscope``, which keeps each test module on
one worker, and ``-w``/``--pytest-workers`` sets the number of workers. Use the same
flags when reproducing a failure that the script reports.

Running the Checks
==================

``scripts/run-all-checks.sh`` is the single source of truth for which checks must pass.
CI runs exactly that set, no more and no less, so passing the script locally means
passing CI. Run it after every change.

.. code-block:: sh

   ./scripts/run-all-checks.sh            # everything, in parallel
   ./scripts/run-all-checks.sh -s         # everything, sequentially, easier to read
   ./scripts/run-all-checks.sh -c         # code checks only
   ./scripts/run-all-checks.sh -d         # Sphinx, codespell, and PyMarkdown only
   ./scripts/run-all-checks.sh --pytest   # one check; combine flags as needed

The checks it enables by default are:

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Check
     - Flag
     - What it enforces
   * - ruff
     - ``--ruff-check``
     - The linter of record, for every rule it implements. The rule set and the
       deliberate exemptions are in ``pyproject.toml``.
   * - flake8
     - ``--flake8-cont``
     - Continuation-line indentation only (codes E12x and E13x), which ruff does not
       implement. The per-file exemptions in ``.flake8`` are authoritative for these
       codes alone.
   * - mypy
     - ``--mypy``
     - Type checking of ``tests/`` only, which are fully annotated, against the type
       stub.
   * - pytest
     - ``--pytest``
     - The test suite and the coverage floor.
   * - pyroma
     - ``--pyroma``
     - Packaging metadata completeness.
   * - stubtest
     - ``--stubtest``
     - The type stub, ``src/vicar/__init__.pyi``, matches the runtime API.
   * - pip-audit
     - ``--pip-audit``
     - No installed dependency has a known vulnerability. The package itself is
       skipped, because it is installed from the checkout rather than from PyPI.
   * - Sphinx
     - ``--sphinx``
     - The documentation builds with warnings as errors and with nitpicky
       cross-reference checking.
   * - codespell
     - ``--codespell``
     - Typos and British spellings in ``src/``, ``tests/``, ``docs/``, ``scripts/``,
       ``README.md``, and ``CONTRIBUTING.md``. The words it is told to accept, each with
       its reason, are in ``[tool.codespell]`` in ``pyproject.toml``.
   * - PyMarkdown
     - ``--pymarkdown``
     - Markdown style for ``docs/``, ``.claude/``, ``README.md``, and ``CONTRIBUTING.md``.

Three more checks are wired in but disabled by default: ``ruff format --check``, bandit,
and vulture. Leave them disabled; ``ruff format`` in particular would remove the column
alignment the code uses deliberately. Never run mypy on ``src/``: the modules there are
deliberately unannotated, so it would report meaningless errors. Run it by hand the way
the check script does:

.. code-block:: sh

   MYPYPATH=src mypy tests

Building the Documentation
==========================

The documentation builds with ``-W``, so any warning is an error, and in nitpicky mode,
so a cross-reference with no target is an error too. The check script and CI pass ``-n``
as well, and ``docs/conf.py`` sets nitpicky mode itself so that the ReadTheDocs build,
which takes no extra options, applies it too.

.. code-block:: sh

   ./scripts/run-all-checks.sh --sphinx   # build only
   ./scripts/read-docs.sh                 # build, then open in a browser

Continuous Integration
======================

Three GitHub Actions workflows live in ``.github/workflows/``.

* ``run-tests.yml`` runs on every pull request against ``main``, on every push to
  ``main``, weekly, and on demand. Its lint job runs ruff, flake8, mypy, pip-audit,
  pyroma, stubtest, Sphinx, codespell, and PyMarkdown on Python 3.13, which is the check
  script's default set minus pytest. Its test job runs pytest with coverage on Ubuntu,
  macOS, and Windows for each of Python 3.11, 3.12, and 3.13, and uploads coverage to
  Codecov from the Ubuntu, Python 3.13 cell of the matrix.
* ``publish_to_pypi.yml`` builds the distribution and uploads it to PyPI when a GitHub
  Release is published.
* ``publish_to_test_pypi.yml`` does the same for Test PyPI, on demand.

Dependabot, configured in ``.github/dependabot.yml``, opens a weekly pull request when
an action used by these workflows has a newer release.

ReadTheDocs builds the documentation from ``.readthedocs.yaml``, installing the package
with the ``docs`` extra on Python 3.12 and failing on any warning.

Releasing
=========

Versions come from git tags through ``setuptools_scm``; never edit
``src/vicar/_version.py`` by hand. To release, tag the commit on ``main`` with the
version, push the tag, and create a GitHub Release from it. Publishing the release
triggers the upload to PyPI. A build from a commit that is not tagged carries a
development version derived from the most recent tag.

Contributing Changes
====================

Work on a branch named ``<initials>_<YYMMDD>_<topic>``, such as ``rf_251125_filecache``.
Commit subjects are plain capitalized imperative sentences with no type prefix and no
trailing period. Every pull request must pass the full check set, and pull requests are
squash-merged onto ``main``, which appends the pull request number to the subject.
:doc:`/contributing` covers reporting bugs and proposing enhancements.
