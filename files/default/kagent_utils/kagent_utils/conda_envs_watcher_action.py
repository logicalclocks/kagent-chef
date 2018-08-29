import watcher_action
import subprocess
import os

import json

"""
A WatcherAction to monitor Anaconda environments and add them
to a CircularLinkedList
"""
class CondaEnvsWatcherAction(watcher_action.WatcherAction):
    def __init__(self, monitor_list, kconfig):
        self.monitor_list = monitor_list
        self.kconfig = kconfig
        self.conda_bin = os.path.join(kconfig.conda_dir, 'bin', 'conda')
        
        # System conda envs that should NOT be cleaned by GC
        self._blacklisted_envs = set()
        self._blacklisted_envs.add('anaconda')
        self._blacklisted_envs.add(os.path.basename(os.path.normpath(kconfig.conda_dir)))
        # python27 python36
        [self._bl_python_env_name(p) for p in kconfig.conda_python_versions.split(',')]

    def _bl_python_env_name(self, version):
        stripped = version.strip()
        env_name = "python{0}".format(stripped.replace('.', ''))
        self._blacklisted_envs.add(env_name)
        
    def preAction(self, *args, **kwargs):
        pass

    def action(self, *args, **kwargs):
        conda_envs = self._get_conda_envs()
        envs_json = json.loads(conda_envs)
        if not envs_json.has_key('envs'):
            raise RuntimeError('envs key does not exist in Anaconda env list command output')
        envs_path = envs_json['envs']
        envs = [os.path.basename(os.path.normpath(i)) for i in envs_path]
        for e in envs:
            if e not in self._blacklisted_envs:
                self.monitor_list.add_first(e)

    def postAction(self, *args, **kwargs):
        pass

    def _get_conda_envs(self):
        return subprocess.check_output([self.conda_bin, "env", "list", "--json"])
