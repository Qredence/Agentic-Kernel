#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=src
python3 -m pytest tests/test_config_agent_team.py -vv 