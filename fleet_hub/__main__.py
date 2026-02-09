"""
Allow running Fleet Hub as a module: python -m fleet_hub
"""
import click
from fleet_hub.api import run_server


@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8080, help='Port to bind to')
def main(host: str, port: int):
    """Run the Fleet Hub monitoring dashboard"""
    click.echo(f'Starting Fleet Hub on {host}:{port}')
    click.echo(f'Access the dashboard at http://localhost:{port}')
    click.echo(f'API documentation at http://localhost:{port}/docs')
    run_server(host=host, port=port)


if __name__ == '__main__':
    main()
