# Beancount-Trans-Backend/project/apps/fava_instances/services/fava_manager.py
import os
import docker
import time
import logging
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class FavaContainerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.network = settings.TRAEFIK_NETWORK
        self.fava_image = settings.FAVA_IMAGE
        self.base_url = settings.BASE_URL
        self.certresolver = settings.CERTRESOLVER

    def _is_container_ready(self, container_name, container_host_port):
        try:
            import requests
            response = requests.get(
                f"http://{container_name}:{container_host_port}",
                timeout=0.3
            )
            return response.status_code == 200
        except:
            return False


    def start_container(self, user, bean_file_path, instance):
        # 生成唯一容器名称
        container_name = f"fava-{user.username}-{int(time.time())}"

        # 创建容器
        container = self.client.containers.run(
            image=self.fava_image,
            name=container_name,
            volumes={bean_file_path: {'bind': '/Assets', 'mode': 'rw'}},
            network=self.network,
            # ports={'5000/tcp': None},
            detach=True,
            environment={
                "PYTHONUNBUFFERED": "1",
                "BEANCOUNT_FILE": "/Assets/main.bean",
                "FAVA_PREFIX": f"/{instance.uuid}",
            },
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.fava-{user.username}.rule": f"Host(`{self.base_url}`) && PathPrefix(`/{instance.uuid}`)",
                f"traefik.http.routers.fava-{user.username}.entrypoints": "websecure",
                f"traefik.http.routers.fava-{user.username}.tls":"true",
                f"traefik.http.routers.fava-{user.username}.tls.certresolver":f"{self.certresolver}",
                f"traefik.http.services.fava-{user.username}.loadbalancer.server.port": "5000",
                f"traefik.http.middlewares.fava-{user.username}-stripprefix.stripprefix.prefixes": "/",
                f"traefik.http.routers.fava-{user.username}.middlewares": f"fava-{user.username}-stripprefix@docker",
            }
        )
        max_retries = 20
        for _ in range(max_retries):
            time.sleep(0.5)
            container.reload()

            if container.status == 'running':
                if self._is_container_ready(container_name, 5000):
                    return container.id, container_name

        # 超时处理
        container.stop()
        container.remove()
        raise Exception("Fava container failed to start in time")

    def check_container_exists(self, container_id):
        """
        检查容器是否真实存在
        
        Args:
            container_id: 容器ID
            
        Returns:
            bool: 容器存在返回 True，不存在返回 False
        """
        if not container_id:
            return False
        try:
            container = self.client.containers.get(container_id)
            container.reload()
            return True
        except docker.errors.NotFound:
            return False
        except Exception as e:
            logger.warning(f"检查容器 {container_id} 时出错: {str(e)}")
            return False

    def verify_and_cleanup_instance(self, instance):
        """
        验证实例的容器是否存在，不存在则清理数据库记录
        
        Args:
            instance: FavaInstance 实例
            
        Returns:
            bool: 容器存在返回 True，不存在且已清理返回 False
        """
        if not instance.container_id:
            # 如果没有 container_id，直接清理数据库记录
            instance.container_id = ''
            instance.container_name = ''
            instance.status = 'stopped'
            instance.save()
            logger.info(f"实例 {instance.uuid} 没有 container_id，已清理数据库记录")
            return False
        
        if self.check_container_exists(instance.container_id):
            return True
        else:
            # 容器不存在，清理数据库记录
            logger.info(f"实例 {instance.uuid} 的容器 {instance.container_id} 不存在，清理数据库记录")
            instance.container_id = ''
            instance.container_name = ''
            instance.status = 'stopped'
            instance.save()
            return False

    def cleanup_user_containers(self, user):
        """
        清理当前用户的所有旧容器和实例记录
        
        该方法会：
        1. 查找用户的所有非 stopped 状态的实例
        2. 验证每个实例的容器是否存在
        3. 如果容器存在，停止并删除容器
        4. 清理数据库记录（清空 container_id 和 container_name，设置状态为 stopped）
        
        Args:
            user: User 实例
            
        Returns:
            int: 清理的实例数量
        """
        from project.apps.fava_instances.models import FavaInstance
        
        # 查找用户的所有非 stopped 状态的实例
        old_instances = FavaInstance.objects.filter(
            owner=user
        ).exclude(status='stopped')
        
        cleaned_count = 0
        
        for instance in old_instances:
            try:
                logger.info(f"清理用户 {user.username} 的实例 {instance.uuid} (状态: {instance.status})")
                
                # 如果实例有 container_id，尝试停止容器
                if instance.container_id:
                    if self.check_container_exists(instance.container_id):
                        # 容器存在，停止并删除
                        try:
                            container = self.client.containers.get(instance.container_id)
                            container.stop(timeout=5)
                            container.remove()
                            logger.info(f"已停止并删除容器 {instance.container_id}")
                        except docker.errors.NotFound:
                            logger.warning(f"容器 {instance.container_id} 不存在，跳过停止操作")
                        except Exception as e:
                            logger.error(f"停止容器 {instance.container_id} 时出错: {str(e)}")
                    else:
                        logger.info(f"容器 {instance.container_id} 不存在，跳过停止操作")
                
                # 清理数据库记录
                instance.container_id = ''
                instance.container_name = ''
                instance.status = 'stopped'
                instance.save()
                cleaned_count += 1
                logger.info(f"已清理实例 {instance.uuid} 的数据库记录")
                
            except Exception as e:
                logger.error(f"清理实例 {instance.uuid} 时出错: {str(e)}")
                # 即使出错，也尝试清理数据库记录
                try:
                    instance.container_id = ''
                    instance.container_name = ''
                    instance.status = 'error'
                    instance.save()
                except:
                    pass
        
        logger.info(f"用户 {user.username} 共清理了 {cleaned_count} 个旧实例")
        return cleaned_count

    def _wait_for_running(self, instance, timeout=10, interval=0.5):
        """等待另一进程把实例切到 running。超时或失败返回 None。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            instance.refresh_from_db()
            if instance.status == 'running':
                if self.verify_and_cleanup_instance(instance):
                    return instance
                return None
            if instance.status in ('error', 'stopped', 'stopping'):
                return None
            time.sleep(interval)
        logger.warning(f"等待实例 {instance.uuid} 启动超时")
        return None

    def ensure_running(self, user, *, touch_last_accessed=False):
        """
        确保用户有一个真实运行中的 Fava 容器（幂等）。

        登录预热与打开报表走同一入口，避免并发各起一个容器。
        touch_last_accessed=True 时刷新 last_accessed（用户打开 Fava）；
        预热已有容器时不刷新，闲置回收仍按 FAVA_CONTAINER_LIFETIME。
        """
        from project.apps.fava_instances.models import FavaInstance
        from project.utils.file import BeanFileManager

        if settings.FAVA_DEPLOY_MODE == 'static':
            return None

        def _touch(inst):
            if touch_last_accessed:
                inst.save()
            return inst

        running = FavaInstance.objects.filter(owner=user, status='running').first()
        if running and self.verify_and_cleanup_instance(running):
            logger.info(f"用户 {user.username} 的实例 {running.uuid} 容器运行正常")
            return _touch(running)

        with transaction.atomic():
            locked_running = (
                FavaInstance.objects.select_for_update()
                .filter(owner=user, status='running')
                .first()
            )
            locked_starting = (
                FavaInstance.objects.select_for_update()
                .filter(owner=user, status='starting')
                .first()
            )
            should_start = False
            instance = None
            if locked_running:
                instance = locked_running
            elif locked_starting:
                instance = locked_starting
            else:
                logger.info(f"清理用户 {user.username} 的所有旧实例")
                self.cleanup_user_containers(user)
                instance = FavaInstance(owner=user, status='starting')
                instance.save()
                should_start = True
                logger.info(f"为用户 {user.username} 创建新实例 {instance.uuid}")

        if instance.status == 'running':
            if self.verify_and_cleanup_instance(instance):
                return _touch(instance)
            should_start = True

        if instance.status == 'starting' and not should_start:
            waited = self._wait_for_running(instance)
            if waited:
                logger.info(f"用户 {user.username} 的实例 {waited.uuid} 已由其他进程启动")
                return _touch(waited)
            should_start = True

        if should_start:
            if instance.status != 'starting' or instance.container_id:
                logger.info(f"清理用户 {user.username} 的所有旧实例")
                self.cleanup_user_containers(user)
                instance = FavaInstance(owner=user, status='starting')
                instance.save()
                logger.info(f"为用户 {user.username} 创建新实例 {instance.uuid}")

            user_assets_path = BeanFileManager.get_user_assets_path(user)
            bean_file = os.path.join(settings.ASSETS_HOST_PATH, os.path.basename(user_assets_path))
            try:
                container_id, container_name = self.start_container(user, bean_file, instance)
                instance.container_id = container_id
                instance.container_name = container_name
                instance.status = 'running'
                instance.save()
                logger.info(f"用户 {user.username} 的实例 {instance.uuid} 容器启动成功")
                return instance
            except Exception:
                logger.exception(f"用户 {user.username} 的实例 {instance.uuid} 容器启动失败")
                instance.container_id = ''
                instance.container_name = ''
                instance.status = 'error'
                instance.save()
                raise

        raise Exception("Fava container failed to start")

    def stop_container(self, container_id):
        """
        停止并删除容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            bool: 成功停止并删除返回 True，容器不存在返回 False
        """
        if not container_id:
            return False
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
            logger.info(f"已停止并删除容器 {container_id}")
            return True
        except docker.errors.NotFound:
            logger.info(f"容器 {container_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"停止容器 {container_id} 时出错: {str(e)}")
            return False

