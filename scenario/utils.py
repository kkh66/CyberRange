import docker
from docker import errors
import random
from datetime import datetime
from django.utils import timezone
import time


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
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Try to get existing container
                try:
                    container = self.client.containers.get(container_name)
                    container.reload()
                    
                    # If container exists but is not running, start it
                    if container.status != 'running':
                        container.start()
                        
                    # Wait for container to be ready
                    for _ in range(30):  # 30 seconds timeout
                        container.reload()
                        if container.status == 'running':
                            # Check if port mapping exists
                            if '3000/tcp' in container.ports:
                                return container.id, container.ports['3000/tcp'][0]['HostPort']
                            break
                        time.sleep(1)
                        
                    # If we got here without returning, port mapping failed
                    raise Exception("Container started but port mapping failed")
                    
                except docker.errors.NotFound:
                    # Container doesn't exist, create new one
                    port = self.get_available_port()
                    environment = {
                        'PYTHONUNBUFFERED': '1',
                        'PORT': '3000'  # Ensure container knows which port to use
                    }
                    
                    container = self.client.containers.run(
                        image=image_name,
                        name=container_name,
                        detach=True,
                        ports={'3000/tcp': port},
                        privileged=True,
                        environment=environment,
                        restart_policy={"Name": "unless-stopped"},
                    )
                    
                    # Wait for container to be ready
                    for _ in range(30):  # 30 seconds timeout
                        container.reload()
                        if container.status == 'running' and '3000/tcp' in container.ports:
                            return container.id, port
                        time.sleep(1)
                    
                    raise Exception("Container created but failed to start properly")
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    # Try to cleanup before retry
                    try:
                        container = self.client.containers.get(container_name)
                        container.remove(force=True)
                    except:
                        pass
                    time.sleep(2)  # Wait before retry
                    continue
                else:
                    raise Exception(f"Failed to start container after {max_retries} attempts: {last_error}")

    def get_container_status(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.reload()

            status = container.status
            state = container.attrs.get('State', {})
            started_at = state.get('StartedAt')
            is_paused = state.get('Paused', False)
            is_running = state.get('Running', False)
            
            # If container is paused, ensure status is correct
            if is_paused:
                status = 'paused'

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
                'container_status': {
                    'status': 'stopped',
                    'is_paused': False,
                    'is_running': False,
                    'started_at': None,
                    'runtime': 0
                },
                'progress_info': {
                    'progress': 0,
                    'level': None,
                    'logs': 'Container not found'
                }
            }
        except Exception as e:
            print(f"Error getting container status: {str(e)}")
            return {
                'status': 'error',
                'container_status': {
                    'status': 'error',
                    'is_paused': False,
                    'is_running': False,
                    'started_at': None,
                    'runtime': 0
                },
                'progress_info': {
                    'progress': 0,
                    'level': None,
                    'logs': str(e)
                }
            }

    def stop_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            
            container.reload()
            if container.status == 'exited' or not container.attrs['State']['Running']:
                raise Exception("Container is already stopped")
            
            container.stop()
            return True
            
        except Exception as e:
            error_message = str(e)
            if "Failed to stop container: " in error_message:
                error_message = error_message.replace("Failed to stop container: ", "")
            raise Exception(error_message)

    def pause_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            
            container.reload()
            if container.attrs['State']['Paused']:
                raise Exception("Container is already paused")
            
            container.pause()
            return True
            
        except Exception as e:
            error_message = str(e)
            if "Failed to pause container: " in error_message:
                error_message = error_message.replace("Failed to pause container: ", "")
            raise Exception(error_message)

    def unpause_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            
            container.reload()
            if not container.attrs['State']['Paused']:
                raise Exception("Container is not paused")
            
            container.unpause()
            return True
            
        except Exception as e:
            # Extract original error message to avoid duplicate wrapping
            error_message = str(e)
            if "Failed to unpause container: " in error_message:
                error_message = error_message.replace("Failed to unpause container: ", "")
            raise Exception(error_message)

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
