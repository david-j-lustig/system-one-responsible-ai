# system-one-responsible-ai

Understanding the biases and limitations of system one models.


## Setup

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --group dev
cp .env.example .env
```

Set `TYPESAFE_API_KEY` in `.env` ([console.typesafe.ai](https://console.typesafe.ai/settings/keys)).

First explainability study: [race perturbation](explainability/bias/race/README.md). After setup:

```bash
uv run python explainability/bias/race/run.py --help
uv run python explainability/bias/race/run.py --all
```

## License

[MIT](LICENSE)
