# Week 1: Core Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core deployment system that deploys Python apps via git push with health checks and rollback

**Architecture:** Single-file CLI (`deploy_paradigm.py`) with three commands (init, setup, execute). Uses symlink swapping for zero-downtime, health check validation, and automatic rollback on failure.

**Tech Stack:** Python 3.10+, Click (CLI), PyYAML (config), requests (health checks)

---

## Prerequisites

**Required tools:**
- Python 3.10+
- pytest (for testing)
- Git

**Install dependencies:**
```bash
pip install click pyyaml requests pytest pytest-mock
```

---

## Task 1: Project Structure Setup

**Files:**
- Create: `deploy_paradigm.py`
- Create: `tests/test_deploy_paradigm.py`
- Create: `requirements.txt`
- Create: `templates/deploy.yml.template`
- Create: `templates/post-receive.sh`
- Create: `templates/app-config.yml.template`

**Step 1: Create requirements.txt**

Create `requirements.txt`:
```txt
click>=8.1.0
pyyaml>=6.0
requests>=2.31.0
```

**Step 2: Create deploy_paradigm.py skeleton**

Create `deploy_paradigm.py`:
```python
#!/usr/bin/env python3
"""
Deployment Paradigm - Standardized deployment for VPS applications
"""
import click

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Deployment Paradigm CLI"""
    pass

if __name__ == '__main__':
    cli()
```

**Step 3: Make executable and test**

Run:
```bash
chmod +x deploy_paradigm.py
python deploy_paradigm.py --help
```

Expected output:
```
Usage: deploy_paradigm.py [OPTIONS] COMMAND [ARGS]...

  Deployment Paradigm CLI

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.
```

**Step 4: Create test file skeleton**

Create `tests/test_deploy_paradigm.py`:
```python
"""Tests for deploy_paradigm.py"""
import pytest
from click.testing import CliRunner
import sys
import os

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
```

**Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add deploy_paradigm.py tests/test_deploy_paradigm.py requirements.txt
git commit -m "feat: add deployment paradigm CLI skeleton

- Create Click-based CLI with version
- Add basic test structure
- Define dependencies in requirements.txt"
```

---

## Task 2: Configuration Models

**Files:**
- Modify: `deploy_paradigm.py`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Write tests for config parsing**

Add to `tests/test_deploy_paradigm.py`:
```python
import tempfile
import yaml
from pathlib import Path

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
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_parse_deploy_config -v
```

Expected: FAIL with "ImportError: cannot import name 'parse_deploy_config'"

**Step 3: Implement config parsing**

Add to `deploy_paradigm.py` (after imports, before cli()):
```python
import yaml
import sys
from pathlib import Path

class ConfigError(Exception):
    """Configuration validation error"""
    pass

def parse_deploy_config(config_path):
    """
    Parse and validate deploy.yml configuration

    Args:
        config_path: Path to deploy.yml file

    Returns:
        dict: Validated configuration

    Raises:
        ConfigError: If configuration is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    # Validate required fields
    required = ['name', 'type', 'healthCheck']
    for field in required:
        if field not in config:
            raise ConfigError(f"Missing required field: {field}")

    # Validate type
    valid_types = ['python', 'node', 'docker', 'static']
    if config['type'] not in valid_types:
        raise ConfigError(f"Invalid type: {config['type']}. Must be one of {valid_types}")

    return config

def parse_vps_config(config_path):
    """
    Parse VPS-specific config.yml

    Args:
        config_path: Path to config.yml file

    Returns:
        dict: VPS configuration
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"VPS config not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    return config
```

**Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k config
```

Expected: All config tests PASS

**Step 5: Commit**

```bash
git add deploy_paradigm.py tests/test_deploy_paradigm.py
git commit -m "feat: add config parsing and validation

- Parse deploy.yml with required field validation
- Parse VPS config.yml
- Add ConfigError for validation errors
- Test minimal and full config variants"
```

---

## Task 3: Init Command

**Files:**
- Modify: `deploy_paradigm.py`
- Create: `templates/deploy.yml.template`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Create template file**

Create `templates/deploy.yml.template`:
```yaml
# Deployment configuration
# See: https://github.com/you/deployment-paradigm

# Required fields
name: my-app              # Deployment name
type: python              # python|node|docker|static
healthCheck: /health      # Health check endpoint (relative path)

# Optional fields
command: python -m uvicorn main:app  # Override default start command

# Optional hooks
hooks:
  preDeploy: ./scripts/migrate.sh    # Run before deployment (e.g., migrations)
  postDeploy: ./scripts/notify.sh    # Run after successful deployment
```

**Step 2: Write test for init command**

Add to `tests/test_deploy_paradigm.py`:
```python
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
```

**Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_init_command -v
```

Expected: FAIL with "UsageError: No such command 'init'"

**Step 4: Implement init command**

Add to `deploy_paradigm.py` (after parse_vps_config, before cli group):
```python
import shutil

TEMPLATES_DIR = Path(__file__).parent / 'templates'

@cli.command()
def init():
    """Initialize deploy.yml in current directory"""
    deploy_yml = Path('deploy.yml')

    if deploy_yml.exists():
        click.echo(click.style('❌ deploy.yml already exists', fg='red'))
        sys.exit(1)

    template_path = TEMPLATES_DIR / 'deploy.yml.template'

    if not template_path.exists():
        click.echo(click.style(f'❌ Template not found: {template_path}', fg='red'))
        sys.exit(1)

    # Copy template
    shutil.copy(template_path, deploy_yml)

    click.echo(click.style('✓ Created deploy.yml', fg='green'))
    click.echo('Edit deploy.yml to configure your application')
```

**Step 5: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k init
```

Expected: All init tests PASS

**Step 6: Commit**

```bash
git add deploy_paradigm.py templates/deploy.yml.template tests/test_deploy_paradigm.py
git commit -m "feat: add init command

- Create deploy.yml from template
- Check for existing file before overwriting
- Add deploy.yml.template with documented fields"
```

---

## Task 4: Health Check Function

**Files:**
- Modify: `deploy_paradigm.py`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Write tests for health check**

Add to `tests/test_deploy_paradigm.py`:
```python
from unittest.mock import Mock, patch
import requests

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
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_health_check_success -v
```

Expected: FAIL with "ImportError: cannot import name 'health_check'"

**Step 3: Implement health check**

Add to `deploy_paradigm.py` (after config functions):
```python
import requests
import time

def health_check(url, retries=3, delay=5, timeout=10):
    """
    Check if application health endpoint is responding

    Args:
        url: Full health check URL (e.g., http://localhost:8000/health)
        retries: Number of attempts
        delay: Seconds between retries
        timeout: Request timeout in seconds

    Returns:
        bool: True if healthy, False otherwise
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                click.echo(click.style(f'✓ Health check passed: {url}', fg='green'))
                return True
            else:
                click.echo(click.style(f'⚠ Health check returned {response.status_code}', fg='yellow'))
        except requests.exceptions.RequestException as e:
            click.echo(click.style(f'⚠ Health check failed (attempt {attempt + 1}/{retries}): {e}', fg='yellow'))

        if attempt < retries - 1:
            time.sleep(delay)

    click.echo(click.style(f'❌ Health check failed after {retries} attempts', fg='red'))
    return False
```

**Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k health_check
```

Expected: All health_check tests PASS

**Step 5: Commit**

```bash
git add deploy_paradigm.py tests/test_deploy_paradigm.py
git commit -m "feat: add health check function

- Perform HTTP GET to health endpoint
- Retry with configurable attempts and delay
- Return boolean success/failure
- Log progress to user"
```

---

## Task 5: Python Deployer

**Files:**
- Modify: `deploy_paradigm.py`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Write tests for Python deployer**

Add to `tests/test_deploy_paradigm.py`:
```python
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
            assert mock_run.call_count >= 1
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_python_deployer_install -v
```

Expected: FAIL with "ImportError: cannot import name 'PythonDeployer'"

**Step 3: Implement base deployer and Python deployer**

Add to `deploy_paradigm.py` (after health_check):
```python
import subprocess
from abc import ABC, abstractmethod

class Deployer(ABC):
    """Base deployer class"""

    def __init__(self, deploy_config):
        self.config = deploy_config

    @abstractmethod
    def install_dependencies(self, release_dir):
        """Install application dependencies"""
        pass

    @abstractmethod
    def get_start_command(self):
        """Get command to start the application"""
        pass

class PythonDeployer(Deployer):
    """Deployer for Python applications"""

    def install_dependencies(self, release_dir):
        """
        Install Python dependencies in virtualenv

        Args:
            release_dir: Path to release directory
        """
        release_dir = Path(release_dir)
        venv_dir = release_dir / 'venv'

        click.echo('Creating Python virtual environment...')
        result = subprocess.run(
            ['python3', '-m', 'venv', str(venv_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f'Failed to create venv: {result.stderr}')

        # Check if requirements.txt exists
        requirements = release_dir / 'requirements.txt'
        if requirements.exists():
            click.echo('Installing dependencies from requirements.txt...')
            pip_path = venv_dir / 'bin' / 'pip'
            result = subprocess.run(
                [str(pip_path), 'install', '-r', str(requirements)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f'Failed to install dependencies: {result.stderr}')

            click.echo(click.style('✓ Dependencies installed', fg='green'))
        else:
            click.echo('No requirements.txt found, skipping dependency installation')

    def get_start_command(self):
        """Get command to start Python app"""
        # Use custom command if provided, otherwise default
        if 'command' in self.config:
            return self.config['command']

        # Default: assume main.py exists
        return 'python main.py'

def get_deployer(deploy_config):
    """
    Factory function to get appropriate deployer

    Args:
        deploy_config: Parsed deploy.yml config

    Returns:
        Deployer: Appropriate deployer instance
    """
    deployer_map = {
        'python': PythonDeployer,
    }

    app_type = deploy_config['type']
    if app_type not in deployer_map:
        raise ConfigError(f'Unsupported app type: {app_type}')

    return deployer_map[app_type](deploy_config)
```

**Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k deployer
```

Expected: All deployer tests PASS

**Step 5: Commit**

```bash
git add deploy_paradigm.py tests/test_deploy_paradigm.py
git commit -m "feat: add Python deployer

- Create base Deployer abstract class
- Implement PythonDeployer with venv + pip install
- Add factory function to get deployer by type
- Handle missing requirements.txt gracefully"
```

---

## Task 6: Execute Command Core

**Files:**
- Modify: `deploy_paradigm.py`
- Create: `templates/post-receive.sh`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Create post-receive hook template**

Create `templates/post-receive.sh`:
```bash
#!/bin/bash
# Post-receive hook for Deployment Paradigm
# This hook is called by git after receiving a push

set -e

# Read stdin (old_commit new_commit ref_name)
while read oldrev newrev refname; do
    # Only deploy on main/master branch
    if [[ "$refname" == "refs/heads/main" ]] || [[ "$refname" == "refs/heads/master" ]]; then
        echo "=== Deployment Paradigm ==="
        echo "Deploying $refname: $newrev"

        # Call deployment script
        /usr/local/bin/deploy-paradigm execute "$GIT_DIR" "$newrev"

        exit_code=$?
        if [ $exit_code -eq 0 ]; then
            echo "✓ Deployment successful"
        else
            echo "❌ Deployment failed"
            exit $exit_code
        fi
    else
        echo "Skipping deployment for branch: $refname"
    fi
done
```

**Step 2: Write tests for execute command**

Add to `tests/test_deploy_paradigm.py`:
```python
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
            'healthCheck': '/health'
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

            mock_run.return_value = Mock(returncode=0)
            mock_health.return_value = True
            mock_parse_deploy.return_value = deploy_config
            mock_parse_vps.return_value = vps_config

            # Create deployment base dir
            deploy_base = base_dir / 'deployments' / 'test-app'
            deploy_base.mkdir(parents=True)
            (deploy_base / 'config.yml').write_text('port: 8000\nmanager: systemd\n')

            result = execute_deployment(str(git_dir), 'abc123', str(deploy_base))

            assert result is True
```

**Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_execute_command_basic -v
```

Expected: FAIL with "ImportError: cannot import name 'execute_deployment'"

**Step 4: Implement execute_deployment function**

Add to `deploy_paradigm.py` (after get_deployer):
```python
import os
from datetime import datetime

def execute_deployment(git_dir, commit_sha, deployment_base_dir):
    """
    Execute deployment for a git push

    Args:
        git_dir: Path to git repository
        commit_sha: Commit SHA to deploy
        deployment_base_dir: Base deployment directory (e.g., /opt/deployments/app-name)

    Returns:
        bool: True if deployment succeeded, False otherwise
    """
    deployment_base = Path(deployment_base_dir)

    click.echo(f'\n=== Deploying commit {commit_sha[:7]} ===\n')

    # 1. Extract deploy.yml from commit
    click.echo('Extracting deploy.yml...')
    result = subprocess.run(
        ['git', '--git-dir', git_dir, 'show', f'{commit_sha}:deploy.yml'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        click.echo(click.style('❌ deploy.yml not found in repository', fg='red'))
        return False

    # Save to temp file
    deploy_yml_path = Path('/tmp/deploy.yml')
    deploy_yml_path.write_text(result.stdout)

    # Parse configs
    try:
        deploy_config = parse_deploy_config(str(deploy_yml_path))
    except ConfigError as e:
        click.echo(click.style(f'❌ Invalid deploy.yml: {e}', fg='red'))
        return False

    vps_config_path = deployment_base / 'config.yml'
    if not vps_config_path.exists():
        click.echo(click.style(f'❌ VPS config not found: {vps_config_path}', fg='red'))
        return False

    vps_config = parse_vps_config(str(vps_config_path))

    # 2. Create release directory
    timestamp = int(datetime.now().timestamp())
    releases_dir = deployment_base / 'releases'
    releases_dir.mkdir(exist_ok=True)

    release_dir = releases_dir / str(timestamp)
    click.echo(f'Creating release: {release_dir}')

    # Clone repository to release directory
    result = subprocess.run(
        ['git', 'clone', git_dir, str(release_dir)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        click.echo(click.style(f'❌ Failed to clone repository: {result.stderr}', fg='red'))
        return False

    # Checkout specific commit
    result = subprocess.run(
        ['git', '-C', str(release_dir), 'checkout', commit_sha],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        click.echo(click.style(f'❌ Failed to checkout commit: {result.stderr}', fg='red'))
        return False

    click.echo(click.style('✓ Release created', fg='green'))

    # 3. Install dependencies
    try:
        deployer = get_deployer(deploy_config)
        deployer.install_dependencies(release_dir)
    except Exception as e:
        click.echo(click.style(f'❌ Failed to install dependencies: {e}', fg='red'))
        return False

    # 4. Copy environment file if exists
    env_file = deployment_base / f".env.{vps_config.get('env', 'production')}"
    if env_file.exists():
        click.echo('Copying environment file...')
        shutil.copy(env_file, release_dir / '.env')

    # 5. Run pre-deploy hook if configured
    if 'hooks' in deploy_config and 'preDeploy' in deploy_config['hooks']:
        hook_script = release_dir / deploy_config['hooks']['preDeploy']
        if hook_script.exists():
            click.echo('Running pre-deploy hook...')
            result = subprocess.run(
                [str(hook_script)],
                cwd=release_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                click.echo(click.style(f'❌ Pre-deploy hook failed: {result.stderr}', fg='red'))
                return False

    # 6. Update symlink
    current_link = deployment_base / 'current'
    previous_link = deployment_base / 'previous'

    # Save current as previous
    if current_link.exists():
        if previous_link.exists():
            previous_link.unlink()
        shutil.copy(current_link, previous_link)

    # Point current to new release
    if current_link.exists():
        current_link.unlink()

    current_link.symlink_to(release_dir)
    click.echo(click.style('✓ Symlink updated', fg='green'))

    # 7. Reload process manager
    click.echo(f"Reloading {vps_config['manager']}...")
    app_name = deploy_config['name']

    if vps_config['manager'] == 'systemd':
        result = subprocess.run(
            ['systemctl', 'reload', app_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            click.echo(click.style(f'⚠ Failed to reload systemd: {result.stderr}', fg='yellow'))

    # 8. Health check
    click.echo('\nWaiting 10s for application startup...')
    time.sleep(10)

    health_url = f"http://localhost:{vps_config['port']}{deploy_config['healthCheck']}"
    click.echo(f'Running health check: {health_url}')

    if not health_check(health_url, retries=3, delay=5):
        # Rollback
        click.echo(click.style('\n❌ Health check failed, rolling back...', fg='red'))

        if previous_link.exists():
            current_link.unlink()
            shutil.copy(previous_link, current_link)

            if vps_config['manager'] == 'systemd':
                subprocess.run(['systemctl', 'reload', app_name])

            click.echo(click.style('✓ Rolled back to previous release', fg='green'))

        return False

    # 9. Success
    click.echo(click.style('\n✓ Deployment successful!', fg='green'))

    # Cleanup old releases (keep last 3)
    releases = sorted(releases_dir.iterdir(), key=lambda p: p.name)
    if len(releases) > 3:
        for old_release in releases[:-3]:
            click.echo(f'Cleaning up old release: {old_release.name}')
            shutil.rmtree(old_release)

    return True
```

**Step 5: Add execute CLI command**

Add to `deploy_paradigm.py` (as a command in the CLI group):
```python
@cli.command()
@click.argument('git_dir')
@click.argument('commit_sha')
def execute(git_dir, commit_sha):
    """
    Execute deployment (called by git post-receive hook)

    GIT_DIR: Path to git repository
    COMMIT_SHA: Commit to deploy
    """
    # Determine app name from git directory
    # Assume git dir is like /var/repos/app-name.git
    git_path = Path(git_dir)
    app_name = git_path.stem.replace('.git', '')

    deployment_base = Path('/opt/deployments') / app_name

    if not deployment_base.exists():
        click.echo(click.style(f'❌ Deployment not configured: {app_name}', fg='red'))
        click.echo(f'Run: deploy-paradigm setup {app_name} <git-url>')
        sys.exit(1)

    success = execute_deployment(git_dir, commit_sha, str(deployment_base))

    if not success:
        sys.exit(1)
```

**Step 6: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k execute
```

Expected: All execute tests PASS

**Step 7: Commit**

```bash
git add deploy_paradigm.py templates/post-receive.sh tests/test_deploy_paradigm.py
git commit -m "feat: add execute deployment command

- Extract deploy.yml from git commit
- Create timestamped release directory
- Install dependencies via deployer
- Update symlink with previous backup
- Perform health check with rollback on failure
- Cleanup old releases (keep last 3)
- Add post-receive hook template"
```

---

## Task 7: Setup Command

**Files:**
- Modify: `deploy_paradigm.py`
- Create: `templates/app-config.yml.template`
- Modify: `tests/test_deploy_paradigm.py`

**Step 1: Create app config template**

Create `templates/app-config.yml.template`:
```yaml
# VPS-specific configuration
# This file is NOT in git - it stays on the VPS

port: 8000
manager: systemd  # systemd or pm2
env: production
```

**Step 2: Write tests for setup command**

Add to `tests/test_deploy_paradigm.py`:
```python
def test_setup_command(runner):
    """Test setup command creates necessary structure"""
    with runner.isolated_filesystem():
        # Create mock directories
        Path('/tmp/test-repos').mkdir(exist_ok=True, parents=True)
        Path('/tmp/test-deployments').mkdir(exist_ok=True, parents=True)

        with patch('deploy_paradigm.REPOS_DIR', Path('/tmp/test-repos')), \
             patch('deploy_paradigm.DEPLOYMENTS_DIR', Path('/tmp/test-deployments')), \
             patch('deploy_paradigm.subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(cli, [
                'setup',
                'test-app',
                'git@github.com:user/test-app.git',
                '--port', '8000',
                '--manager', 'systemd'
            ])

            assert result.exit_code == 0
            assert Path('/tmp/test-repos/test-app.git').exists()
            assert Path('/tmp/test-deployments/test-app').exists()
```

**Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/test_deploy_paradigm.py::test_setup_command -v
```

Expected: FAIL with "UsageError: No such command 'setup'"

**Step 4: Implement setup command**

Add to `deploy_paradigm.py` (constants near top):
```python
REPOS_DIR = Path('/var/repos')
DEPLOYMENTS_DIR = Path('/opt/deployments')
```

Add setup command to CLI group:
```python
@cli.command()
@click.argument('app_name')
@click.argument('git_url')
@click.option('--port', default=8000, help='Application port')
@click.option('--manager', type=click.Choice(['systemd', 'pm2']), default='systemd', help='Process manager')
@click.option('--env', default='production', help='Environment name')
def setup(app_name, git_url, port, manager, env):
    """
    Setup VPS for an application

    APP_NAME: Name of the application
    GIT_URL: Git repository URL
    """
    click.echo(f'\n=== Setting up {app_name} ===\n')

    # 1. Create bare git repository
    git_repo_dir = REPOS_DIR / f'{app_name}.git'

    if git_repo_dir.exists():
        click.echo(click.style(f'⚠ Git repository already exists: {git_repo_dir}', fg='yellow'))
    else:
        click.echo(f'Creating bare git repository: {git_repo_dir}')
        git_repo_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ['git', 'init', '--bare', str(git_repo_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            click.echo(click.style(f'❌ Failed to create git repo: {result.stderr}', fg='red'))
            sys.exit(1)

        click.echo(click.style('✓ Git repository created', fg='green'))

    # 2. Install post-receive hook
    hooks_dir = git_repo_dir / 'hooks'
    post_receive_hook = hooks_dir / 'post-receive'

    template_hook = TEMPLATES_DIR / 'post-receive.sh'

    if template_hook.exists():
        shutil.copy(template_hook, post_receive_hook)
        post_receive_hook.chmod(0o755)
        click.echo(click.style('✓ Post-receive hook installed', fg='green'))
    else:
        click.echo(click.style(f'⚠ Hook template not found: {template_hook}', fg='yellow'))

    # 3. Create deployment directory structure
    deploy_dir = DEPLOYMENTS_DIR / app_name
    deploy_dir.mkdir(parents=True, exist_ok=True)

    (deploy_dir / 'releases').mkdir(exist_ok=True)

    click.echo(click.style(f'✓ Deployment directory created: {deploy_dir}', fg='green'))

    # 4. Create VPS config
    config_file = deploy_dir / 'config.yml'

    if config_file.exists():
        click.echo(click.style(f'⚠ Config already exists: {config_file}', fg='yellow'))
    else:
        config_content = f"""# VPS Configuration for {app_name}
port: {port}
manager: {manager}
env: {env}
"""
        config_file.write_text(config_content)
        click.echo(click.style('✓ VPS config created', fg='green'))

    # 5. Create systemd service if using systemd
    if manager == 'systemd':
        service_file = Path(f'/etc/systemd/system/{app_name}.service')

        if service_file.exists():
            click.echo(click.style(f'⚠ Systemd service already exists: {service_file}', fg='yellow'))
        else:
            service_content = f"""[Unit]
Description={app_name} application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/deployments/{app_name}/current
ExecStart=/opt/deployments/{app_name}/current/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port {port}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            try:
                service_file.write_text(service_content)

                # Reload systemd
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
                subprocess.run(['systemctl', 'enable', app_name], check=True)

                click.echo(click.style(f'✓ Systemd service created: {app_name}.service', fg='green'))
            except PermissionError:
                click.echo(click.style(f'⚠ Cannot create systemd service (need sudo)', fg='yellow'))
                click.echo(f'Run manually: sudo systemctl enable {app_name}')

    # 6. Print instructions
    click.echo(click.style('\n=== Setup Complete ===\n', fg='green', bold=True))
    click.echo('Next steps:')
    click.echo(f'1. On your local machine, add git remote:')
    click.echo(f'   git remote add production <user>@<host>:{git_repo_dir}')
    click.echo(f'2. Add deploy.yml to your project:')
    click.echo(f'   deploy-paradigm init')
    click.echo(f'3. Deploy:')
    click.echo(f'   git push production main')
```

**Step 5: Run tests to verify they pass**

Run:
```bash
pytest tests/test_deploy_paradigm.py -v -k setup
```

Expected: All setup tests PASS

**Step 6: Commit**

```bash
git add deploy_paradigm.py templates/app-config.yml.template tests/test_deploy_paradigm.py
git commit -m "feat: add setup command

- Create bare git repository with post-receive hook
- Create deployment directory structure
- Generate VPS config.yml
- Create systemd service file
- Print setup instructions for user"
```

---

## Task 8: Install Script

**Files:**
- Create: `install.sh`

**Step 1: Create install script**

Create `install.sh`:
```bash
#!/bin/bash
# Installation script for Deployment Paradigm

set -e

echo "=== Installing Deployment Paradigm ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Create installation directory
INSTALL_DIR="/opt/deployment-paradigm"
echo "Creating installation directory: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"

# Clone or copy files
if [ -d ".git" ]; then
    # Running from git repo
    echo "Copying files from current directory..."
    sudo cp deploy_paradigm.py "$INSTALL_DIR/"
    sudo cp -r templates "$INSTALL_DIR/"
else
    # Download from GitHub (future)
    echo "Downloading latest version..."
    REPO_URL="https://github.com/you/deployment-paradigm"
    sudo git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing Python dependencies..."
sudo pip3 install click pyyaml requests

# Create symlink
echo "Creating symlink: /usr/local/bin/deploy-paradigm"
sudo ln -sf "$INSTALL_DIR/deploy_paradigm.py" /usr/local/bin/deploy-paradigm
sudo chmod +x /usr/local/bin/deploy-paradigm

# Create directories
echo "Creating deployment directories..."
sudo mkdir -p /var/repos
sudo mkdir -p /opt/deployments
sudo mkdir -p /var/log/deployments

# Set permissions
sudo chown -R $USER:$USER /opt/deployments
sudo chown -R $USER:$USER /var/repos
sudo chown -R $USER:$USER /var/log/deployments

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Setup an application:"
echo "   deploy-paradigm setup <app-name> <git-url>"
echo ""
echo "2. Or check help:"
echo "   deploy-paradigm --help"
```

**Step 2: Make executable**

Run:
```bash
chmod +x install.sh
```

**Step 3: Test install script (dry run)**

Run:
```bash
bash -n install.sh  # Syntax check
```

Expected: No errors

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add installation script

- Check Python version requirement
- Copy files to /opt/deployment-paradigm
- Install dependencies via pip
- Create symlink to /usr/local/bin
- Create deployment directories with permissions"
```

---

## Task 9: README Documentation

**Files:**
- Create: `README.md`

**Step 1: Create comprehensive README**

Create `README.md`:
```markdown
# Deployment Paradigm

A standardized deployment system for VPS applications with zero-downtime deploys, health checks, and automatic rollback.

## Features

- **Zero-downtime deployments** - Symlink-based swapping keeps old version running until new is healthy
- **Health checks** - Validate deployments before switching traffic
- **Automatic rollback** - Failed health checks trigger instant rollback
- **Multi-type support** - Python, Node.js, Docker (Week 1: Python only)
- **Git-based workflow** - Deploy with `git push production main`

## Installation

### On VPS

```bash
curl -sSL https://raw.githubusercontent.com/you/deployment-paradigm/main/install.sh | bash
```

Or install manually:

```bash
git clone https://github.com/you/deployment-paradigm /opt/deployment-paradigm
cd /opt/deployment-paradigm
pip install -r requirements.txt
sudo ln -s /opt/deployment-paradigm/deploy_paradigm.py /usr/local/bin/deploy-paradigm
```

## Quick Start

### 1. Setup VPS for your app

On your VPS:

```bash
deploy-paradigm setup my-api git@github.com:you/my-api.git --port 8000 --manager systemd
```

This creates:
- Bare git repository at `/var/repos/my-api.git`
- Deployment directory at `/opt/deployments/my-api`
- Systemd service for your app

### 2. Configure your project

In your project repository:

```bash
deploy-paradigm init
```

Edit `deploy.yml`:

```yaml
name: my-api
type: python
healthCheck: /health
command: python -m uvicorn main:app
```

Commit and push:

```bash
git add deploy.yml
git commit -m "Add deployment config"
```

### 3. Add git remote

On your local machine:

```bash
git remote add production user@your-vps.com:/var/repos/my-api.git
```

### 4. Deploy

```bash
git push production main
```

Watch the deployment process:
- Extracts config from commit
- Creates timestamped release
- Installs dependencies in virtualenv
- Updates symlink
- Runs health check
- Rolls back if health check fails

## Configuration

### deploy.yml (in your project repo)

```yaml
# Required
name: my-api              # Application name
type: python              # python|node|docker|static
healthCheck: /health      # Health check endpoint

# Optional
command: python -m uvicorn main:app  # Custom start command

hooks:
  preDeploy: ./scripts/migrate.sh    # Run before deployment
  postDeploy: ./scripts/notify.sh    # Run after success
```

### VPS config (on server)

Located at `/opt/deployments/{app-name}/config.yml`:

```yaml
port: 8000
manager: systemd  # or pm2
env: production
```

## Directory Structure

On VPS:

```
/opt/deployments/{app-name}/
├── releases/
│   ├── 1707319401/          # Old release
│   └── 1707319402/          # New release
├── current -> releases/1707319402/  # Symlink
├── previous -> releases/1707319401/ # For rollback
├── config.yml               # VPS config
└── .env.production          # Environment variables

/var/repos/{app-name}.git/   # Bare git repository
└── hooks/
    └── post-receive         # Deployment trigger
```

## Health Checks

Your application must expose a health check endpoint that returns HTTP 200 when healthy.

Example (Flask):

```python
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200
```

Example (FastAPI):

```python
@app.get('/health')
def health():
    return {'status': 'healthy'}
```

The deployment system will:
1. Wait 10s after restarting the app
2. Make 3 health check attempts (5s apart)
3. Rollback if any attempt fails

## Rollback

Automatic rollback happens when:
- Health check fails
- Pre-deploy hook fails

Manual rollback:

```bash
# On VPS
cd /opt/deployments/my-api
ln -sfn previous current
systemctl reload my-api
```

## Troubleshooting

**Deployment fails with "deploy.yml not found"**
- Ensure `deploy.yml` is committed to your repository
- Check you're pushing the correct branch

**Health check fails**
- Verify your app exposes the health endpoint
- Check logs: `/var/log/deployments/{app-name}/`
- Ensure the port matches config

**Dependencies fail to install**
- Check `requirements.txt` syntax
- Verify Python version compatibility
- Check VPS has internet access

## Development

Run tests:

```bash
pytest tests/ -v
```

## Roadmap

- [x] Week 1: Core deployment (Python)
- [ ] Week 2: Node.js and Docker support
- [ ] Week 3: Fleet monitoring dashboard
- [ ] Week 4: Polish and notifications

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README

- Installation instructions
- Quick start guide
- Configuration reference
- Health check examples
- Troubleshooting section"
```

---

## Task 10: Integration Test

**Files:**
- Create: `tests/test_integration.py`
- Create: `examples/flask-app/`

**Step 1: Create example Flask app**

Create `examples/flask-app/main.py`:
```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return {'message': 'Hello from Deployment Paradigm!'}

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

Create `examples/flask-app/requirements.txt`:
```txt
flask==3.0.0
```

Create `examples/flask-app/deploy.yml`:
```yaml
name: flask-example
type: python
healthCheck: /health
command: python main.py
```

**Step 2: Create integration test**

Create `tests/test_integration.py`:
```python
"""Integration tests for full deployment flow"""
import pytest
import tempfile
import subprocess
from pathlib import Path
import shutil
import time

@pytest.mark.integration
def test_full_deployment_flow():
    """
    Test complete deployment flow:
    1. Setup VPS structure
    2. Create git repo with Flask app
    3. Push to trigger deployment
    4. Verify health check passes
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Setup directories
        repos_dir = base / 'repos'
        deployments_dir = base / 'deployments'
        repos_dir.mkdir()
        deployments_dir.mkdir()

        # Create test app repo
        app_repo = base / 'app-repo'
        app_repo.mkdir()

        # Copy example Flask app
        example_dir = Path(__file__).parent.parent / 'examples' / 'flask-app'
        for file in ['main.py', 'requirements.txt', 'deploy.yml']:
            shutil.copy(example_dir / file, app_repo / file)

        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=app_repo, check=True)
        subprocess.run(['git', 'add', '.'], cwd=app_repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=app_repo, check=True)

        # Create bare repo (simulating VPS)
        bare_repo = repos_dir / 'flask-example.git'
        subprocess.run(['git', 'clone', '--bare', str(app_repo), str(bare_repo)], check=True)

        # Setup deployment structure
        deploy_dir = deployments_dir / 'flask-example'
        deploy_dir.mkdir()
        (deploy_dir / 'releases').mkdir()

        config_file = deploy_dir / 'config.yml'
        config_file.write_text('port: 8000\nmanager: systemd\nenv: test\n')

        # Import and run deployment
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from deploy_paradigm import execute_deployment

        # Get latest commit
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=bare_repo,
            capture_output=True,
            text=True,
            check=True
        )
        commit_sha = result.stdout.strip()

        # Mock health check (since we're not actually running Flask)
        from unittest.mock import patch
        with patch('deploy_paradigm.health_check') as mock_health:
            mock_health.return_value = True

            # Execute deployment
            success = execute_deployment(
                str(bare_repo),
                commit_sha,
                str(deploy_dir)
            )

            assert success is True

            # Verify release was created
            releases = list((deploy_dir / 'releases').iterdir())
            assert len(releases) == 1

            # Verify symlink
            current = deploy_dir / 'current'
            assert current.exists()
            assert current.is_symlink()

            # Verify venv was created
            release_dir = releases[0]
            assert (release_dir / 'venv').exists()

            # Verify Flask was installed
            pip_freeze = subprocess.run(
                [str(release_dir / 'venv' / 'bin' / 'pip'), 'freeze'],
                capture_output=True,
                text=True
            )
            assert 'Flask' in pip_freeze.stdout
```

**Step 3: Run integration test**

Run:
```bash
pytest tests/test_integration.py -v -m integration
```

Expected: Integration test PASS

**Step 4: Commit**

```bash
git add tests/test_integration.py examples/
git commit -m "test: add integration test with Flask example

- Create example Flask app with health endpoint
- Test full deployment flow from git push to health check
- Verify release structure and dependency installation"
```

---

## Final Steps

**Step 1: Run all tests**

Run:
```bash
pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Manual testing checklist**

Create `TESTING.md`:
```markdown
# Manual Testing Checklist

## Prerequisites
- [ ] VPS with Python 3.10+
- [ ] SSH access to VPS
- [ ] Test Flask app repository

## Test Setup
- [ ] Run install.sh on VPS
- [ ] Verify `/usr/local/bin/deploy-paradigm` exists
- [ ] Run `deploy-paradigm --help`

## Test Init
- [ ] Create new project directory
- [ ] Run `deploy-paradigm init`
- [ ] Verify `deploy.yml` created
- [ ] Edit deploy.yml with app details

## Test Setup
- [ ] Run `deploy-paradigm setup test-app git@github.com:you/test.git`
- [ ] Verify bare repo created in `/var/repos/`
- [ ] Verify deployment dir created in `/opt/deployments/`
- [ ] Verify systemd service created

## Test Deployment
- [ ] Add git remote: `git remote add production user@vps:/var/repos/test-app.git`
- [ ] Push: `git push production main`
- [ ] Verify deployment output shows progress
- [ ] Verify release created in `/opt/deployments/test-app/releases/`
- [ ] Verify symlink points to new release
- [ ] Verify health check passed

## Test Rollback
- [ ] Deploy broken code (health check fails)
- [ ] Verify automatic rollback
- [ ] Verify previous release is running

## Cleanup
- [ ] Remove test app
- [ ] Remove deployment directories
```

**Step 3: Update main commit**

```bash
git add TESTING.md
git commit -m "docs: add manual testing checklist"
```

**Step 4: Final verification**

Run:
```bash
# Verify structure
ls -la

# Expected files:
# - deploy_paradigm.py
# - requirements.txt
# - install.sh
# - README.md
# - TESTING.md
# - templates/
# - tests/
# - examples/
```

---

## Plan Complete

**Deliverables:**
✅ `deploy_paradigm.py` - Core CLI with init, setup, execute commands
✅ Python deployer with virtualenv + pip install
✅ Health check with retry logic
✅ Automatic rollback on failure
✅ Post-receive git hook
✅ Installation script
✅ Comprehensive tests
✅ Documentation

**Next Steps:**
1. Test on real VPS
2. Deploy example Flask app
3. Verify zero-downtime works
4. Move to Week 2 (Node.js + Docker support)
