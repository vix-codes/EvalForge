from __future__ import annotations

import json
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import typer
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


app = typer.Typer(
    name="evalforge",
    help="EvalForge CLI for generating and running local model evaluations.",
    no_args_is_help=True,
    invoke_without_command=False,
)
console = Console()
OUTPUT_ENCODING = (getattr(sys.stdout, "encoding", None) or "").lower()
ASCII_ONLY = (os.name == "nt" and os.getenv("EVALFORGE_UNICODE") != "1") or "utf" not in OUTPUT_ENCODING
PANEL_BOX = box.ASCII if ASCII_ONLY else box.ROUNDED
TABLE_BOX = box.ASCII if ASCII_ONLY else box.SIMPLE_HEAVY
SPINNER_NAME = "line" if ASCII_ONLY else "dots"
TRUNCATION_MARK = "..." if ASCII_ONLY else "\u2026"

DEFAULT_API_URLS = (
    "http://localhost:8765/api/v1",
    "http://localhost:8000/api/v1",
)
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "phi4"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "canceled"}
REQUIRED_HEALTH_SERVICES = ("database", "redis")


class CliError(RuntimeError):
    """User-facing CLI failure."""


@dataclass(frozen=True)
class GeneratedQuestion:
    question: str
    golden_answer: str
    keywords: list[str]


@dataclass(frozen=True)
class CliConfig:
    intent_file: Path
    api_url: str | None
    ollama_model: str
    ollama_base_url: str
    gemini_model: str
    poll_interval: float
    pull_model: bool


@app.callback()
def main() -> None:
    """EvalForge CLI."""


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_intent_file(intent_file: Path) -> str:
    if not intent_file.exists():
        raise CliError(f"Intent file not found: {intent_file}")
    if not intent_file.is_file():
        raise CliError(f"Intent path is not a file: {intent_file}")

    intent = intent_file.read_text(encoding="utf-8").strip()
    if not intent:
        raise CliError("Intent file is empty.")
    return intent


def api_candidates(explicit_url: str | None) -> list[str]:
    if explicit_url:
        return [explicit_url.rstrip("/")]

    env_url = os.getenv("EVALFORGE_API_URL")
    candidates = [env_url.rstrip("/")] if env_url else []
    candidates.extend(DEFAULT_API_URLS)
    return list(dict.fromkeys(candidates))


def discover_api_url(explicit_url: str | None) -> str:
    failures: list[str] = []

    for candidate in api_candidates(explicit_url):
        try:
            with httpx.Client(base_url=candidate, timeout=5.0) as client:
                health = fetch_health(client)
                validate_health(health)
            return candidate
        except Exception as exc:
            failures.append(f"{candidate} ({exc})")

    joined = "\n  - ".join(failures)
    raise CliError(
        "EvalForge API is not ready. Tried:\n"
        f"  - {joined}\n"
        "Start the stack with `docker compose up -d postgres redis api worker` "
        "and run migrations if needed."
    )


def fetch_health(client: httpx.Client) -> dict[str, Any]:
    response = client.get("/health")
    response.raise_for_status()
    return response.json()


def validate_health(health: dict[str, Any]) -> None:
    services = health.get("services") or {}
    unhealthy = [
        f"{service}={services.get(service, 'missing')}"
        for service in REQUIRED_HEALTH_SERVICES
        if services.get(service) != "ok"
    ]
    if unhealthy:
        raise CliError(f"health check degraded: {', '.join(unhealthy)}")


def gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise CliError("Set GEMINI_API_KEY or GOOGLE_API_KEY before running auto-test.")
    return api_key


def ensure_ollama_model(base_url: str, model_name: str, pull_model: bool) -> None:
    base_url = base_url.rstrip("/")
    try:
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            response = client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
    except httpx.HTTPError as exc:
        raise CliError(f"Ollama is not reachable at {base_url}: {exc}") from exc

    installed = {item.get("name") for item in models}
    installed.update((item.get("name") or "").split(":")[0] for item in models)
    if model_name in installed:
        return

    if not pull_model:
        raise CliError(
            f"Ollama model `{model_name}` is not installed. Run `ollama pull {model_name}`."
        )

    console.print(f"[bold cyan]Ollama model `{model_name}` missing; pulling it now...[/bold cyan]")
    pull_ollama_model(base_url, model_name)


def pull_ollama_model(base_url: str, model_name: str) -> None:
    progress = Progress(
        SpinnerColumn(SPINNER_NAME, style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
    task_id = progress.add_task(f"Pulling {model_name} from Ollama...", total=None)

    try:
        with Live(progress, console=console, refresh_per_second=8):
            with httpx.Client(base_url=base_url, timeout=1800.0) as client:
                response = client.post("/api/pull", json={"name": model_name, "stream": False})
                response.raise_for_status()
                progress.update(task_id, description=f"Ollama model {model_name} ready")
    except httpx.HTTPError as exc:
        raise CliError(
            f"Could not pull `{model_name}` from Ollama. Try manually: `ollama pull {model_name}`. {exc}"
        ) from exc


def load_gemini_sdk() -> Any:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as genai
    except ImportError as exc:
        raise CliError(
            "Install Gemini CLI dependency first: "
            "`python -m pip install google-generativeai`"
        ) from exc
    return genai


def extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise CliError("Gemini did not return a JSON array.")
        parsed = json.loads(match.group(0))

    if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        parsed = parsed["questions"]
    if not isinstance(parsed, list):
        raise CliError("Gemini response must be a JSON array.")
    return parsed


def normalize_generated_questions(raw_items: list[dict[str, Any]]) -> list[GeneratedQuestion]:
    if not 3 <= len(raw_items) <= 5:
        raise CliError("Gemini must generate between 3 and 5 questions.")

    questions: list[GeneratedQuestion] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise CliError(f"Generated question #{index} is not an object.")

        question = str(item.get("question", "")).strip()
        golden_answer = str(item.get("golden_answer", "")).strip()
        keywords = item.get("keywords") or item.get("expected_keywords") or []

        if isinstance(keywords, str):
            keywords = [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]
        if not isinstance(keywords, list):
            raise CliError(f"Generated question #{index} has invalid keywords.")

        cleaned_keywords = [str(keyword).strip().lower() for keyword in keywords if str(keyword).strip()]
        if not question or not golden_answer or len(cleaned_keywords) != 4:
            raise CliError(
                f"Generated question #{index} must include question, golden_answer, and exactly 4 keywords."
            )

        questions.append(
            GeneratedQuestion(
                question=question,
                golden_answer=golden_answer,
                keywords=cleaned_keywords,
            )
        )

    return questions


def generate_eval_questions(intent: str, gemini_model: str) -> list[GeneratedQuestion]:
    genai = load_gemini_sdk()
    genai.configure(api_key=gemini_api_key())
    model = genai.GenerativeModel(gemini_model)
    prompt = f"""
You are EvalForge's dataset generator. Use exactly one response and return only valid JSON.

Given this Gen AI model purpose:
\"\"\"
{intent}
\"\"\"

Create a JSON array of 3 to 5 evaluation objects. Each object must have:
- "question": a highly specific, realistic task prompt tailored to the purpose.
- "golden_answer": a concise but complete expected answer with facts, constraints, and reasoning.
- "keywords": exactly 4 lowercase strings that should appear in a strong answer.

Prefer hard, domain-specific questions over generic prompts.
Do not include markdown, comments, explanations, or extra keys.
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:
        raise CliError(
            f"Gemini dataset generation failed with model `{gemini_model}`. "
            "Set GEMINI_MODEL in .env or pass `--gemini-model <model>` if your key supports a different model. "
            f"Original error: {exc}"
        ) from exc
    return normalize_generated_questions(extract_json_array(response.text or ""))


def create_suite(client: httpx.Client, intent: str, intent_file: Path) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    response = client.post(
        "/suites",
        json={
            "name": f"Auto Test - {intent_file.stem} - {timestamp}",
            "description": intent,
            "version": "1.0.0",
            "tags": "auto-test,ollama,gemini-generated",
        },
    )
    response.raise_for_status()
    return response.json()


def bulk_ingest_questions(
    client: httpx.Client,
    suite_id: str,
    generated_questions: list[GeneratedQuestion],
) -> list[dict[str, Any]]:
    questions = [
        {
            "question": item.question,
            "golden_answer": item.golden_answer,
            "category": "auto-generated",
            "difficulty": "hard",
            "expected_keywords": ", ".join(item.keywords),
            "max_latency_ms": 120000,
            "weight": 1.0,
            "order_index": index,
        }
        for index, item in enumerate(generated_questions)
    ]
    response = client.post(f"/suites/{suite_id}/questions/bulk", json={"questions": questions})
    response.raise_for_status()
    return response.json()


def trigger_run(client: httpx.Client, suite_id: str, ollama_model: str) -> dict[str, Any]:
    response = client.post(
        "/evals",
        json={
            "suite_id": suite_id,
            "model_name": ollama_model,
            "model_provider": "ollama",
            "trigger": "cli:auto-test",
        },
    )
    response.raise_for_status()
    return response.json()


def poll_run(client: httpx.Client, run_id: str, poll_interval: float) -> dict[str, Any]:
    progress = Progress(
        SpinnerColumn(SPINNER_NAME, style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
    task_id = progress.add_task("Celery evaluation running...", total=None)

    with Live(progress, console=console, refresh_per_second=8):
        while True:
            response = client.get(f"/evals/{run_id}")
            response.raise_for_status()
            run = response.json()
            status = str(run.get("status", "unknown"))
            total = run.get("total_questions") or "?"
            passed = run.get("passed_count") or 0
            failed = run.get("failed_count") or 0
            progress.update(
                task_id,
                description=(
                    f"Celery evaluation {status} "
                    f"[questions={total} pass={passed} fail={failed}]"
                ),
            )
            if status.lower() in TERMINAL_STATUSES:
                return run
            time.sleep(poll_interval)


def fetch_result_details(client: httpx.Client, run_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/evals/{run_id}/results", params={"page_size": 200})
    response.raise_for_status()
    summaries = response.json().get("items", [])

    details: list[dict[str, Any]] = []
    for summary in summaries:
        result_id = summary["id"]
        detail_response = client.get(f"/evals/{run_id}/results/{result_id}")
        detail_response.raise_for_status()
        details.append(detail_response.json())
    return details


def pct(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def score(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.3f}"


def latency(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.0f} ms"


def snippet(value: str | None, limit: int = 180) -> str:
    if not value:
        return "[dim]No response[/dim]"
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - len(TRUNCATION_MARK)].rstrip() + TRUNCATION_MARK


def status_cell(result: dict[str, Any]) -> Text:
    if result.get("is_hallucination"):
        return Text("Hallucinated", style="bold red")
    if result.get("passed"):
        return Text("Pass", style="bold green")
    return Text("Fail", style="bold yellow")


def render_report(
    intent: str,
    run: dict[str, Any],
    results: list[dict[str, Any]],
    ollama_model: str,
) -> None:
    console.rule("[bold cyan]EvalForge Auto-Test Report")
    console.print(
        Panel(
            intent,
            title="[bold]Gen AI Purpose[/bold]",
            subtitle=f"Ollama model: [bold]{ollama_model}[/bold]",
            border_style="cyan",
            box=PANEL_BOX,
        )
    )
    console.print(metrics_grid(run, len(results)))
    console.print(results_table(results))
    console.print(insights_panel(run))


def metrics_grid(run: dict[str, Any], result_count: int) -> Table:
    metrics = Table.grid(expand=True)
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")
    metrics.add_row(
        Panel(str(run.get("total_questions", result_count)), title="Total Questions", border_style="blue"),
        Panel(pct(run.get("hallucination_rate")), title="Hallucination Rate", border_style="red"),
        Panel(pct(run.get("pass_rate")), title="Pass Rate", border_style="green"),
        Panel(latency(run.get("avg_latency_ms")), title="Average Latency", border_style="magenta"),
    )
    return metrics


def results_table(results: list[dict[str, Any]]) -> Table:
    table = Table(
        title="Detailed Results",
        box=TABLE_BOX,
        expand=True,
        show_lines=True,
        header_style="bold white",
    )
    table.add_column("Question", ratio=3, overflow="fold")
    table.add_column("Expected Keywords", ratio=2, overflow="fold")
    table.add_column("Ollama Answer Snippet", ratio=4, overflow="fold")
    table.add_column("Similarity", justify="right", no_wrap=True)
    table.add_column("Keyword", justify="right", no_wrap=True)
    table.add_column("Gemini Judge", justify="right", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)

    for result in results:
        question = result.get("question") or {}
        table.add_row(
            question.get("question") or f"Question ID: {result.get('question_id', 'unknown')}",
            question.get("expected_keywords") or "N/A",
            snippet(result.get("model_response") or result.get("error")),
            score(result.get("similarity_score")),
            score(result.get("keyword_coverage")),
            score(result.get("gemini_score")),
            status_cell(result),
        )
    return table


def insights_panel(run: dict[str, Any]) -> Panel:
    hallucination_rate = run.get("hallucination_rate")
    pass_rate = run.get("pass_rate")
    quality_gate_passed = run.get("quality_gate_passed")

    if hallucination_rate is None:
        readiness = "Readiness is inconclusive because hallucination data is unavailable."
        style = "yellow"
    elif hallucination_rate <= 0.10 and (pass_rate or 0) >= 0.80:
        readiness = (
            "The model looks ready for this purpose: hallucinations are low and the pass rate "
            "is strong enough for a local Ollama candidate."
        )
        style = "green"
    elif hallucination_rate <= 0.25:
        readiness = (
            "The model is promising but not production-ready yet. Tighten prompts, add more "
            "purpose-specific examples, and rerun before relying on it."
        )
        style = "yellow"
    else:
        readiness = (
            "The model is not ready for this purpose. The hallucination rate is too high for "
            "safe use without stronger retrieval, guardrails, or fine-tuning."
        )
        style = "red"

    gate = "passed" if quality_gate_passed else "failed"
    body = Group(
        Markdown(f"**Readiness:** {readiness}"),
        Text(
            f"Quality gate: {gate} | Pass rate: {pct(pass_rate)} | "
            f"Hallucination rate: {pct(hallucination_rate)} | P95 latency: {latency(run.get('p95_latency_ms'))}"
        ),
    )
    return Panel(body, title="[bold]Insights[/bold]", border_style=style, box=PANEL_BOX)


def execute_auto_test(config: CliConfig) -> None:
    load_dotenv()
    intent = read_intent_file(config.intent_file)

    console.print("[bold cyan]Discovering ready EvalForge API...[/bold cyan]")
    base_url = discover_api_url(config.api_url)
    console.print(f"[green]Using EvalForge API:[/green] {base_url}")

    console.print("[bold cyan]Checking local Ollama model before spending Gemini quota...[/bold cyan]")
    ensure_ollama_model(config.ollama_base_url, config.ollama_model, config.pull_model)

    console.print("[bold cyan]Generating evaluation dataset with one Gemini call...[/bold cyan]")
    generated_questions = generate_eval_questions(intent, config.gemini_model)

    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        console.print("[bold cyan]Creating generated EvalForge suite...[/bold cyan]")
        suite = create_suite(client, intent, config.intent_file)

        console.print(f"[bold cyan]Ingesting {len(generated_questions)} generated questions...[/bold cyan]")
        bulk_ingest_questions(client, suite["id"], generated_questions)

        console.print(f"[bold cyan]Starting Ollama evaluation run for {config.ollama_model}...[/bold cyan]")
        run = trigger_run(client, suite["id"], config.ollama_model)
        run = poll_run(client, run["id"], config.poll_interval)

        if str(run.get("status", "")).lower() != "completed":
            raise CliError(run.get("error_message") or f"Evaluation ended with status: {run.get('status')}")

        results = fetch_result_details(client, run["id"])

    render_report(intent, run, results, config.ollama_model)


@app.command("auto-test")
def auto_test(
    intent_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Text file containing roughly 5 lines describing the model purpose.",
    ),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="EvalForge API base URL. If omitted, tries EVALFORGE_API_URL, :8765, then :8000.",
    ),
    ollama_model: str = typer.Option(
        DEFAULT_OLLAMA_MODEL,
        "--model",
        "-m",
        help="Local Ollama model name to evaluate.",
    ),
    ollama_base_url: str = typer.Option(
        DEFAULT_OLLAMA_BASE_URL,
        "--ollama-url",
        help="Local Ollama API URL used for model preflight and auto-pull.",
    ),
    gemini_model: str | None = typer.Option(
        None,
        "--gemini-model",
        help=f"Gemini model used once for dataset generation. Defaults to GEMINI_MODEL or {DEFAULT_GEMINI_MODEL}.",
    ),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        min=0.5,
        help="Seconds between EvalForge run status polls.",
    ),
    pull_model: bool = typer.Option(
        True,
        "--pull-model/--no-pull-model",
        help="Automatically pull the Ollama model if it is missing.",
    ),
) -> None:
    """Generate a suite from an intent file, run Ollama through EvalForge, and render a report."""
    load_dotenv()
    config = CliConfig(
        intent_file=intent_file,
        api_url=api_url,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url.rstrip("/"),
        gemini_model=gemini_model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        poll_interval=poll_interval,
        pull_model=pull_model,
    )

    try:
        execute_auto_test(config)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        console.print(f"[bold red]EvalForge API error:[/bold red] {exc.response.status_code} {detail}")
        raise typer.Exit(code=1) from exc
    except (httpx.HTTPError, CliError, json.JSONDecodeError) as exc:
        console.print(f"[bold red]auto-test failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    typer.main.get_command(app)(prog_name="evalforge")
