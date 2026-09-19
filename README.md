# system-one-responsible-ai

Understanding the biases and limitations of system one models.


## Setup

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --group dev
cp .env.example .env
```

Set `TYPESAFE_API_KEY` in `.env` ([console.typesafe.ai](https://console.typesafe.ai/settings/keys)). For harm `--mutate`, also set `OPENAI_API_KEY`.

First explainability study: [race perturbation](explainability/bias/race/README.md). First stress test: [harm Noul search](stress_tests/harm/README.md). After setup:

```bash
uv run python explainability/bias/race/run.py --help
uv run python explainability/bias/race/run.py --all
uv run python stress_tests/harm/run.py --help
uv run python stress_tests/harm/run.py --all
uv run python stress_tests/harm/run.py --self-harm --mutate
```

## License

[MIT](LICENSE)
