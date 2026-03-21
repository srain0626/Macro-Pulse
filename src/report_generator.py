import os
import base64
import io
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

from logging_utils import get_logger
from models import RenderedAssetSnapshot, ValueFormat, normalize_dataset
from report_format_config import get_mode_format, load_report_format_config

# Use Agg backend for non-interactive environments
matplotlib.use("Agg")

logger = get_logger(__name__)


def generate_sparkline(history):
    """
    Generates a sparkline image as a base64 string.
    """
    figure, axis = plt.subplots(figsize=(2, 0.5))
    axis.plot(
        history,
        color="#2ecc71" if history[-1] >= history[0] else "#e74c3c",
        linewidth=2,
    )
    axis.axis("off")
    figure.tight_layout(pad=0)

    img = io.BytesIO()
    figure.savefig(img, format="png", transparent=True)
    img.seek(0)
    plt.close(figure)

    return base64.b64encode(img.getvalue()).decode("utf-8")


def generate_html_report(data, template_dir="src/templates"):
    """
    Generates the HTML report using Jinja2.
    """
    normalized_data = normalize_dataset(data)
    logger.info("Generating HTML report for %s categories", len(normalized_data))
    rendered_data = {
        category: [_render_item(item) for item in items]
        for category, items in normalized_data.items()
    }

    env = Environment(loader=FileSystemLoader(_resolve_template_dir(template_dir)))
    template = env.get_template("report.html")
    return template.render(data=rendered_data)


def generate_telegram_summary(data, mode="Global", format_config=None):
    """
    Generates a text summary for Telegram based on the configured market mode.
    """
    normalized_data = normalize_dataset(data)
    logger.info("Generating Telegram summary for mode=%s", mode)

    def _format_line(item):
        price = item.price
        change_pct = item.change_pct

        if price is None:
            return f"{item.name}: N/A"

        price_str = _format_numeric(price, item.value_format)

        if change_pct is not None and change_pct != 0:
            change_str = f"({change_pct:+,.2f}%)"
            return f"{item.name}: {price_str} {change_str}"

        return f"{item.name}: {price_str}"

    def get_items(category, names):
        found = []
        source_list = normalized_data.get(category, [])
        for name in names:
            for item in source_list:
                if item.name == name:
                    found.append(item)
                    break
        return found

    mode_format = get_mode_format(mode, format_config or load_report_format_config())
    sections = mode_format.summary_sections

    lines = []
    for index, section in enumerate(sections):
        lines.append(f"[{section.title}]")
        for item in get_items(section.category, section.items):
            lines.append(_format_line(item))
        if index < len(sections) - 1:
            lines.append("")

    return "\n".join(lines)


def _resolve_template_dir(template_dir):
    path = Path(template_dir)
    if path.is_absolute():
        return str(path)
    project_root = Path(__file__).resolve().parents[1]
    return str(project_root / path)


def _render_item(item) -> RenderedAssetSnapshot:
    sparkline = generate_sparkline(item.history) if len(item.history) > 1 else ""
    change_str = ""
    change_pct_str = ""
    color_class = "neutral"

    if item.change is not None:
        change_str = _format_signed_numeric(item.change, item.value_format)
        change_pct_str = (
            f"{item.change_pct:+,.2f}%" if item.change_pct is not None else ""
        )
        color_class = (
            "positive"
            if item.change > 0
            else "negative"
            if item.change < 0
            else "neutral"
        )

    return RenderedAssetSnapshot(
        name=item.name,
        price_str=_format_numeric(item.price, item.value_format),
        change_str=change_str,
        change_pct_str=change_pct_str,
        color_class=color_class,
        sparkline=sparkline,
    )


def _format_numeric(value, value_format):
    if value is None:
        return ""
    decimals = 3 if value_format == ValueFormat.YIELD_3 else 2
    return f"{value:,.{decimals}f}"


def _format_signed_numeric(value, value_format):
    if value is None:
        return ""
    decimals = 3 if value_format == ValueFormat.YIELD_3 else 2
    return f"{value:+,.{decimals}f}"


if __name__ == "__main__":
    pass
