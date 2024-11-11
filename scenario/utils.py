import docker
from docker import errors
import random


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
        for attempt in range(2):
            try:
                container = self.client.containers.get(container_name)
                return container.id, container.ports['3000/tcp'][0]['HostPort']
            except docker.errors.NotFound:
                try:
                    port = self.get_available_port()
                    container = self.client.containers.run(
                        image=image_name,
                        name=container_name,
                        detach=True,
                        ports={'3000/tcp': port},
                        privileged=True,
                        restart_policy={"Name": "unless-stopped"}
                    )
                    return container.id, port
                except Exception as e:
                    if attempt == 1:
                        raise Exception(f"Failed to create container after 2 attempts: {str(e)}")
                    continue

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
            container_info = container.attrs
            return container_info
        except Exception as e:
            print(f"Error getting container info: {e}")
            raise

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

    def start_test_container(self, image_name, container_name, user_id):
        """
        启动测试容器，如果容器不存在则重新创建
        """
        try:
            # 先尝试获取已存在的容器
            try:
                container = self.client.containers.get(container_name)
                return container.id, container.ports['3000/tcp'][0]['HostPort']
            except docker.errors.NotFound:
                # 如果容器不存在，创建新容器
                port = self.get_available_port()
                environment = {
                    'CONTAINER_ID': container_name,
                    'USER_ID': str(user_id),
                    'PYTHONUNBUFFERED': '1'
                }
                container = self.client.containers.run(
                    image=image_name,
                    name=container_name,
                    detach=True,
                    environment=environment,
                    ports={'3000/tcp': port},
                    restart_policy={"Name": "unless-stopped"}
                )
                return container.id, port

        except Exception as e:
            raise Exception(f"Failed to start test container: {str(e)}")

    def get_container_logs(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(
                stdout=True,
                stderr=True,
                stream=False,
                tail=100
            ).decode('utf-8')

            # 查找特定的日志信息
            for line in logs.split('\n'):
                if "Command executed: chmod" in line:
                    return "Command executed: chmod"

            return "No chmod command detected"

        except Exception as e:
            raise Exception(f"Failed to get container logs: {str(e)}")
