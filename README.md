# system-one-responsible-ai

Understanding the biases and limitations of system one models.


## Setup

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --group dev
cp .env.example .env
```

Set `TYPESAFE_API_KEY` in `.env` ([console.typesafe.ai](https://console.typesafe.ai/settings/keys)). For harm `--mutate`, also set `OPENAI_API_KEY`.

First explainability studies: [race perturbation](explainability/bias/race/README.md), [gender perturbation](explainability/bias/gender/README.md). First stress test: [harm Noul search](stress_tests/harm/README.md). First evals: [fixed harm cases](evals/README.md). After setup:

```bash
uv run python explainability/bias/race/run.py --help
uv run python explainability/bias/race/run.py --financial --repeats 10
uv run python explainability/bias/race/analyze.py
uv run python explainability/bias/gender/run.py --dry-run
uv run python explainability/bias/gender/run.py
uv run python explainability/bias/gender/analyze.py
uv run python stress_tests/harm/run.py --help
uv run python stress_tests/harm/run.py --all
uv run python stress_tests/harm/run.py --self-harm --mutate
uv run python evals/run.py
uv run python evals/run.py --dry-run
```

## License

[MIT](LICENSE)
