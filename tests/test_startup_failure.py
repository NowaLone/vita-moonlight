"""Interpret startup failure/exit ordering with serial PAF mocks; no native calls."""
import unittest

from pycparser import c_parser
from test_host_persistence import run
from test_host_storage_paths import extract
from test_xml_source import ROOT


class StartupFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'src/app/paf_runtime.cpp').read_text()
        callback = extract(source, 'loadPluginCB').replace('paf::Plugin', 'Plugin')
        callback = callback.replace('MoonlightApp::Instance()', 'app_instance()').replace('s_startup_app->Start', 'start_app')
        cls.callback = c_parser.CParser().parse('typedef int Plugin;' + callback).ext[-1].body
        task = extract(source, 'StartupErrorTask')
        task = task.replace('static_cast<MoonlightApp *>(userdata)', '(MoonlightApp *)userdata')
        task = task.replace('app->Connection().IsBusy()', 'busy()')
        task = task.replace('paf::common::MainThreadCallList::Unregister', 'unregister_task')
        task = task.replace('paf::Framework::Instance()->RequestShutdown()', 'request_shutdown()')
        cls.task = c_parser.CParser().parse('typedef int MoonlightApp;' + task).ext[-1].body
        code = source[source.index('    s_startup_result = -1;', source.index('int paf_runtime_main')):]
        for old, new in (
                ('paf::Plugin::LoadSync', 'load_plugin'), ('paf::Plugin::Find', 'find_plugin'),
                ('s_startup_app->Connection().ShowError', 'show_error'),
                ('ui_text("msg_error_startup").c_str()', 'startup_text()'),
                ('paf::common::MainThreadCallList::Register', 'register_task'),
                ('paf_fw->RequestShutdown()', 'request_shutdown()'),
                ('paf_fw->Run()', 'framework_run()'), ('s_startup_app->Shutdown()', 'shutdown_app()')):
            code = code.replace(old, new)
        cls.flow = c_parser.CParser().parse('int startup(void) {' + code).ext[-1].body
        main = (ROOT / 'src/main.cpp').read_text()
        code = main[main.index('\tint result = paf_runtime_main();'):]
        code = code[:code.index('\n}') + 2]
        cls.module = c_parser.CParser().parse('int module_tail(void) {' + code).ext[-1].body

    def test_callback_keeps_exact_start_error_and_handles_allocation_failure(self):
        for app, status in ((1, 0), (1, -10), (0, -1)):
            calls = []
            values = dict(plugin=7, s_startup_app=0, s_startup_result=-1,
                          app_instance=lambda: app, start_app=lambda plugin: calls.append(plugin) or status)
            run(self.callback, values)
            self.assertEqual(values['s_startup_result'], status)
            self.assertEqual(calls, [7] if app else [])

    def test_load_failure_dialog_and_success_paths_return_through_cleanup(self):
        for app, plugin, status in ((1, 1, 0), (1, 1, -10), (1, 0, -1), (0, 0, -1)):
            with self.subTest(app=app, plugin=plugin, status=status):
                calls = []
                values = dict(s_startup_app=99, s_startup_result=99, NULL=0, pluginParam=7,
                              StartupErrorTask=5, startup_text=lambda: 'startup error',
                              find_plugin=lambda name: plugin,
                              show_error=lambda text, status: calls.append(('error', status)),
                              register_task=lambda *args: calls.append('register'),
                              request_shutdown=lambda: calls.append('exit'),
                              framework_run=lambda: calls.append('run'),
                              shutdown_app=lambda: calls.append('cleanup'))
                def load(param):
                    self.assertEqual((values['s_startup_app'], values['s_startup_result']), (0, -1))
                    calls.append('load')
                    values.update(s_startup_app=app, s_startup_result=status)
                values['load_plugin'] = load
                self.assertEqual(run(self.flow, values), status)
                expected = ['load']
                if status:
                    expected += [('error', status), 'register'] if app and plugin else ['exit']
                expected += ['run'] + (['cleanup'] if app else [])
                self.assertEqual(calls, expected)
                module_calls = []
                result = run(self.module, dict(paf_runtime_main=lambda: status,
                    _free_vita_newlib=lambda: module_calls.append('free-runtime'),
                    SCE_KERNEL_START_SUCCESS=0, SCE_KERNEL_START_FAILED=1))
                self.assertEqual(result, int(status != 0))
                self.assertEqual(module_calls, ['free-runtime'])

    def test_exit_waits_for_dialog_and_unregisters_before_shutdown(self):
        for busy in (True, False):
            calls = []
            run(self.task, dict(userdata=1, StartupErrorTask=5, busy=lambda: busy,
                               unregister_task=lambda *args: calls.append('unregister'),
                               request_shutdown=lambda: calls.append('exit')))
            self.assertEqual(calls, [] if busy else ['unregister', 'exit'])


if __name__ == '__main__':
    unittest.main()
