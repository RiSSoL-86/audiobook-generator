install:
	uv sync --locked

pre-commit.install:
	uv run pre-commit install

lint:
	uv run ruff format src/
	uv run ruff check src/ --fix
	uv run mypy src/

test:
	uv run pytest src/
