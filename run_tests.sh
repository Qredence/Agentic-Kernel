#!/bin/bash
cd /Volumes/Samsung-SSD-T7/QredenceBeta/Builderio/app/AgenticFleet-Labs
source .venv/bin/activate
pip install -e '.[test,dev]'
python -m pytest tests/test_orchestrator_workflow.py -v 