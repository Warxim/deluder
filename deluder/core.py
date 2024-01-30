import copy
import frida
import frida
import time
import psutil

from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Set, Union, List

from deluder.common import *
from deluder.interceptor import MessageInterceptor
from deluder.log import logger, set_debug_level
from deluder.router import MessageRouter
from deluder.script import load_scripts
from deluder.interceptors import AVAILABLE_INTERCEPTORS, INTERCEPTORS_REGISTRY, DebugMessageInterceptor


class Deluder:
    """
    Deluder class is a core component, which boots the whole Deluder application
    """
    config: DeluderConfig
    managed: bool
    processes: Set[Process]
    script: str
    executor: ThreadPoolExecutor
    interceptors: List[MessageInterceptor]
    host: str
    
    def __init__(self, processes: Set[Process], managed: bool, config: Optional[DeluderConfig]=None, host: Optional[DeluderConfig]=""):
        self.managed = managed
        self.config = config if config is not None else create_default_config()
        self.host = host if host is not None else ""
        self.processes = processes

    @classmethod
    def version(cls) -> str:
        return VERSION

    @classmethod
    def for_new_app(cls, app_path: Union[str, List[str]], config: Optional[DeluderConfig]) -> 'Deluder':
        """
        Creates Deluder core for starting new application
        """
        logger.info(f'Starting process for application "{app_path}"...')
        pid = frida.spawn(app_path)
        logger.info(f'Process started with PID "{pid}".')
        process = Process(pid=pid)
        logger.info(f'Created deluder for existing process with PID {pid}.')
        return Deluder(processes={process}, managed=True, config=config)

    @classmethod
    def for_existing_process_id(cls, pid: int, config: DeluderConfig, host: str) -> 'Deluder':
        """
        Creates Deluder core for already running application identified by PID
        """
        logger.info(f'Attaching deluder to process with PID {pid}...')
        process = Process(pid=pid)
        logger.info(f'Created deluder for existing process with PID {pid}...')
        return Deluder(processes={process}, managed=False, config=config, host=host)

    @classmethod
    def for_existing_process_name(cls, process_name: str, config: DeluderConfig, host: str) -> 'Deluder':
        """
        Creates Deluder core for already running application identified by process name
        """
        logger.info(f'Attaching deluder to process "{process_name}"...')
        if not host:
            pid = frida.get_local_device().get_process(process_name).pid  
        else:
            frida.get_device_manager().add_remote_device(host).get_process(process_name).pid
        process = Process(pid=pid)
        logger.info(f'Created deluder for existing process "{process_name}" with PID {pid}...')
        return Deluder(processes={process}, managed=False, config=config, host=host)

    def delude(self):
        """
        Starts the Deluder core and all underlying components.
        Finishes once the target application stops or user interrupts Deluder.
        """
        logger.info('Starting to cause delusions...')
        try: 
            set_debug_level(self.config.debug)

            self.executor = ThreadPoolExecutor(max_workers=1)

            self._init_device()
            self._init_interceptors()
            self._init_child_gating()
            self._init_scripts()
            self._init_router()

            for process in copy.copy(self.processes):
                self._attach_process(process, resume=self.managed)

            logger.info('Delusions started.')

            self._wait_for_app_stop()
        except DeluderException as e:
            logger.error(f'Deluder failed with an error: {e.message}')
        except Exception as e:
            logger.error('Deluder crashed!', exc_info=e)
        finally:
            self._stop_app()

            self._destroy_interceptors()

            self.executor.shutdown()
        logger.info('Deluder finished.')

    def _init_device(self):
        self.device = frida.get_local_device() if not self.host else frida.get_device_manager().add_remote_device(self.host)

    def _resume_process(self, process: Process):
        try:
            self.device.resume(process.pid)
        except frida.InvalidArgumentError as e:
            logger.error('Failed to resume application process with PID %d!', process.pid, exc_info=e)
    
    def _attach_process(self, process: Process, resume=False):
        try:
            # Attach process
            session = self.device.attach(process.pid)
            
            # Handle detach
            process.session = session
            session.on('detached', lambda reason: self.executor.submit(self._on_detached, process, reason))

            # Enable child gating
            if not self.config.ignore_child_processes:
                session.enable_child_gating()

            # Inject script
            script = session.create_script(self.script)
            process.script = script
            script.on('message', lambda message, data: self.router.route(process=process, message=message, data=data))
            script.load()
        except Exception as e:
            logger.error('Failed to attach to application process with PID %d!', process.pid, exc_info=e)
            self.executor.submit(self._on_detached, process, 'Attach process failed!')
        finally:
            # Resume process if needed
            if resume:
                self._resume_process(process)

    def _on_detached(self, process: Process, reason: str):
        logger.info("Deluder detached from process %d: %s", process.pid, reason)
        self.processes.remove(process)

    def _wait_for_app_stop(self):
        # Wait for deluded app to finish
        logger.info('Waiting for target process to finish...')
        try:
            while len(self.processes) > 0:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info('Delusions interrupted.')

    def _resume_app(self):
        if not self.managed:
            return
    
        # If app is managed by deluder, resume it
        for process in copy.copy(self.processes):
            self._resume_process(process)

    def _stop_app(self):
        if not self.managed:
            return
        
        # If app is managed by deluder, kill it if it is still running
        for process in copy.copy(self.processes):
            if psutil.pid_exists(process.pid):
                psutil.Process(process.pid).kill()
                logger.info('Killed target application process with PID %d.', process.pid)
    
    def _init_child_gating(self):
        if self.config.ignore_child_processes:
            return

        self.device.on('child-added', lambda child: self.executor.submit(self._on_child_added, child))
        self.device.on('child-removed', lambda child: self.executor.submit(self._on_child_removed, child))

    def _on_child_added(self, child):
        logger.info("Child process detected: %s", child)
        process = Process(child.pid)
        self.processes.add(process)
        self._attach_process(process, True)

    def _on_child_removed(self, child):
        logger.info("Child process destroyed: %s", child)

    def _init_scripts(self):
        self.script = load_scripts(self.config)
        logger.info('Scripts loaded.')

    def _init_interceptors(self):
        self.interceptors = []
        
        if self.config.debug:
            logger.info('Loaded interceptor: debug')
            self.interceptors.append(DebugMessageInterceptor())

        for interceptor in self.config.interceptors:
            if interceptor.type not in AVAILABLE_INTERCEPTORS:
                raise DeluderException(f'Interceptor {interceptor.type} not found!')
            self.interceptors.append(INTERCEPTORS_REGISTRY[interceptor.type](interceptor.config))
            logger.info('Loaded interceptor: %s', interceptor.type)

        for interceptor in self.interceptors:
            interceptor.init()

    def _init_router(self):
        self.router = MessageRouter(
            interceptors=self.interceptors
        )
        logger.info('Router initialized.')

    def _destroy_interceptors(self):
        if not hasattr(self, 'interceptors'):
            return
        for interceptor in self.interceptors:
            interceptor.destroy()
        logger.info('Interceptors destroyed.')
