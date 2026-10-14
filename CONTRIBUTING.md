# Contributing

Issues and pull requests are welcome.

- **New page type:** add `templates/pages/<name>.html` (one `<section class="page">`, comment header with purpose and image slots), list it in `references/page-types.md`, and add it to a preset if it belongs there.
- **New concept widget:** add it to `templates/ui.css` using only `--c-*` variables.
- **New check:** add it to `scripts/build.py` with a unit test in `tests/`.
- Keep scripts dependency-light: standard library, Pillow, PyYAML, pypdfium2.
- Run `python -m unittest discover tests` and `python examples/run_examples.py` before opening a PR.
- Never commit real client data, profiles you don't own, or paid stock photos.
