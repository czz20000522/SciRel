"""Replace this stub with the executable task-graph black-box boundary."""

from pathlib import Path

import yaml


TASK_GRAPH_PATH = Path(__file__).with_name("task_graph.yaml")
TASK_GRAPH_CONTRACT = yaml.safe_load(TASK_GRAPH_PATH.read_text(encoding="utf-8"))


def project_state_contract(input_name):
    """Project caller state into the graph contract without adding physics."""
    return input_name


def run_graph(**inputs):
    """Execute the graph in the declared task_graph.yaml order."""
    raise NotImplementedError("replace the artifact-template stub")
