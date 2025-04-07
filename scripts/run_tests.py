import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('src'))
exit_code = pytest.main(['tests/test_config_agent_team.py', '-vv'])
sys.exit(exit_code) 