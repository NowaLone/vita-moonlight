"""Interpret motion worker steps with serial host-callback/kernel mocks, without compilation."""
import re
import unittest
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import function, run
from test_xml_source import ROOT, strip_directives


class Motion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'src/moonlight/vita_motion.c').read_text()
        code = '\n'.join(function(cls.source, name) for name in (
            'gyro_thread_main', 'accel_thread_main', 'vita_motion_set_state', 'vita_motion_stop',
            'send_gyro', 'send_accel', 'vita_motion_set_suspended',
            'vita_motion_init', 'vita_motion_start'))
        process = function((ROOT / 'src/moonlight/vita_input.c').read_text(), 'vita_input_process')
        code += '\n' + process[:process.index('    s_overlay_release_sent = false;')]
        code += '    forward_input();\n}'
        code = code.replace('(void)args;', '').replace('(void)argp;', '')
        unit = c_parser.CParser().parse('typedef unsigned int SceSize; typedef unsigned int SceUInt;'
                                       'typedef unsigned short uint16_t; typedef unsigned char uint8_t; typedef int bool;'
                                       'typedef struct {float x,y,z;} Vector;'
                                       'typedef struct {Vector acceleration, angularVelocity;} SceMotionState;'
                                       'typedef struct {Vector accelerometer, gyro;} SceMotionSensorState;'
                                       + strip_directives(code))
        cls.bodies = {node.decl.name: node.body for node in unit.ext if isinstance(node, c_ast.FuncDef)}

    def setUp(self):
        self.sent, self.delays = [], []
        self.values = dict(args=0, argp=0, true=1, false=0, s_active=1, s_enabled=1,
                           s_suspended=0,
                           s_gyro_rate=100, s_accel_rate=50, __ATOMIC_RELAXED=0,
                           LI_MOTION_TYPE_GYRO=2, LI_MOTION_TYPE_ACCEL=1,
                           vita_debug_log=lambda *args: None,
                           __atomic_load_n=lambda name, order: self.values[name],
                           __atomic_store_n=lambda name, value, order: self.values.update({name: value}),
                           sceKernelDelayThread=self.delay)
        self.values['vita_motion_set_suspended'] = self.suspend
        self.values.update({name: float(value) for name, value in re.findall(
            r'^#define (\w+) ([\d.]+)f$', self.source, re.M)})

    def invoke(self, name):
        original = runtime.expression

        def expression(node, values):
            if isinstance(node, c_ast.BinaryOp) and node.op in ('/', '*'):
                a, b = expression(node.left, values), expression(node.right, values)
                return a // b if node.op == '/' else a * b
            return original(node, values)

        with patch.object(runtime, 'expression', expression):
            return run(self.bodies[name], self.values)

    def delay(self, microseconds):
        self.delays.append(microseconds)
        raise StopIteration  # End the otherwise persistent worker after one iteration.

    def suspend(self, value):
        self.values['suspended'] = value
        self.invoke('vita_motion_set_suspended')

    def step(self, kind, during_send=None):
        def send():
            self.sent.append(kind)
            if during_send:
                during_send()
        self.values['send_' + kind] = send
        with self.assertRaises(StopIteration):
            self.invoke(kind + '_thread_main')

    def test_zero_rate_or_stop_during_send_cannot_become_the_delay_divisor(self):
        for kind, motion_type, expected in (('gyro', 2, 10000), ('accel', 1, 20000)):
            for action in ('host_disable', 'stop', 'rate_change'):
                with self.subTest(kind=kind, action=action):
                    self.setUp()

                    def interrupt():
                        if action == 'stop':
                            self.invoke('vita_motion_stop')
                        else:
                            self.values.update(controller=0, motion_type=motion_type,
                                               report_rate_hz=0 if action == 'host_disable' else 200)
                            self.invoke('vita_motion_set_state')

                    self.step(kind, interrupt)
                    self.assertEqual(self.sent, [kind])
                    self.assertEqual(self.delays, [expected])
                    self.sent.clear()
                    self.delays.clear()
                    self.step(kind)
                    self.assertEqual(self.sent, [kind] if action == 'rate_change' else [])
                    self.assertEqual(self.delays, [5000 if action == 'rate_change' else 100000])

    def test_disabled_inactive_or_zero_rate_workers_do_not_send(self):
        for kind in ('gyro', 'accel'):
            for field in ('s_active', 's_enabled', 's_' + kind + '_rate'):
                with self.subTest(kind=kind, field=field):
                    self.setUp()
                    self.values[field] = 0
                    self.step(kind)
                    self.assertEqual(self.sent, [])
                    self.assertEqual(self.delays, [100000])

    def test_samples_use_moonlight_units_and_sdl_axis_order(self):
        def sample(destination, *args):
            gyro = dict(x=1.5707963268, y=-0.7853981634, z=3.1415926536)
            accel = dict(x=1, y=-0.5, z=0.25)
            self.values[destination] = dict(gyro=gyro, angularVelocity=gyro,
                                            accelerometer=accel, acceleration=accel)
            return 0

        self.values.update(sceMotionGetState=sample, sceMotionGetSensorState=sample,
                           LiSendControllerMotionEvent=lambda *args: self.sent.append(args))
        for kind, motion_type, expected in (('gyro', 2, (90, -45, 180)),
                ('accel', 1, (9.80665, -4.903325, 2.4516625))):
            with self.subTest(kind=kind):
                self.sent.clear()
                self.invoke('send_' + kind)
                self.assertEqual(len(self.sent), 1)
                self.assertEqual(len(self.sent[0]), 5)
                self.assertEqual(self.sent[0][:2], (0, motion_type))
                for actual, wanted in zip(self.sent[0][2:], expected):
                    self.assertAlmostEqual(actual, wanted, places=4)

    def test_sensor_read_errors_never_send_uninitialized_data(self):
        self.values.update(sceMotionGetState=lambda *args: -1,
                           sceMotionGetSensorState=lambda *args: -1,
                           LiSendControllerMotionEvent=lambda *args: self.sent.append(args))
        self.invoke('send_gyro')
        self.invoke('send_accel')
        self.assertEqual(self.sent, [])

    def test_overlay_pauses_workers_and_resumes_with_current_host_rates(self):
        self.suspend(1)
        self.values.update(controller=0, motion_type=2, report_rate_hz=200)
        self.invoke('vita_motion_set_state')
        for kind in ('gyro', 'accel'):
            self.step(kind)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.delays, [100000, 100000])
        self.suspend(0)
        self.delays.clear()
        for kind in ('gyro', 'accel'):
            self.step(kind)
        self.assertEqual(self.sent, ['gyro', 'accel'])
        self.assertEqual(self.delays, [5000, 20000])
        self.invoke('vita_motion_stop')
        self.assertEqual(self.values['s_suspended'], 1)

    def test_input_overlay_gate_updates_motion_before_suppressing_or_forwarding_buttons(self):
        calls = []
        def observed(action, suspended):
            self.assertEqual(self.values['s_suspended'], suspended)
            calls.append(action)

        self.values.update(vita_input_system_ui_overlaid=lambda: True,
                           vita_input_suppress_for_system_ui=lambda: observed('suppress', 1),
                           forward_input=lambda: observed('forward', 0))
        self.invoke('vita_input_process')
        self.assertEqual(self.values['s_suspended'], 1)
        self.assertEqual(calls, ['suppress'])
        self.values['vita_input_system_ui_overlaid'] = lambda: False
        self.invoke('vita_input_process')
        self.assertEqual(self.values['s_suspended'], 0)
        self.assertEqual(calls, ['suppress', 'forward'])
        start = function(self.source, 'vita_motion_start')
        self.assertLess(start.index('vita_motion_set_suspended(1)'),
                        start.index('__atomic_store_n(&s_active,'))

    def test_start_failure_stays_inactive_and_next_stream_retries_missing_setup(self):
        for failure in ('sampling', 'gyro', 'accel'):
            with self.subTest(failure=failure):
                self.setUp()
                attempts = []
                failed = [True]

                def create(name, entry, started):
                    # Existing create_thread only starts threads whose flag is still false.
                    if not self.values[started]:
                        attempts.append(name)
                        self.values[started] = not (failed[0] and failure in name)

                self.values.update(enabled=1, s_active=0, s_initialized=0,
                                   s_gyro_thread_started=0, s_accel_thread_started=0,
                                   gyro_thread_main=1, accel_thread_main=2,
                                   SCE_MOTION_ERROR_ALREADY_SAMPLING=-2,
                                   sceMotionStartSampling=lambda: -1 if failed[0] and failure == 'sampling' else -2,
                                   sceMotionReset=lambda: 0, create_thread=create,
                                   vita_motion_init=lambda: self.invoke('vita_motion_init'),
                                   vita_motion_stop=lambda: self.invoke('vita_motion_stop'))
                self.invoke('vita_motion_start')
                self.assertFalse(self.values['s_initialized'])
                self.assertFalse(self.values['s_active'])
                if failure == 'sampling':
                    self.assertEqual(attempts, [])
                failed[0] = False
                self.invoke('vita_motion_start')
                self.assertTrue(self.values['s_initialized'])
                self.assertTrue(self.values['s_active'])
                for kind in ('gyro', 'accel'):
                    self.assertEqual(attempts.count('vita_moonlight_' + kind),
                                     2 if failure == kind else 1)
                completed_attempts = list(attempts)
                self.values['enabled'] = 0
                self.invoke('vita_motion_start')
                self.assertFalse(self.values['s_active'])
                self.assertEqual((self.values['s_gyro_rate'], self.values['s_accel_rate']), (0, 0))
                self.values['enabled'] = 1
                self.invoke('vita_motion_start')
                self.assertTrue(self.values['s_active'])
                self.assertEqual(attempts, completed_attempts)


if __name__ == '__main__':
    unittest.main()
