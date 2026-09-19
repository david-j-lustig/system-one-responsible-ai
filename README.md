# system-one-responsible-ai

Understanding the biases and limitations of system one models.

Mode first, topic second. Explainability, stress tests, and evals each repeat the same topic tree.

```text
research_docs/
explainability/
stress_tests/
evals/
```

Topics: `bias/` (race, gender, ageism, political, disability, religion, sexuality), `harm/` (violence, self_harm, crime, hate), plus privacy, misinformation, and calibration.

## Setup

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --group dev
cp .env.example .env
```

Set `TYPESAFE_API_KEY` in `.env` ([console.typesafe.ai](https://console.typesafe.ai/settings/keys)).

## License

[MIT](LICENSE)
