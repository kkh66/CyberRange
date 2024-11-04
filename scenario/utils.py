import docker
import random
from django.conf import settings


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.MIN_PORT = 30000
        self.MAX_PORT = 50000

    def get_available_port(self):
        used_ports = set()
        containers = self.client.containers.list()

        # get the used ports
        for container in containers:
            ports = container.attrs['HostConfig']['PortBindings'] or {}
            for port_bindings in ports.values():
                for binding in port_bindings:
                    if binding and 'HostPort' in binding:
                        used_ports.add(int(binding['HostPort']))

        # find an available port
        while True:
            port = random.randint(self.MIN_PORT, self.MAX_PORT)
            if port not in used_ports:
                return port

    def start_container(self, image_name, container_name):
        try:
            # 检查是否已存在同名容器
            try:
                old_container = self.client.containers.get(container_name)
                old_container.remove(force=True)
            except docker.errors.NotFound:
                pass

            port = self.get_available_port()

            container = self.client.containers.run(
                image=image_name,
                name=container_name,
                detach=True,
                ports={'3000/tcp': port},
                restart_policy={"Name": "unless-stopped"}
            )

            return container.id, port

        except Exception as e:
            raise Exception(f"Failed to start container: {str(e)}")

    def stop_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            return True
        except Exception as e:
            raise Exception(f"Failed to stop container: {str(e)}")

    def get_container_info(self, container_id):
        try:
            container = self.client.containers.get(container_id)

            return {
                'id': container.id[:12],
                'status': container.status,
                'name': container.name,
                'created': container.attrs['Created'],
                'ports': container.attrs['HostConfig']['PortBindings']
            }
        except Exception as e:
            raise Exception(f"Failed to get container info: {str(e)}")

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
