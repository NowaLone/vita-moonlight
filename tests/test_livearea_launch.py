"""Interpret LiveArea admission/routing with serial AppMgr, store and UI mocks."""
import copy
import unittest
from unittest.mock import patch

from ui_test_strings import mock_ui_text
from pycparser import c_parser
import test_adapter_lifecycle as runtime
import test_livearea as frames
from test_host_lists import function
from test_host_persistence import run
from test_xml_source import ROOT, strip_directives


class LiveAreaLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frames.LiveArea.setUpClass()
        cls.main = (ROOT / 'src/pages/page_main.cpp').read_text()
        cls.apps = (ROOT / 'src/pages/page_apps.cpp').read_text()
        poll = function((ROOT / 'src/app/moonlight_app.cpp').read_text(), 'MoonlightApp::PollLiveAreaEvents')
        poll = poll.replace('page::Main *main = page::Main::Instance()', 'int main = main_instance()')
        poll = poll.replace('LiveAreaService::ParseTarget', 'parse_target')
        poll = poll.replace('main->CanConnectFromLiveArea', 'can_connect').replace('main->ConnectFromLiveArea', 'connect')
        poll = poll.replace('m_hosts.Resolve', 'resolve').replace('m_connection.ShowError', 'show_error')
        for name, size in (('state', 128), ('event', 1028), ('parameter', 1051)):
            poll = poll.replace('sizeof(' + name + ')', str(size))
        admission = function(cls.main, 'Main::CanConnectFromLiveArea').replace(') const', ')')
        admission = admission.replace('MoonlightApp *app = MoonlightApp::Instance()', 'int app = 1')
        admission = admission.replace('Base *current = Base::GetCurrent()', 'int current = current_page()')
        admission = admission.replace('current->IsTransitioning()', 'is_transitioning(current)')
        admission = admission.replace('Base::Find', 'find_page').replace('app->Connection().IsBusy', 'is_busy')
        admission = admission.replace('app->Connection().State', 'connection_state')
        admission = admission.replace('app->Applications().IsArtworkIdle', 'artwork_idle')
        resolve = function((ROOT / 'src/services/host_service.cpp').read_text(), 'HostService::Resolve')
        resolve = resolve.replace('const MoonlightHost &identity', 'const MoonlightHost *identity')
        resolve = resolve.replace('paf::vector<MoonlightHost> hosts;', 'int hosts = host_vector();')
        resolve = resolve.replace('hosts.resize(capacity)', 'resize(hosts, capacity)').replace('hosts.data()', 'hosts')
        launch = function(cls.apps, 'Apps::LaunchRequestedApplication').replace(
            'MoonlightApp::Instance()->Connection().ShowError', 'show_error')
        types = '''typedef int bool; typedef unsigned long long uint64_t;
        typedef struct {char name[256], internal[256], host_id[33]; int port;} MoonlightHost;
        typedef struct {int appEventNum, isSystemUiOverlaid;} SceAppMgrAppState;
        typedef struct {int type;} SceAppUtilAppEventParam;
        typedef struct {char param[1019], reserved[32];} MoonlightLiveAreaEventParam;'''
        code = poll + admission + resolve + launch
        code = mock_ui_text(code)
        for prefix in ('MoonlightApp::', 'Main::', 'HostService::', 'Apps::'): code = code.replace(prefix, '')
        unit = c_parser.CParser().parse(types + strip_directives(code))
        cls.bodies = {node.decl.name: node.body for node in unit.ext if hasattr(node, 'body')}

    def setUp(self):
        self.h = frames.LiveArea()
        self.h.setUp()
        self.calls = []
        self.scope = dict(false=0, true=1, NULL=0, this=1, root=1,
                          m_transitioning=0, m_apps_ready=1, m_connecting=0, m_selection_mode=0,
                          m_ime_open=0, m_ime_retry_pending=0,
                          m_settings_suspended=0, m_delete_dialog_open=0, m_pending_action=0, Pending_None=0,
                          MOONLIGHT_CONNECTION_STREAMING=3, MOONLIGHT_CONNECTION_PAUSED=4,
                          current_page=lambda: 1, find_page=lambda name: 2,
                          is_busy=lambda: False, is_transitioning=lambda page: False, connection_state=lambda: 2,
                          artwork_idle=lambda: True,
                          vita_debug_log=lambda *args: None,
                          show_error=lambda *args: self.calls.append('error'))

    def execute(self, name):
        with patch.object(runtime, 'expression', self.h.expression), patch.object(runtime, 'execute', self.h.execute):
            return run(self.bodies[name], self.scope)

    def test_saved_uuid_is_authoritative_and_routes_only_resolve_uuidless_attempts(self):
        saved = [self.h.host('Duplicate name', 'A'), self.h.host('Duplicate name', 'B')]
        saved[1]['internal'] = frames.string('192.0.2.2')
        def get_hosts(out, capacity):
            if out == 0: return len(saved)
            out[:] = copy.deepcopy(saved[:capacity])
            return len(out)
        self.scope.update(GetHosts=get_hosts, host_vector=list, resize=lambda *args: None,
                          strcmp=lambda a, b: int(frames.text(a) != frames.text(b)))
        for host_id, address, port, expected in (('B', '192.0.2.1', 47989, 'B'),
                ('deleted', '192.0.2.1', 47989, None), ('', '192.0.2.1', 47989, 'A'),
                ('', '192.0.2.1', 48000, None), ('', 'missing', 47989, None)):
            identity = self.h.host('Duplicate name', host_id)
            identity.update(internal=frames.string(address), port=port)
            out = self.h.host('', '')
            self.scope.update(identity=identity, out=out)
            self.assertEqual(bool(self.execute('Resolve')), expected is not None)
            if expected: self.assertEqual(frames.text(out['host_id']), expected)

    def test_admission_allows_idle_main_or_apps_and_rejects_each_conflicting_state(self):
        for page, accepted in ((1, True), (2, True), (3, False), (0, False)):
            self.scope['current_page'] = lambda: page
            self.assertEqual(bool(self.execute('CanConnectFromLiveArea')), accepted)
        self.scope['is_transitioning'] = lambda page: True
        for page in (1, 2):
            self.scope['current_page'] = lambda: page
            self.assertFalse(self.execute('CanConnectFromLiveArea'))
        self.scope['is_transitioning'] = lambda page: False
        self.scope['current_page'] = lambda: 1
        for field in ('m_connecting', 'm_selection_mode', 'm_ime_open', 'm_ime_retry_pending',
                      'm_settings_suspended', 'm_delete_dialog_open', 'm_pending_action'):
            self.scope[field] = 1
            self.assertFalse(self.execute('CanConnectFromLiveArea'), field)
            self.scope[field] = 0
        self.scope['is_busy'] = lambda: True
        self.assertFalse(self.execute('CanConnectFromLiveArea'))
        self.scope['is_busy'] = lambda: False
        self.scope['artwork_idle'] = lambda: False
        self.assertFalse(self.execute('CanConnectFromLiveArea'))
        self.scope['artwork_idle'] = lambda: True
        for state in (3, 4):
            self.scope['connection_state'] = lambda: state
            self.assertFalse(self.execute('CanConnectFromLiveArea'))

    def test_requested_app_uses_fresh_id_once_not_the_old_slot_or_an_automatic_retry(self):
        self.scope.update(m_apps=[dict(id=99), dict(id=438)], m_app_count=2,
                          m_livearea_application_id=438,
                          SelectApp=lambda index: self.calls.append(index))
        self.execute('LaunchRequestedApplication')
        self.execute('LaunchRequestedApplication')
        self.assertEqual(self.calls, [1])
        self.scope['m_livearea_application_id'] = 123
        self.execute('LaunchRequestedApplication')
        self.execute('LaunchRequestedApplication')
        self.assertEqual(self.calls, [1, 'error'])

    def prepare_native(self, event_type=5, payload='moonlight1/7063/438', state_error=0,
                       receive_error=0, parse_error=0, overlaid=False, saved=True, eligible=True):
        def zero(destination, value, size):
            self.scope[destination] = (dict(param=[0] * 1019, reserved=[0] * 32)
                                       if destination == 'parameter' else {})
        def app_state(destination, *args):
            self.scope[destination].update(appEventNum=1, isSystemUiOverlaid=overlaid)
            return state_error
        def receive(destination):
            self.calls.append('receive')
            self.scope[destination]['type'] = event_type
            return receive_error
        def parse(destination, output):
            self.calls.append('parse')
            self.scope[output]['param'][:len(payload) + 1] = list(payload.encode()) + [0]
            return parse_error
        def target(parameter, identity, application_id):
            out = [0]
            result = self.h.invoke('ParseTarget', parameter, self.scope[identity], out)
            self.scope[application_id] = out[0]
            return result
        self.scope.update(m_livearea_event_poll_at=0, sceKernelGetProcessTimeWide=lambda: 1000000,
                          sce_paf_memset=zero, _sceAppMgrGetAppState=app_state,
                          sceAppUtilReceiveAppEvent=receive, sceAppUtilAppEventParseLiveArea=parse,
                          sce_paf_memchr=lambda data, value, size: int(value in data[:size]),
                          parse_target=target, main_instance=lambda: 1, can_connect=lambda: eligible,
                          resolve=lambda *args: saved,
                          connect=lambda host, app: self.calls.append(('connect', app)))

    def test_native_poll_only_parses_livearea_events_and_checks_api_results(self):
        for options, expected in ((dict(event_type=0), ['receive']),
                (dict(event_type=1), ['receive']), (dict(receive_error=-9), ['receive']),
                (dict(state_error=-9), []), (dict(overlaid=True), []),
                (dict(parse_error=-9), ['receive', 'parse'])):
            self.calls.clear()
            self.prepare_native(**options)
            self.execute('PollLiveAreaEvents')
            self.assertEqual(self.calls, expected)

    def test_native_poll_launches_once_and_rejects_busy_deleted_or_invalid_targets(self):
        for options, tail in (({}, [('connect', 438)]),
                (dict(payload='moonlight1/7063/0'), [('connect', 0)]),
                (dict(saved=False), ['error']), (dict(eligible=False), []),
                (dict(payload='eboot'), [])):
            self.calls.clear()
            self.prepare_native(**options)
            self.execute('PollLiveAreaEvents')
            self.execute('PollLiveAreaEvents')  # 100 ms gate; no replay at the same tick.
            self.assertEqual(self.calls, ['receive', 'parse'] + tail)

    def test_queued_event_is_consumed_once_after_resume_and_busy_taps_are_not_deferred(self):
        for label, overlaid, eligible in (('cold', False, True), ('resume', True, True),
                                          ('busy', False, False)):
            with self.subTest(label=label):
                self.setUp()
                self.prepare_native(eligible=eligible)
                events = [5]
                now = [1000000]
                overlay = [overlaid]

                def app_state(destination, *args):
                    self.scope[destination].update(appEventNum=len(events),
                                                   isSystemUiOverlaid=overlay[0])
                    return 0

                def receive(destination):
                    self.calls.append('receive')
                    self.scope[destination]['type'] = events.pop(0)
                    return 0

                self.scope.update(_sceAppMgrGetAppState=app_state,
                                  sceAppUtilReceiveAppEvent=receive,
                                  sceKernelGetProcessTimeWide=lambda: now[0])
                self.execute('PollLiveAreaEvents')
                if overlaid:
                    self.assertEqual(self.calls, [])
                    self.assertEqual(events, [5])
                    overlay[0] = False
                    now[0] += 100000
                    self.execute('PollLiveAreaEvents')
                self.assertEqual(events, [])
                expected = ['receive', 'parse'] + ([('connect', 438)] if eligible else [])
                self.assertEqual(self.calls, expected)
                self.scope['can_connect'] = lambda: True
                for _ in range(3):
                    now[0] += 100000
                    self.execute('PollLiveAreaEvents')
                self.assertEqual(self.calls, expected)

    def test_unterminated_native_parameter_is_rejected_before_target_parser(self):
        self.prepare_native()

        def parse(destination, output):
            self.calls.append('parse')
            # The reserved tail remains zero; only param's own boundary may terminate it.
            self.scope[output]['param'] = [ord('a')] * 1019
            return 0

        def unexpected_target(*args):
            self.fail('Unterminated native parameter reached the string parser')

        self.scope.update(sceAppUtilAppEventParseLiveArea=parse, parse_target=unexpected_target)
        self.execute('PollLiveAreaEvents')
        self.assertEqual(self.calls, ['receive', 'parse'])

    def test_pairing_handoff_and_error_paths_preserve_one_shot_intent(self):
        pairing = (ROOT / 'src/pages/page_pairing.cpp').read_text()
        self.assertIn('new Apps(application_id)', self.main)
        self.assertIn('new Pairing(pin, application_id)', self.main)
        self.assertIn('new Apps(pairing->m_livearea_application_id)', pairing)
        self.assertIn('m_livearea_application_id = 0;', function(pairing, 'Pairing::ShowSystemError'))
        self.assertIn('apps->m_livearea_application_id = 0;', function(self.apps, 'Apps::OnMoonlightEvent'))
        binding = (ROOT / 'include/platform/livearea.h').read_text()
        self.assertIn('VITASDK_BUILD_ASSERT_EQ(1051, MoonlightLiveAreaEventParam)', binding)


if __name__ == '__main__':
    unittest.main()
