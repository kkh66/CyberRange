import docker
from docker import errors
import random
from datetime import datetime
from django.utils import timezone


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.MIN_PORT = 30000
        self.MAX_PORT = 50000

    def get_available_port(self):
        used_ports = set()
        containers = self.client.containers.list()
        for container in containers:
            ports = container.attrs['HostConfig']['PortBindings'] or {}
            for port_bindings in ports.values():
                for binding in port_bindings:
                    if binding and 'HostPort' in binding:
                        used_ports.add(int(binding['HostPort']))
        while True:
            port = random.randint(self.MIN_PORT, self.MAX_PORT)
            if port not in used_ports:
                return port

    def start_container(self, image_name, container_name):
        for attempt in range(2):
            try:
                container = self.client.containers.get(container_name)
                container.reload()
                if container.status != 'running':
                    container.start()
                if '3000/tcp' not in container.ports:
                    raise Exception("Container exists but has no port mapping")
                return container.id, container.ports['3000/tcp'][0]['HostPort']
            except docker.errors.NotFound:
                try:
                    port = self.get_available_port()
                    environment = {'PYTHONUNBUFFERED': '1'}
                    container = self.client.containers.run(
                        image=image_name,
                        name=container_name,
                        detach=True,
                        ports={'3000/tcp': port},
                        privileged=True,
                        environment=environment,
                        restart_policy={"Name": "unless-stopped"},
                    )
                    return container.id, port
                except Exception as e:
                    if attempt == 1:
                        raise Exception(f"Failed to create container after 2 attempts: {str(e)}")
                    continue

    def get_container_status(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.reload()

            status = container.status
            state = container.attrs.get('State', {})
            started_at = state.get('StartedAt')
            is_paused = state.get('Paused', False)
            is_running = state.get('Running', False)
            
            runtime = 0
            if started_at and is_running and not is_paused:
                started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                runtime = int((timezone.now() - started_time).total_seconds())
            
            progress = 0
            level = None
            logs = ''
            try:
                logs = container.logs(tail=100).decode('utf-8')
                for line in logs.split('\n'):
                    if "Progress:" in line:
                        try:
                            progress_str = line.split("Progress:")[1].strip().replace('%', '')
                            progress = int(progress_str)
                        except (IndexError, ValueError):
                            continue
                    elif "Level:" in line:
                        try:
                            level = line.split("Level:")[1].strip()
                        except (IndexError, ValueError):
                            continue
            except Exception as e:
                print(f"Error reading logs: {e}")

            return {
                'status': 'success',
                'container_status': {
                    'status': status,
                    'is_paused': is_paused,
                    'is_running': is_running,
                    'started_at': started_at,
                    'runtime': runtime
                },
                'progress_info': {
                    'progress': progress,
                    'level': level,
                    'logs': logs
                }
            }

        except docker.errors.NotFound:
            return {
                'status': 'error',
                'message': 'Container not found'
            }
        except Exception as e:
            print(f"Error getting container status: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def stop_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            return True
        except Exception as e:
            raise Exception(f"Failed to stop container: {str(e)}")

    def pause_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.pause()
            return True
        except Exception as e:
            raise Exception(f"Failed to pause container: {str(e)}")

    def unpause_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            return True
        except Exception as e:
            raise Exception(f"Failed to unpause container: {str(e)}")

    def restart_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.restart()
            return True
        except Exception as e:
            raise Exception(f"Failed to restart container: {str(e)}")

    def remove_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.remove()
            return True
        except Exception as e:
            raise Exception(f"Failed to remove container: {str(e)}")
