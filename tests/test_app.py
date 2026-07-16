from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from click.testing import CliRunner

from ethos import app
from ethos.home import initialise_home


def test_init_command_initialises_default_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app, "HOME_PATH", tmp_path / ".ethos")

    result = CliRunner().invoke(app.main, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / ".ethos" / "config.yaml").exists()
    assert (tmp_path / ".ethos" / "data" / "ethos.db").exists()


def test_init_command_reports_existing_home_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".ethos"
    home.mkdir()
    monkeypatch.setattr(app, "HOME_PATH", home)

    result = CliRunner().invoke(app.main, ["init"])

    assert result.exit_code == 1
    assert "Error: ethos home already exists:" in result.output
    assert "Run [ethos init --reinitialise] to replace it." in result.output
    assert "Traceback" not in result.output


def test_uninit_command_removes_home_after_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".ethos"
    home.mkdir()
    (home / "config.yaml").touch()
    monkeypatch.setattr(app, "HOME_PATH", home)

    result = CliRunner().invoke(app.main, ["uninit"], input="y\n")

    assert result.exit_code == 0
    assert not home.exists()
    assert f".ethos removed from: {home}" in result.output


def test_uninit_command_preserves_home_without_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".ethos"
    home.mkdir()
    monkeypatch.setattr(app, "HOME_PATH", home)

    result = CliRunner().invoke(app.main, ["uninit"], input="n\n")

    assert result.exit_code == 0
    assert home.exists()
    assert "Aborted!" in result.output


def test_onboarding_command_configures_openai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = initialise_home(tmp_path / ".ethos")
    monkeypatch.setattr(app, "HOME_PATH", home)

    result = CliRunner().invoke(
        app.main,
        ["onboard"],
        input="openai\ngpt-5-mini\ntest-key\n",
    )

    config = yaml.safe_load((home / "config.yaml").read_text())
    assert result.exit_code == 0
    assert config["provider"]["name"] == "openai"
    assert config["provider"]["model_name"] == "gpt-5-mini"
    assert config["keys"]["openai_api_key"] == "test-key"


def test_onboarding_command_configures_ollama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = initialise_home(tmp_path / ".ethos")
    monkeypatch.setattr(app, "HOME_PATH", home)

    result = CliRunner().invoke(
        app.main,
        ["onboard"],
        input="ollama\nllama3.2\n\n\n",
    )

    config = yaml.safe_load((home / "config.yaml").read_text())
    assert result.exit_code == 0
    assert config["provider"]["name"] == "ollama"
    assert config["provider"]["model_name"] == "llama3.2"
    assert config["provider"]["ollama_base_url"] == (
        "http://localhost:11434/v1"
    )
    assert config["keys"]["ollama_api_key"] is None


def test_ask_command_prints_model_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".ethos"
    home.mkdir()
    monkeypatch.setattr(app, "HOME_PATH", home)
    monkeypatch.setattr(app, "run_prompt", lambda prompt: f"reply: {prompt}")

    result = CliRunner().invoke(app.main, ["ask", "hello"])

    assert result.exit_code == 0
    assert result.output == "reply: hello\n"


def test_ask_command_reports_runtime_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".ethos"
    home.mkdir()
    monkeypatch.setattr(app, "HOME_PATH", home)

    def fail(_prompt: str) -> str:
        raise ValueError("ETHOS_KEYS__OPENAI_API_KEY is required")

    monkeypatch.setattr(app, "run_prompt", fail)

    result = CliRunner().invoke(app.main, ["ask", "hello"])

    assert result.exit_code == 1
    assert result.output == "Error: ETHOS_KEYS__OPENAI_API_KEY is required\n"
    assert "Traceback" not in result.output


def test_ask_command_requires_initialised_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app, "HOME_PATH", tmp_path / ".ethos")

    result = CliRunner().invoke(app.main, ["ask", "hello"])

    assert result.exit_code == 1
    assert result.output == (
        "Error: ethos is not initialised. Run [ethos init] first.\n"
    )
