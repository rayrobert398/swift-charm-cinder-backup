# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mock import patch

with patch('cinder_backup_utils.register_configs'):
    import cinder_backup_hooks as hooks

from test_utils import (
    CharmTestCase
)

TO_PATCH = [
    # cinder_utils
    'ensure_ceph_keyring',
    'register_configs',
    'restart_map',
    'set_ceph_env_variables',
    'is_request_complete',
    'send_request_if_needed',
    'CONFIGS',
    # charmhelpers.core.hookenv
    'config',
    'relation_ids',
    'relation_set',
    'service_name',
    'service_restart',
    'log',
    # charmhelpers.core.host
    'apt_install',
    'apt_update',
    # charmhelpers.contrib.hahelpers.cluster_utils
    'execd_preinstall',
    'delete_keyring'
]


class TestCinderBackupHooks(CharmTestCase):

    def setUp(self):
        super(TestCinderBackupHooks, self).setUp(hooks, TO_PATCH)
        self.config.side_effect = self.test_config.get

    @patch('charmhelpers.core.hookenv.config')
    @patch('os.mkdir')
    def test_ceph_joined(self, mkdir, mock_config):
        """It correctly prepares for a ceph changed hook"""
        with patch('os.path.isdir') as isdir:
            isdir.return_value = False
            hooks.hooks.execute(['hooks/ceph-relation-joined'])
            mkdir.assert_called_with('/etc/ceph')

    @patch('charmhelpers.core.hookenv.config')
    def test_ceph_changed_no_key(self, mock_config):
        """It does nothing when ceph key is not available"""
        self.CONFIGS.complete_contexts.return_value = ['']
        hooks.hooks.execute(['hooks/ceph-relation-changed'])
        m = 'ceph relation incomplete. Peer not ready?'
        self.log.assert_called_with(m)

    @patch('charmhelpers.core.hookenv.config')
    def test_ceph_changed(self, mock_config):
        """It ensures ceph assets created on ceph changed"""
        self.is_request_complete.return_value = True
        self.CONFIGS.complete_contexts.return_value = ['ceph']
        self.service_name.return_value = 'cinder-backup'
        self.ensure_ceph_keyring.return_value = True
        hooks.hooks.execute(['hooks/ceph-relation-changed'])
        self.ensure_ceph_keyring.assert_called_with(service='cinder-backup',
                                                    user='cinder',
                                                    group='cinder')
        self.assertTrue(self.CONFIGS.write_all.called)
        self.set_ceph_env_variables.assert_called_with(service='cinder-backup')

    @patch.object(hooks, 'get_ceph_request')
    @patch('charmhelpers.core.hookenv.config')
    def test_ceph_changed_newrq(self, mock_config, mock_get_ceph_request):
        """It ensures ceph assets created on ceph changed"""
        mock_get_ceph_request.return_value = 'cephreq'
        self.is_request_complete.return_value = False
        self.CONFIGS.complete_contexts.return_value = ['ceph']
        self.service_name.return_value = 'cinder-backup'
        self.ensure_ceph_keyring.return_value = True
        hooks.hooks.execute(['hooks/ceph-relation-changed'])
        self.ensure_ceph_keyring.assert_called_with(service='cinder-backup',
                                                    user='cinder',
                                                    group='cinder')
        self.send_request_if_needed.assert_called_with('cephreq')

    @patch('charmhelpers.core.hookenv.config')
    def test_ceph_changed_no_keys(self, mock_config):
        """It ensures ceph assets created on ceph changed"""
        self.CONFIGS.complete_contexts.return_value = ['ceph']
        self.service_name.return_value = 'cinder-backup'
        self.is_request_complete.return_value = True
        self.ensure_ceph_keyring.return_value = False
        hooks.hooks.execute(['hooks/ceph-relation-changed'])
        # NOTE(jamespage): If ensure_ceph keyring fails, then
        # the hook should just exit 0 and return.
        self.assertTrue(self.log.called)
        self.assertFalse(self.CONFIGS.write_all.called)
