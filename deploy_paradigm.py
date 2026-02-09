#!/usr/bin/env python3
"""
Deployment Paradigm - Standardized deployment for VPS applications
"""
import click
import yaml
import sys
import shutil
import requests
import time
import subprocess
import os
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

TEMPLATES_DIR = Path(__file__).parent / 'templates'
REPOS_DIR = Path('/var/repos')
DEPLOYMENTS_DIR = Path('/opt/deployments')

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

    # Add default deployment strategy if not specified
    if 'deployment' not in config:
        config['deployment'] = {'strategy': 'simple'}
    elif 'strategy' not in config['deployment']:
        config['deployment']['strategy'] = 'simple'

    # Validate strategy
    valid_strategies = ['simple', 'blue-green', 'rolling']
    strategy = config['deployment']['strategy']
    if strategy not in valid_strategies:
        raise ConfigError(f"Invalid strategy: {strategy}. Must be one of {valid_strategies}")

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


class DockerDeployer(Deployer):
    """Deployer for Docker containerized applications"""

    def install_dependencies(self, release_dir):
        """
        Build Docker image from Dockerfile

        Args:
            release_dir: Path to release directory containing Dockerfile
        """
        release_dir = Path(release_dir)
        dockerfile = release_dir / 'Dockerfile'

        if not dockerfile.exists():
            raise RuntimeError('Dockerfile not found in release directory')

        # Build image with release directory as timestamp tag
        image_name = self.config['name']
        tag = release_dir.name  # timestamp from release directory
        image_tag = f"{image_name}:{tag}"

        click.echo(f'Building Docker image: {image_tag}...')
        result = subprocess.run(
            ['docker', 'build', '-t', image_tag, str(release_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f'Docker build failed: {result.stderr}')

        click.echo(click.style(f'✓ Image built: {image_tag}', fg='green'))

        # Also tag as 'latest'
        subprocess.run(
            ['docker', 'tag', image_tag, f"{image_name}:latest"],
            capture_output=True
        )

        # Cleanup old images (keep last 3)
        self._cleanup_old_images(image_name)

    def get_start_command(self):
        """Get Docker run command"""
        image_name = self.config['name']

        if 'command' in self.config:
            return self.config['command']

        # Default docker run command
        return f'docker run -d --name {image_name} -p 8000:8000 {image_name}:latest'

    def _cleanup_old_images(self, image_name):
        """Remove old Docker images, keeping last 3"""
        try:
            # List images for this app
            result = subprocess.run(
                ['docker', 'images', image_name, '--format', '{{.Tag}}'],
                capture_output=True,
                text=True,
                check=True
            )

            tags = [t.strip() for t in result.stdout.split('\n') if t.strip() and t != 'latest']
            tags.sort(reverse=True)  # Newest first

            # Remove old images (keep 3 most recent)
            for old_tag in tags[3:]:
                click.echo(f'Removing old image: {image_name}:{old_tag}')
                subprocess.run(
                    ['docker', 'rmi', f'{image_name}:{old_tag}'],
                    capture_output=True
                )
        except Exception as e:
            click.echo(click.style(f'Warning: Could not cleanup old images: {e}', fg='yellow'))


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
        'docker': DockerDeployer,
    }

    app_type = deploy_config['type']
    if app_type not in deployer_map:
        raise ConfigError(f'Unsupported app type: {app_type}')

    return deployer_map[app_type](deploy_config)

class DeploymentStrategy(ABC):
    """Base class for deployment strategies"""

    def __init__(self, deploy_config, vps_config, deployment_base):
        self.deploy_config = deploy_config
        self.vps_config = vps_config
        self.deployment_base = Path(deployment_base)

    @abstractmethod
    def deploy(self, git_dir, commit_sha):
        """Execute deployment"""
        pass

    @abstractmethod
    def rollback(self):
        """Rollback deployment"""
        pass

    # Protected helper methods (shared across strategies)

    def _create_release(self, git_dir, commit_sha):
        """Create timestamped release directory with code checkout"""
        timestamp = int(datetime.now().timestamp())
        releases_dir = self.deployment_base / 'releases'
        releases_dir.mkdir(exist_ok=True)

        release_dir = releases_dir / str(timestamp)
        click.echo(f'Creating release: {release_dir}')

        # Clone and checkout
        result = subprocess.run(
            ['git', 'clone', git_dir, str(release_dir)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f'Failed to clone: {result.stderr}')

        subprocess.run(
            ['git', '-C', str(release_dir), 'checkout', commit_sha],
            check=True, capture_output=True
        )

        click.echo(click.style('✓ Release created', fg='green'))
        return release_dir

    def _install_dependencies(self, code_dir):
        """Install dependencies using appropriate deployer"""
        deployer = get_deployer(self.deploy_config)
        deployer.install_dependencies(code_dir)

    def _copy_env_file(self, target_dir):
        """Copy environment-specific .env file to target directory"""
        env_file = self.deployment_base / f".env.{self.vps_config.get('env', 'production')}"
        if env_file.exists():
            shutil.copy(env_file, target_dir / '.env')

    def _run_hook(self, hook_name, working_dir):
        """Run deployment hook script"""
        if 'hooks' in self.deploy_config and hook_name in self.deploy_config['hooks']:
            hook_script = working_dir / self.deploy_config['hooks'][hook_name]
            if hook_script.exists():
                click.echo(f'Running {hook_name} hook...')
                result = subprocess.run([str(hook_script)], cwd=working_dir)
                if result.returncode != 0:
                    raise RuntimeError(f'{hook_name} hook failed')

    def _cleanup_old_releases(self, releases_dir):
        """Keep only last 3 releases"""
        releases = sorted(releases_dir.iterdir(), key=lambda p: p.name)
        if len(releases) > 3:
            for old_release in releases[:-3]:
                click.echo(f'Cleaning up: {old_release.name}')
                shutil.rmtree(old_release)


class SimpleStrategy(DeploymentStrategy):
    """Simple deployment: symlink swap with health check"""

    def deploy(self, git_dir, commit_sha):
        """Simple deployment: create release, swap symlink, health check"""
        click.echo('Using simple deployment strategy')

        # Create release using base class helper
        release_dir = self._create_release(git_dir, commit_sha)
        releases_dir = release_dir.parent

        # Install dependencies and copy env
        self._install_dependencies(release_dir)
        self._copy_env_file(release_dir)

        # Pre-deploy hooks
        self._run_hook('preDeploy', release_dir)

        # Swap symlink
        current_link = self.deployment_base / 'current'
        previous_link = self.deployment_base / 'previous'

        if current_link.exists():
            if previous_link.exists():
                previous_link.unlink()
            current_link.rename(previous_link)

        current_link.symlink_to(release_dir)
        click.echo(click.style('✓ Symlink updated', fg='green'))

        # Reload service
        self._reload_service()

        # Health check
        if not self._health_check():
            self.rollback()
            raise RuntimeError('Health check failed')

        # Post-deploy hooks
        self._run_hook('postDeploy', release_dir)

        # Cleanup old releases
        self._cleanup_old_releases(releases_dir)

        return True

    def rollback(self):
        """Rollback to previous release"""
        click.echo(click.style('Rolling back...', fg='yellow'))

        previous_link = self.deployment_base / 'previous'
        current_link = self.deployment_base / 'current'

        if previous_link.exists():
            current_link.unlink()
            previous_link.rename(current_link)
            self._reload_service()
            click.echo(click.style('✓ Rolled back', fg='green'))
        else:
            click.echo(click.style('No previous release to rollback to', fg='red'))

    def _reload_service(self):
        """Reload the service"""
        app_name = self.deploy_config['name']
        if self.vps_config['manager'] == 'systemd':
            subprocess.run(['systemctl', 'reload', app_name], capture_output=True)

    def _health_check(self):
        """Run health check"""
        click.echo('\nWaiting 10s for startup...')
        time.sleep(10)

        health_url = f"http://localhost:{self.vps_config['port']}{self.deploy_config['healthCheck']}"
        return health_check(health_url, retries=3, delay=5)


class BlueGreenStrategy(DeploymentStrategy):
    """Blue-green deployment: deploy to inactive environment, test, switch"""

    def deploy(self, git_dir, commit_sha):
        """Deploy to inactive environment and switch"""
        click.echo('Using blue-green deployment strategy')

        # Determine active/inactive
        current_link = self.deployment_base / 'current'

        if current_link.exists():
            active_env = current_link.resolve().name
            inactive_env = 'green' if active_env == 'blue' else 'blue'
        else:
            active_env = None
            inactive_env = 'blue'

        click.echo(f'Active: {active_env or "none"} -> Deploying to: {inactive_env}')

        # Deploy to inactive
        inactive_dir = self.deployment_base / inactive_env
        inactive_dir.mkdir(exist_ok=True)

        code_dir = inactive_dir / 'code'
        if code_dir.exists():
            shutil.rmtree(code_dir)

        # Clone code
        subprocess.run(
            ['git', 'clone', git_dir, str(code_dir)],
            check=True, capture_output=True
        )
        subprocess.run(
            ['git', '-C', str(code_dir), 'checkout', commit_sha],
            check=True, capture_output=True
        )

        click.echo(click.style('✓ Code deployed to inactive environment', fg='green'))

        # Install dependencies
        deployer = get_deployer(self.deploy_config)
        deployer.install_dependencies(code_dir)

        # Copy env
        env_file = self.deployment_base / f".env.{self.vps_config.get('env', 'production')}"
        if env_file.exists():
            shutil.copy(env_file, code_dir / '.env')

        # Pre-deploy hooks (migrations)
        self._run_hook('preDeploy', code_dir)

        # Start inactive service
        inactive_port = 8001 if inactive_env == 'green' else 8000
        self._start_service(inactive_env, inactive_port, code_dir)

        # Health check inactive
        if not self._health_check_environment(inactive_env, inactive_port):
            self._stop_service(inactive_env)
            raise RuntimeError(f'{inactive_env} environment health check failed')

        # Run smoke tests
        if not self._run_smoke_tests(inactive_port):
            self._stop_service(inactive_env)
            raise RuntimeError('Smoke tests failed')

        # Switch to inactive
        click.echo(f'\n✓ {inactive_env.capitalize()} healthy, switching...')

        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to(inactive_env)

        # Update proxy
        active_port = 8000 if inactive_env == 'green' else 8001
        self._update_proxy(inactive_port)

        click.echo(click.style(f'✓ Switched to {inactive_env}', fg='green'))

        # Post-deploy hooks
        self._run_hook('postDeploy', code_dir)

        # Stop old environment (unless keepInactive)
        if active_env and not self.deploy_config['deployment'].get('keepInactive', False):
            self._stop_service(active_env)

        return True

    def rollback(self):
        """Switch back to previous environment"""
        current_link = self.deployment_base / 'current'

        if not current_link.exists():
            click.echo(click.style('No active environment', fg='red'))
            return

        active_env = current_link.resolve().name
        inactive_env = 'green' if active_env == 'blue' else 'blue'

        click.echo(f'Rolling back from {active_env} to {inactive_env}')

        # Switch symlink
        current_link.unlink()
        current_link.symlink_to(inactive_env)

        # Switch ports
        inactive_port = 8001 if inactive_env == 'green' else 8000
        self._update_proxy(inactive_port)

        # Start old environment if not running
        self._start_service(inactive_env, inactive_port, self.deployment_base / inactive_env / 'code')

        click.echo(click.style('✓ Rolled back', fg='green'))

    def _start_service(self, env_name, port, code_dir):
        """Start service for specific environment"""
        app_name = f"{self.deploy_config['name']}-{env_name}"

        if self.vps_config['manager'] == 'systemd':
            # Create environment-specific service file
            service_content = f"""[Unit]
Description={self.deploy_config['name']} {env_name} environment
After=network.target

[Service]
Type=simple
WorkingDirectory={code_dir}
Environment="PORT={port}"
ExecStart={code_dir}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port {port}
Restart=always

[Install]
WantedBy=multi-user.target
"""
            service_file = Path(f'/etc/systemd/system/{app_name}.service')
            try:
                service_file.write_text(service_content)
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
                subprocess.run(['systemctl', 'start', app_name], check=True)
                click.echo(click.style(f'✓ Started {env_name} service', fg='green'))
            except Exception as e:
                click.echo(click.style(f'Warning: Could not start systemd service: {e}', fg='yellow'))

    def _stop_service(self, env_name):
        """Stop service for specific environment"""
        app_name = f"{self.deploy_config['name']}-{env_name}"
        subprocess.run(['systemctl', 'stop', app_name], capture_output=True)

    def _health_check_environment(self, env_name, port):
        """Health check specific environment"""
        click.echo(f'\nTesting {env_name} environment on port {port}...')
        time.sleep(10)

        health_url = f"http://localhost:{port}{self.deploy_config['healthCheck']}"

        # Multiple health checks
        for i in range(5):
            if not health_check(health_url, retries=1, delay=0):
                return False
            time.sleep(2)

        return True

    def _run_smoke_tests(self, port):
        """Run smoke tests if configured"""
        if 'smokeTests' not in self.deploy_config:
            return True

        click.echo('Running smoke tests...')

        for test in self.deploy_config['smokeTests']:
            if 'endpoint' in test:
                url = f"http://localhost:{port}{test['endpoint']}"
                method = test.get('method', 'GET')
                expected_status = test.get('expectedStatus', 200)

                try:
                    response = requests.request(method, url, timeout=10)
                    if response.status_code != expected_status:
                        click.echo(click.style(f'✗ Smoke test failed: {url} returned {response.status_code}', fg='red'))
                        return False

                    if 'expectedBody' in test:
                        if test['expectedBody'] not in response.text:
                            click.echo(click.style(f'✗ Smoke test failed: unexpected response body', fg='red'))
                            return False

                    click.echo(click.style(f'✓ {url}', fg='green'))
                except Exception as e:
                    click.echo(click.style(f'✗ Smoke test failed: {e}', fg='red'))
                    return False

            elif 'script' in test:
                script_path = self.deployment_base / test['script']
                if script_path.exists():
                    result = subprocess.run([str(script_path)])
                    if result.returncode != 0:
                        click.echo(click.style(f'✗ Smoke test script failed', fg='red'))
                        return False
                    click.echo(click.style(f'✓ {script_path.name}', fg='green'))

        return True

    def _update_proxy(self, port):
        """Update proxy to point to new port"""
        # This would update nginx config
        # For now, just log it
        click.echo(f'Note: Update your proxy/load balancer to port {port}')


class RollingStrategy(DeploymentStrategy):
    """Rolling deployment: gradual instance-by-instance update"""

    def deploy(self, git_dir, commit_sha):
        """Deploy with rolling restart"""
        click.echo('Using rolling deployment strategy')

        # Create release using base class helper
        release_dir = self._create_release(git_dir, commit_sha)
        releases_dir = release_dir.parent

        # Install dependencies and copy env
        self._install_dependencies(release_dir)
        self._copy_env_file(release_dir)

        # Pre-deploy hooks
        self._run_hook('preDeploy', release_dir)

        # Update symlink
        current_link = self.deployment_base / 'current'
        previous_link = self.deployment_base / 'previous'

        if current_link.exists():
            if previous_link.exists():
                previous_link.unlink()
            current_link.rename(previous_link)

        current_link.symlink_to(release_dir)
        click.echo(click.style('✓ Symlink updated', fg='green'))

        # Rolling restart (process manager handles instance-by-instance)
        self._rolling_restart()

        # Wait for stabilization
        batch_delay = self.deploy_config['deployment'].get('batchDelay', 10)
        click.echo(f'\nWaiting {batch_delay}s for stabilization...')
        time.sleep(batch_delay)

        # Health check
        if not self._health_check():
            self.rollback()
            raise RuntimeError('Health check failed after rolling deployment')

        # Post-deploy hooks
        self._run_hook('postDeploy', release_dir)

        # Cleanup old releases
        self._cleanup_old_releases(releases_dir)

        click.echo(click.style('✓ Rolling deployment complete', fg='green'))
        return True

    def rollback(self):
        """Rollback to previous release"""
        click.echo(click.style('Rolling back...', fg='yellow'))

        previous_link = self.deployment_base / 'previous'
        current_link = self.deployment_base / 'current'

        if previous_link.exists():
            current_link.unlink()
            previous_link.rename(current_link)
            self._rolling_restart()
            click.echo(click.style('✓ Rolled back', fg='green'))
        else:
            click.echo(click.style('No previous release to rollback to', fg='red'))

    def _rolling_restart(self):
        """Perform rolling restart of service"""
        app_name = self.deploy_config['name']
        manager = self.vps_config['manager']

        if manager == 'pm2':
            # PM2 reload does rolling restart automatically
            click.echo('Rolling restart with PM2...')
            result = subprocess.run(
                ['pm2', 'reload', app_name, '--update-env'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                click.echo(click.style('✓ PM2 rolling restart complete', fg='green'))
            else:
                raise RuntimeError(f'PM2 reload failed: {result.stderr}')

        elif manager == 'systemd':
            # Systemd reload (graceful restart)
            click.echo('Reloading systemd service...')
            result = subprocess.run(
                ['systemctl', 'reload-or-restart', app_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                click.echo(click.style('✓ Systemd reload complete', fg='green'))
            else:
                # Try regular restart as fallback
                subprocess.run(['systemctl', 'restart', app_name], check=True)
                click.echo(click.style('✓ Systemd restart complete', fg='green'))

    def _health_check(self):
        """Run health check"""
        health_url = f"http://localhost:{self.vps_config['port']}{self.deploy_config['healthCheck']}"
        return health_check(health_url, retries=3, delay=5)


def get_deployment_strategy(deploy_config, vps_config, deployment_base):
    """Factory to get deployment strategy"""
    strategy_map = {
        'simple': SimpleStrategy,
        'blue-green': BlueGreenStrategy,
        'rolling': RollingStrategy,
    }

    strategy_name = deploy_config['deployment']['strategy']
    strategy_class = strategy_map.get(strategy_name)

    if not strategy_class:
        raise ConfigError(f'Unknown strategy: {strategy_name}')

    return strategy_class(deploy_config, vps_config, deployment_base)

def execute_deployment(git_dir, commit_sha, deployment_base_dir):
    """
    Execute deployment using configured strategy

    Args:
        git_dir: Path to git repository
        commit_sha: Commit SHA to deploy
        deployment_base_dir: Base deployment directory (e.g., /opt/deployments/app-name)

    Returns:
        bool: True if deployment succeeded, False otherwise
    """
    deployment_base = Path(deployment_base_dir)

    click.echo(f'\n=== Deploying commit {commit_sha[:7]} ===\n')

    # Extract deploy.yml from commit
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

    # Get and execute deployment strategy
    try:
        strategy = get_deployment_strategy(deploy_config, vps_config, deployment_base)
        strategy.deploy(git_dir, commit_sha)
        click.echo(click.style('\n✓ Deployment successful!', fg='green'))
        return True
    except Exception as e:
        click.echo(click.style(f'\n❌ Deployment failed: {e}', fg='red'))
        return False

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Deployment Paradigm CLI"""
    pass

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
    hooks_dir.mkdir(exist_ok=True)  # Ensure hooks directory exists
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
        # Ask about monitoring
        enable_monitoring = click.confirm('\nEnable observ monitoring for this application?', default=False)

        config_content = f"""# VPS Configuration for {app_name}
port: {port}
manager: {manager}
env: {env}
"""

        if enable_monitoring:
            # Prompt for PostgreSQL URL
            postgres_url = click.prompt(
                'PostgreSQL connection string (or press Enter to use $OBSERV_DB_URL env var)',
                default='${OBSERV_DB_URL}',
                show_default=False
            )

            config_content += f"""
# Monitoring configuration
monitoring:
  enabled: true
  postgres_url: {postgres_url}
  collection_interval: 60
  health_checks:
    - url: http://localhost:{port}/health
      interval: 30
      timeout: 5
  log_files:
    - /opt/deployments/{app_name}/current/logs/app.log
"""

            # If using env var, remind user to set it
            if '${' in postgres_url:
                click.echo(click.style(f'\n⚠ Remember to set OBSERV_DB_URL in {deploy_dir}/.env.{env}', fg='yellow'))

        config_file.write_text(config_content)
        click.echo(click.style('✓ VPS config created', fg='green'))

        # Create postDeploy hook for monitoring if enabled
        if enable_monitoring:
            hooks_dir = deploy_dir / 'hooks'
            hooks_dir.mkdir(exist_ok=True)
            post_deploy_hook = hooks_dir / 'postDeploy'

            # Reference to setup-monitoring.sh script
            setup_script = TEMPLATES_DIR / 'setup-monitoring.sh'
            if setup_script.exists():
                hook_content = f"""#!/bin/bash
# postDeploy hook - setup monitoring agent
{setup_script} {app_name}
"""
                post_deploy_hook.write_text(hook_content)
                post_deploy_hook.chmod(0o755)
                click.echo(click.style('✓ postDeploy hook created for monitoring', fg='green'))
            else:
                click.echo(click.style(f'⚠ setup-monitoring.sh template not found', fg='yellow'))

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
            except (PermissionError, FileNotFoundError, OSError):
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

if __name__ == '__main__':
    cli()
