# Themes

Styles load in this order:
1. `assets/theme-defaults.css`: the dark or light theme (`templates/themes/`).
2. `assets/theme.css`: generated from the profile (accent, background, fonts, heading weight).
3. `assets/base.css`: the page system and components. Uses variables only.
4. `assets/ui.css`: concept screens, coloured by `--c-*` variables.
5. The `<style>` block in `proposal.html`: per-proposal tweaks.

Main variables: `--accent --accent-2 --hl --on-accent --bg --bg-2 --card --text --body --muted --line --head --sans --head-weight --head-track`.

Concept screens (the client's future site): `--c-bg --c-sand --c-line --c-primary --c-deep --c-accent --c-ink --c-soft --c-head --c-sans`.
Set them to the client's colours when known; leave the neutral defaults when the brand is not decided.
