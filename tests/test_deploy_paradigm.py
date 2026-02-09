"""Tests for deploy_paradigm.py"""
import pytest
from click.testing import CliRunner
import sys
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import requests

# Add parent directory to path to import deploy_paradigm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deploy_paradigm import cli

@pytest.fixture
def runner():
    """CLI test runner fixture"""
    return CliRunner()

def test_cli_help(runner):
    """Test CLI displays help"""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Deployment Paradigm CLI' in result.output

def test_parse_deploy_config():
    """Test parsing deploy.yml config"""
    from deploy_paradigm import parse_deploy_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: test-app
type: python
healthCheck: /health
command: python -m uvicorn main:app
""")
        f.flush()

        config = parse_deploy_config(f.name)

        assert config['name'] == 'test-app'
        assert config['type'] == 'python'
        assert config['healthCheck'] == '/health'
        assert config['command'] == 'python -m uvicorn main:app'

        os.unlink(f.name)

def test_parse_deploy_config_minimal():
    """Test parsing minimal deploy.yml"""
    from deploy_paradigm import parse_deploy_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: minimal-app
type: python
healthCheck: /health
""")
        f.flush()

        config = parse_deploy_config(f.name)

        assert config['name'] == 'minimal-app'
        assert config.get('command') is None  # Optional field

        os.unlink(f.name)

def test_parse_deploy_config_invalid():
    """Test parsing invalid config raises error"""
    from deploy_paradigm import parse_deploy_config, ConfigError

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: missing-type
healthCheck: /health
""")
        f.flush()

        with pytest.raises(ConfigError):
            parse_deploy_config(f.name)

        os.unlink(f.name)

def test_parse_vps_config():
    """Test parsing VPS config.yml"""
    from deploy_paradigm import parse_vps_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
port: 8000
manager: systemd
env: production
""")
        f.flush()

        config = parse_vps_config(f.name)

        assert config['port'] == 8000
        assert config['manager'] == 'systemd'
        assert config['env'] == 'production'

        os.unlink(f.name)

def test_init_command(runner):
    """Test init command creates deploy.yml"""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 0
        assert 'Created deploy.yml' in result.output
        assert Path('deploy.yml').exists()

        # Verify content
        with open('deploy.yml') as f:
            content = f.read()
            assert 'name: my-app' in content
            assert 'type: python' in content

def test_init_command_file_exists(runner):
    """Test init command warns if file exists"""
    with runner.isolated_filesystem():
        # Create existing file
        Path('deploy.yml').write_text('existing')

        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 1
        assert 'already exists' in result.output

def test_health_check_success():
    """Test successful health check"""
    from deploy_paradigm import health_check

    with patch('deploy_paradigm.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = health_check('http://localhost:8000/health', retries=1, delay=0)

        assert result is True
        mock_get.assert_called_once()

def test_health_check_failure():
    """Test failed health check"""
    from deploy_paradigm import health_check

    with patch('deploy_paradigm.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = health_check('http://localhost:8000/health', retries=2, delay=0)

        assert result is False
        assert mock_get.call_count == 2  # Should retry

def test_health_check_eventual_success():
    """Test health check succeeds after retry"""
    from deploy_paradigm import health_check

    with patch('deploy_paradigm.requests.get') as mock_get:
        # Fail first, succeed second
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            mock_response
        ]

        result = health_check('http://localhost:8000/health', retries=2, delay=0)

        assert result is True
        assert mock_get.call_count == 2

def test_python_deployer_install():
    """Test Python deployer installs dependencies"""
    from deploy_paradigm import PythonDeployer

    with tempfile.TemporaryDirectory() as tmpdir:
        release_dir = Path(tmpdir)

        # Create requirements.txt
        (release_dir / 'requirements.txt').write_text('requests==2.31.0\n')

        deployer = PythonDeployer({'name': 'test-app', 'type': 'python'})

        with patch('deploy_paradigm.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            deployer.install_dependencies(release_dir)

            # Verify venv creation and pip install
            assert mock_run.call_count >= 2

def test_python_deployer_no_requirements():
    """Test Python deployer handles missing requirements.txt"""
    from deploy_paradigm import PythonDeployer

    with tempfile.TemporaryDirectory() as tmpdir:
        release_dir = Path(tmpdir)
        # No requirements.txt

        deployer = PythonDeployer({'name': 'test-app', 'type': 'python'})

        with patch('deploy_paradigm.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            deployer.install_dependencies(release_dir)

            # Should still create venv


def test_docker_deployer_build():
    """Test Docker deployer builds image"""
    from deploy_paradigm import DockerDeployer

    with tempfile.TemporaryDirectory() as tmpdir:
        release_dir = Path(tmpdir)

        # Create Dockerfile
        (release_dir / 'Dockerfile').write_text('FROM python:3.9\nCOPY . /app\n')

        deployer = DockerDeployer({'name': 'test-app', 'type': 'docker'})

        with patch('deploy_paradigm.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', check=True)

            deployer.install_dependencies(release_dir)

            # Should call docker build
            assert mock_run.called
            # Check that docker build was called (first call)
            first_call = mock_run.call_args_list[0]
            assert 'docker' in first_call[0][0]
            assert 'build' in first_call[0][0]
            assert mock_run.call_count >= 1

def test_execute_command_basic():
    """Test execute command basic flow"""
    from deploy_paradigm import execute_deployment

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create mock git repo
        git_dir = base_dir / 'repo.git'
        git_dir.mkdir()

        # Create mock deploy.yml content
        deploy_config = {
            'name': 'test-app',
            'type': 'python',
            'healthCheck': '/health',
            'deployment': {'strategy': 'simple'}
        }

        # Create VPS config
        vps_config = {
            'port': 8000,
            'manager': 'systemd',
            'env': 'production'
        }

        # Mock all subprocess calls
        with patch('deploy_paradigm.subprocess.run') as mock_run, \
             patch('deploy_paradigm.health_check') as mock_health, \
             patch('deploy_paradigm.parse_deploy_config') as mock_parse_deploy, \
             patch('deploy_paradigm.parse_vps_config') as mock_parse_vps:

            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            mock_health.return_value = True
            mock_parse_deploy.return_value = deploy_config
            mock_parse_vps.return_value = vps_config

            # Create deployment base dir
            deploy_base = base_dir / 'deployments' / 'test-app'
            deploy_base.mkdir(parents=True)
            (deploy_base / 'config.yml').write_text('port: 8000\nmanager: systemd\n')

            result = execute_deployment(str(git_dir), 'abc123', str(deploy_base))

            assert result is True

def test_setup_command(runner):
    """Test setup command creates necessary structure"""
    import shutil as shutil_mod

    with runner.isolated_filesystem():
        # Clean up any previous test runs
        if Path('/tmp/test-repos').exists():
            shutil_mod.rmtree('/tmp/test-repos')
        if Path('/tmp/test-deployments').exists():
            shutil_mod.rmtree('/tmp/test-deployments')

        # Create mock directories
        Path('/tmp/test-repos').mkdir(exist_ok=True, parents=True)
        Path('/tmp/test-deployments').mkdir(exist_ok=True, parents=True)

        # Get real templates dir
        from deploy_paradigm import TEMPLATES_DIR as real_templates

        with patch('deploy_paradigm.REPOS_DIR', Path('/tmp/test-repos')), \
             patch('deploy_paradigm.DEPLOYMENTS_DIR', Path('/tmp/test-deployments')), \
             patch('deploy_paradigm.TEMPLATES_DIR', real_templates), \
             patch('deploy_paradigm.subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(cli, [
                'setup',
                'test-app',
                'git@github.com:user/test-app.git',
                '--port', '8000',
                '--manager', 'systemd'
            ])

            if result.exit_code != 0:
                print(result.output)
                if result.exception:
                    import traceback
                    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

            assert result.exit_code == 0
            assert Path('/tmp/test-repos/test-app.git').exists()
            assert Path('/tmp/test-deployments/test-app').exists()

def test_strategy_config_parsing():
    """Test deployment strategy in config"""
    from deploy_paradigm import parse_deploy_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: test-app
type: python
healthCheck: /health
deployment:
  strategy: blue-green
  keepInactive: true
""")
        f.flush()

        config = parse_deploy_config(f.name)

        assert config['deployment']['strategy'] == 'blue-green'
        assert config['deployment']['keepInactive'] is True

        os.unlink(f.name)

def test_default_strategy():
    """Test default strategy is simple"""
    from deploy_paradigm import parse_deploy_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: test-app
type: python
healthCheck: /health
""")
        f.flush()

        config = parse_deploy_config(f.name)

        assert config['deployment']['strategy'] == 'simple'

        os.unlink(f.name)

def test_invalid_strategy():
    """Test invalid strategy raises error"""
    from deploy_paradigm import parse_deploy_config, ConfigError

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("""
name: test-app
type: python
healthCheck: /health
deployment:
  strategy: invalid-strategy
""")
        f.flush()

        with pytest.raises(ConfigError) as exc_info:
            parse_deploy_config(f.name)

        assert 'Invalid strategy' in str(exc_info.value)

        os.unlink(f.name)

def test_get_deployment_strategy():
    """Test deployment strategy factory"""
    from deploy_paradigm import get_deployment_strategy, SimpleStrategy, BlueGreenStrategy, RollingStrategy

    deploy_config = {
        'name': 'test-app',
        'type': 'python',
        'healthCheck': '/health',
        'deployment': {'strategy': 'simple'}
    }

    vps_config = {
        'port': 8000,
        'manager': 'systemd',
        'env': 'production'
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        strategy = get_deployment_strategy(deploy_config, vps_config, tmpdir)
        assert isinstance(strategy, SimpleStrategy)

        deploy_config['deployment']['strategy'] = 'blue-green'
        strategy = get_deployment_strategy(deploy_config, vps_config, tmpdir)
        assert isinstance(strategy, BlueGreenStrategy)

        deploy_config['deployment']['strategy'] = 'rolling'
        strategy = get_deployment_strategy(deploy_config, vps_config, tmpdir)
        assert isinstance(strategy, RollingStrategy)
