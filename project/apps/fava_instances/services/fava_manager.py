# Beancount-Trans-Backend/project/apps/fava_instances/services/fava_manager.py
import docker
import time
from django.conf import settings


class FavaContainerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.network = settings.TRAEFIK_NETWORK
        self.fava_image = settings.FAVA_IMAGE

    def start_container(self, user, bean_file_path, instance):
        # 生成唯一容器名称
        container_name = f"fava-{user.username}-{int(time.time())}"
        
        # 创建容器
        container = self.client.containers.run(
            image=self.fava_image,
            name=container_name,
            volumes={bean_file_path: {'bind': '/Assets', 'mode': 'rw'}},
            network=self.network,
            ports={'5000/tcp': None},
            detach=True,
            environment={
                "PYTHONUNBUFFERED": "1",
                "BEANCOUNT_FILE": "/Assets/main.bean",
                "FAVA_PREFIX": f"/{instance.uuid}",
            },
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.fava-{user.username}.rule": f"Host(`trans.localhost`) && PathPrefix(`/{instance.uuid}`)",
                f"traefik.http.routers.fava-{user.username}.entrypoints": "web",
                f"traefik.http.services.fava-{user.username}.loadbalancer.server.port": "5000",
                f"traefik.http.middlewares.fava-{user.username}-stripprefix.stripprefix.prefixes": "/",
                f"traefik.http.routers.fava-{user.username}.middlewares": f"fava-{user.username}-stripprefix@docker",
            }
        )
        return container.id, container_name

    def stop_container(self, container_id):
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
            return True
        except docker.errors.NotFound:
            return False
