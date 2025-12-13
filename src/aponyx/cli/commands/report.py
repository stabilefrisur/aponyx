"""
Generate research report command.

Creates comprehensive analysis documents from workflow results.
"""

import json
import logging
from pathlib import Path

import click

from aponyx.reporting import generate_report
from aponyx.config import DATA_WORKFLOWS_DIR

logger = logging.getLogger(__name__)


def _resolve_workflow_dir(workflow: str) -> Path:
    """
    Resolve workflow directory from label or index.

    Parameters
    ----------
    workflow : str
        Workflow label or numeric index.

    Returns
    -------
    Path
        Resolved workflow directory path.

    Raises
    ------
    click.ClickException
        If workflow not found or invalid index.
    """
    if not DATA_WORKFLOWS_DIR.exists():
        raise click.ClickException(
            "No workflows directory found. Run a workflow first."
        )

    # Collect all workflows with valid metadata
    workflows = []
    for workflow_dir in DATA_WORKFLOWS_DIR.iterdir():
        if not workflow_dir.is_dir():
            continue

        metadata_path = workflow_dir / "metadata.json"
        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Skip workflows without label (old format)
            if "label" not in metadata:
                continue

            workflows.append(
                {
                    "dir": workflow_dir,
                    "label": metadata["label"],
                    "timestamp": metadata.get("timestamp", ""),
                }
            )
        except Exception as e:
            logger.debug("Failed to load metadata from %s: %s", workflow_dir, e)
            continue

    if not workflows:
        raise click.ClickException(
            "No workflows found with valid metadata. Run a workflow first."
        )

    # Sort by timestamp descending (newest first)
    workflows.sort(key=lambda w: w["timestamp"], reverse=True)

    # Try to parse as index
    try:
        idx = int(workflow)
        if idx < 0 or idx >= len(workflows):
            raise click.ClickException(
                f"Index {idx} out of range. Valid indices: 0-{len(workflows) - 1}. "
                f"Use 'aponyx list workflows' to see available workflows."
            )
        return workflows[idx]["dir"]
    except ValueError:
        pass

    # Search by label (latest matching timestamp)
    matching = [w for w in workflows if w["label"] == workflow]
    if not matching:
        raise click.ClickException(
            f"Workflow '{workflow}' not found. "
            f"Use 'aponyx list workflows' to see available workflows."
        )

    # Return latest matching workflow
    return matching[0]["dir"]


@click.command(name="report")
@click.option(
    "--workflow",
    required=True,
    type=str,
    help="Workflow label or numeric index from 'aponyx list workflows'",
)
@click.option(
    "--format",
    type=click.Choice(["console", "markdown", "html"], case_sensitive=False),
    default="console",
    help="Report output format (default: console)",
)
def report(
    workflow: str,
    format: str,
) -> None:
    """
    Generate comprehensive research report from workflow results.

    Aggregates suitability evaluation, performance metrics, and visualization
    references into a single document. Supports console output, markdown, and HTML.

    Workflow can be specified by:
    - Label (e.g., "my_test_run")
    - Index from 'aponyx list workflows' (e.g., "0" for most recent)

    Reports are saved to the workflow's reports/ folder.

    \b
    Examples:
        aponyx list workflows
        aponyx report --workflow my_test_run
        aponyx report --workflow 0
        aponyx report --workflow my_test_run --format markdown
        aponyx report --workflow 0 --format html

    Note: Indices are ephemeral and change as new workflows are added.
    Use workflow labels for stable references.
    """
    try:
        # Resolve workflow directory
        workflow_dir = _resolve_workflow_dir(workflow)

        # Generate report
        result = generate_report(
            workflow_dir=workflow_dir,
            format=format,
        )

        if format == "console":
            click.echo(result["content"])
        else:
            click.echo(f"Report saved: {result['output_path']}")

    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        raise click.Abort()
    except click.ClickException:
        raise
    except Exception as e:
        logger.exception("Report generation error")
        click.echo(f"Report generation failed: {e}", err=True)
        raise click.Abort()
