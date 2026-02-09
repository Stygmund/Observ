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

        # Mock health check and systemctl (since we're not actually running Flask)
        from unittest.mock import patch, Mock

        # Save the original subprocess.run before patching
        original_subprocess_run = subprocess.run

        with patch('deploy_paradigm.health_check') as mock_health, \
             patch('deploy_paradigm.subprocess.run') as mock_subprocess:

            # Make subprocess.run work for real git commands but mock systemctl
            def subprocess_side_effect(*args, **kwargs):
                # If it's a systemctl command, mock it
                if args[0][0] == 'systemctl':
                    result = Mock()
                    result.returncode = 0
                    result.stdout = ''
                    result.stderr = ''
                    return result
                # Otherwise, call the original subprocess.run
                return original_subprocess_run(*args, **kwargs)

            mock_subprocess.side_effect = subprocess_side_effect
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
