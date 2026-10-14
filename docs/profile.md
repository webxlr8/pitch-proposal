# Company profile

The profile describes the company that **sends** the proposal. It is a folder:

```
pitch-profile/          (or any folder passed with --profile / PITCH_PROFILE)
├── company.yaml        name, website, tagline, one_liner, contact, brand (logo files, accent, fonts)
├── proof.yaml          approved public claims only: stats, clients, how_we_work
├── theme.json          optional: "mode" (dark/light), CSS "vars", Google "fonts" URLs
└── brand/              logo files (logo for light pages, logo_on_dark for dark pages)
```

Create it from your website, then review:
```bash
python3 skills/pitch-proposal/scripts/profile_from_site.py https://your-company.com --out pitch-profile --theme dark
```
`report.md` lists what was found (accent and why, fonts, logos, emails, phones). If only a dark logo exists, a white version is generated for dark pages.

The format matches [pitch-audit](https://github.com/webxlr8/pitch-audit), so one profile serves both skills.
Examples: [`examples/profiles/webxlr8`](../examples/profiles/webxlr8) (dark) and [`examples/profiles/northwind`](../examples/profiles/northwind) (light, fictional).

## Several senders
Keep one folder per company (`profiles/webxlr8`, `profiles/partner-co`) and pass `--profile` per proposal.
