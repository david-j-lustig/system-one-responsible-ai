# Race perturbation

Toggle `person.race` on decision cases and record TypeSafe Noul, Choice, and Score answers as a CSV.

```bash
uv run python explainability/bias/race/run.py --help
uv run python explainability/bias/race/run.py --all
uv run python explainability/bias/race/run.py --criminal
uv run python explainability/bias/race/run.py --financial
uv run python explainability/bias/race/run.py --all --dry-run
uv run python explainability/bias/race/run.py --criminal --batch-size 10
```

`--help` lists the case sets. Choose `--criminal`, `--financial`, or `--all`. Running with no set flag prints usage and exits.

`--dry-run` uses a fake client (no API key). Live runs need `TYPESAFE_API_KEY` in `.env`.

CSV is written to `explainability/bias/race/results/` (gitignored).
