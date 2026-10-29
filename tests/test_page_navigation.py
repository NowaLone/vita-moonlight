"""Interpret actual Apps navigation with serial PAF timers/widgets, without building.

Callbacks, allocation/API failures and page-stack handoff are mocked. This does
not validate native ownership/ABI, perspective, clipping, focus or Vita rendering.
"""
import re
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from ui_test_strings import mock_ui_text
from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_lists import function
from test_xml_source import ROOT, strip_directives

SOURCE = (ROOT / 'src/pages/page_apps.cpp').read_text()
BASE = (ROOT / 'src/pages/page.cpp').read_text()


class PageNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        methods = []
        for name in ('StartNavigation', 'LaunchRequestedApplication', 'SelectApp', 'StartSelectedApp', 'CompleteArtworkAction'):
            text = function(SOURCE, 'Apps::' + name)
            text = re.sub(r'\b(m_\w+|root)\b', r'apps->\1', text)
            text = text.replace('this', 'apps')
            text = text.replace('Apps::' + name + '(', name + '(Apps *apps, ')
            text = text.replace('Apps *apps, )', 'Apps *apps)')
            text = text.replace('SelectApp(i)', 'SelectApp(apps, i)')
            text = text.replace('StartSelectedApp(i)', 'StartSelectedApp(apps, i)')
            text = text.replace('StartNavigation(true)', 'StartNavigation(apps, true)')
            methods.append(text)
        for name in ('NavigationFinished', 'NavigationTask', 'OnBack'):
            methods.append(function(SOURCE, 'Apps::' + name).replace('Apps::', ''))
        for name in ('stop_navigation', 'set_navigation', 'animate_navigation'):
            methods.append(function(SOURCE, name))
        cleanup = SOURCE.split('Apps::~Apps() {', 1)[1].split('    if (!MoonlightApp::Instance()', 1)[0]
        cleanup = re.sub(r'\b(m_\w+|root)\b', r'apps->\1', cleanup).replace('this', 'apps')
        methods.append('void cleanup(Apps *apps) {' + cleanup + '}')
        restore = BASE.split('    Base *current = GetCurrent();', 1)[1].split('    m_registered = false;', 1)[0]
        methods.append('void restore_current(void) { Apps *current = current_page();' + restore + '}')
        ready = SOURCE.split('case MOONLIGHT_EVENT_APPLICATIONS_READY:', 1)[1].split('        break;', 1)[0]
        ready = ready.replace('apps->ShowApps(event->result)', 'receive_apps(apps)')
        methods.append('void ready_result(Apps *apps) {' + ready + '}')
        code = '\n'.join(methods)
        code = re.sub(r'\(void\)\w+;', '', code)
        code = code.replace('static_cast<Apps *>(userdata)', '(Apps *)userdata')
        code = code.replace('MoonlightApp::Instance()->Connection().IsBusy()', 'is_busy()')
        code = code.replace('MoonlightApp::Instance()->Connection().Start', 'start_stream')
        code = code.replace('MoonlightApp::Instance()->Connection().ShowError', 'show_error')
        code = code.replace('MoonlightApp::Instance()->Applications().CancelArtwork()', 'cancel_artwork()')
        code = code.replace('MoonlightApp::Instance()->Applications().IsArtworkIdle()', 'artwork_idle()')
        code = code.replace('Base::GetCurrent()', 'current_page()').replace('Base::CloseCurrent()', 'force_close()')
        code = code.replace('paf::common::MainThreadCallList::Register', 'register_task')
        code = code.replace('paf::common::MainThreadCallList::Unregister', 'unregister_task')
        code = code.replace('apps->StartNavigation(', 'StartNavigation(apps, ')
        code = code.replace('apps->LaunchRequestedApplication()', 'LaunchRequestedApplication(apps)')
        code = code.replace('apps->IsTransitioning()', 'apps->m_transitioning')
        code = code.replace('current->IsTransitioning()', 'current->m_transitioning')
        code = code.replace('paf::math::v4(', 'make_vector(').replace('new paf::Timer(', 'make_timer(')
        code = re.sub(r'paf::Timer::(\w+)', r'\1', code)
        code = re.sub(r'paf::ui::Widget::(\w+)', r'\1', code)
        code = code.replace('paf::ui::AnimCB', 'int')
        code = re.sub(r'paf::(?:ui::(?:Widget|AnimListener|Handler|Event)|Timer) \*', 'int ', code)
        code = re.sub(r'void \*(\w+)', r'Apps *\1', code)
        code = code.replace('apps->root->SetActivate(', 'set_active(apps->root, ')
        code = code.replace('current->root->SetActivate(', 'set_active(current->root, ')
        code = re.sub(r'widget->(\w+)\(', r'widget_\1(widget, ', code)
        code = code.replace('delete apps;', 'destroy_apps(apps);')
        code = re.sub(r'delete (\w+);', r'free_timer(\1);', code)
        code = code.replace('--apps->m_navigation_pending;',
                            'apps->m_navigation_pending = apps->m_navigation_pending - 1;')
        code = code.replace('ClearArtwork()', 'clear_artwork()')
        code = code.replace('HideStatus()', 'hide_status()').replace('ShowEmptyState()', 'show_empty()')
        code = mock_ui_text(code)
        preamble = '''typedef int bool; typedef int int32_t;
        typedef struct {int id;} Application;
        typedef struct {int root, m_content, m_main_content, m_transitioning,
        m_closing, m_navigation_pending, m_apps_ready, m_livearea_application_id,
        m_launching, m_app_count, m_pending_app; Application m_apps[2];} Apps;'''
        unit = c_parser.CParser().parse(preamble + strip_directives(code))
        cls.functions = {node.decl.name: node for node in unit.ext if isinstance(node, c_ast.FuncDef)}
        cls.constants = {name: float(value) for name, value in
                         re.findall(r'const float (k\w+) = (-?[0-9.]+)f;', SOURCE)}

    def setUp(self):
        self.apps = dict(root=3, m_content=1, m_main_content=2, m_transitioning=0,
                         m_closing=0, m_navigation_pending=0, m_apps_ready=0,
                         m_livearea_application_id=42, m_launching=0, m_app_count=1, m_pending_app=0,
                         m_apps=[dict(id=42)])
        self.main = dict(root=4, m_transitioning=0)
        self.current = self.apps
        self.active, self.callbacks, self.tasks, self.transforms = {}, {}, {}, {}
        self.timers, self.freed, self.calls = [], [], []
        self.fail_timer, self.fail_property, self.busy = 0, None, False
        self.artwork_running = False
        self.artwork_cancelled = False
        self.artwork_cleared = 0
        self.values = dict(self.constants, NULL=0, false=0, true=1,
                           FUNC_CIRQ_OUT=23, FUNC_LINEAR=0, ArtworkTask=991,
                           ANIM_MOVE=0x10000, ANIM_ROT=0x10006, ANIM_META_ALPHA=0x10003,
                           make_timer=self.make_timer, free_timer=self.freed.append,
                           make_vector=lambda *args: args, current_page=lambda: self.current,
                           is_busy=lambda: self.busy,
                           cancel_artwork=lambda: setattr(self, 'artwork_cancelled', True),
                           clear_artwork=lambda: setattr(self, 'artwork_cleared', self.artwork_cleared + 1),
                           artwork_idle=lambda: not self.artwork_running, vita_debug_log=lambda *args: None,
                           register_task=lambda task, app: self.tasks.update({task: app}),
                           unregister_task=lambda task, app: self.tasks.pop(task, None),
                           set_active=lambda root, active: self.active.update({root: active}),
                           widget_SetPos=lambda widget, value, *args: self.property(widget, 'pos', value, bool(args)),
                           widget_SetMetaAlpha=lambda widget, value, *args: self.property(widget, 'alpha', value, bool(args)),
                           widget_SetRot=self.rotate, widget_KillAnim=self.kill,
                           destroy_apps=self.destroy, force_close=lambda: self.destroy(self.apps),
                           start_stream=lambda app_id: self.calls.append(('launch', app_id)) or 0,
                           show_error=lambda *args: self.calls.append('error'),
                           receive_apps=lambda app: app.update(m_apps_ready=0),
                           hide_status=lambda: None, show_empty=lambda: None)
        for name in self.functions:
            self.values[name] = lambda *args, name=name: self.invoke(name, *args)

    def expression(self, node, scope):
        if isinstance(node, c_ast.Constant) and node.type in ('float', 'double'):
            return float(node.value.rstrip('fF'))
        if isinstance(node, c_ast.BinaryOp) and node.op == '<=':
            return self.expression(node.left, scope) <= self.expression(node.right, scope)
        if isinstance(node, c_ast.UnaryOp) and node.op == 'p++':
            value = scope[node.expr.name]
            scope[node.expr.name] += 1
            return value
        if isinstance(node, c_ast.BinaryOp) and node.op == '*':
            return self.expression(node.left, scope) * self.expression(node.right, scope)
        return runtime_expression(node, scope)

    def execute(self, node, scope):
        if isinstance(node, c_ast.DeclList):
            for declaration in node.decls:
                self.execute(declaration, scope)
            return
        if isinstance(node, c_ast.UnaryOp):
            self.expression(node, scope)
            return
        return runtime_execute(node, scope)

    def invoke(self, name, *args):
        node = self.functions[name]
        scope = dict(self.values)
        parameters = node.decl.type.args.params if node.decl.type.args else []
        scope.update((param.name, value) for param, value in zip(parameters, args))
        with patch.object(runtime, 'expression', self.expression), patch.object(runtime, 'execute', self.execute):
            try:
                runtime.execute(node.body, scope)
            except runtime.Returned as result:
                return result.value

    def make_timer(self, duration, curve):
        self.timers.append((duration, curve))
        return 0 if len(self.timers) == self.fail_timer else len(self.timers)

    def property(self, widget, name, value, timed=False):
        if timed and self.fail_property == (widget, name):
            self.fail_property = None
            return -1
        self.transforms[widget, name] = value
        return 0

    def rotate(self, widget, value, *args):
        result = self.property(widget, 'rot', value, bool(args))
        if args and result == 0:
            self.callbacks[widget] = (args[-2], args[-1])
        return result

    def kill(self, widget, animation):
        if animation == 0x10006:
            self.callbacks.pop(widget, None)

    def finish(self, widget):
        callback, app = self.callbacks.pop(widget)
        callback(0, 0, widget, app, 0)

    def poll(self):
        self.invoke('NavigationTask', self.apps)
        if self.apps['m_pending_app']: self.invoke('CompleteArtworkAction', self.apps)

    def destroy(self, app):
        self.invoke('cleanup', app)
        self.calls.append('destroy')
        self.current = self.main
        self.invoke('restore_current')

    def test_open_waits_for_both_native_callbacks_and_ready_apps_before_launch(self):
        for ready_early in (False, True):
            self.setUp()
            self.apps['m_apps_ready'] = ready_early
            self.invoke('StartNavigation', self.apps, False)
            self.assertFalse(self.active[3])
            self.invoke('LaunchRequestedApplication', self.apps)
            self.assertEqual(self.calls, [])
            self.invoke('restore_current')  # Removing Pairing from mid-stack must keep Apps blocked.
            self.assertFalse(self.active[3])
            self.finish(1)
            self.poll()
            self.assertTrue(self.apps['m_transitioning'])
            self.finish(2)
            self.poll()
            self.assertTrue(self.active[3])
            self.assertEqual(self.calls, [('launch', 42)] if ready_early else [])
            self.apps['m_apps_ready'] = 1
            self.invoke('LaunchRequestedApplication', self.apps)
            self.invoke('LaunchRequestedApplication', self.apps)
            self.invoke('CompleteArtworkAction', self.apps)
            self.assertEqual(self.calls, [('launch', 42)])
            self.assertEqual(self.transforms[2, 'alpha'], 0.15)
            self.assertEqual(self.timers, [(500, 23), (500, 23), (400, 0)] * 2)
    def test_ready_result_waits_for_open_and_back_waits_before_destroying(self):
        self.apps['m_apps_ready'] = 1
        self.apps['m_livearea_application_id'] = 0
        self.invoke('StartNavigation', self.apps, False)
        self.invoke('OnBack', 0, 0, 0, self.apps)
        self.assertFalse(self.apps['m_closing'])
        self.finish(2)
        self.finish(1)
        self.poll()
        self.busy = True
        self.invoke('OnBack', 0, 0, 0, self.apps)
        self.assertFalse(self.apps['m_closing'])
        self.busy = False
        self.invoke('OnBack', 0, 0, 0, self.apps)
        self.invoke('CompleteArtworkAction', self.apps)
        self.assertTrue(self.apps['m_closing'])
        self.finish(2)
        self.poll()
        self.assertEqual(self.calls, [])
        self.finish(1)
        self.assertEqual(self.calls, [])  # Never destroy inside an animation callback.
        self.poll()
        self.assertEqual(self.calls, ['destroy'])
        self.assertTrue(self.active[4])
        self.assertEqual(self.transforms[2, 'pos'], (-480, 0, 0))
        self.assertEqual(self.transforms[2, 'rot'], (0, 0, 0))
        self.assertEqual(self.transforms[2, 'alpha'], 1)
        self.assertFalse(self.tasks)

    def test_allocation_and_property_errors_finish_without_input_or_callback_leaks(self):
        for failure in ('timer', 'pos', 'alpha', 'rot'):
            with self.subTest(failure=failure):
                self.setUp()
                if failure == 'timer': self.fail_timer = 2
                else: self.fail_property = (1, failure)  # Second container, after Main started.
                self.invoke('StartNavigation', self.apps, False)
                self.assertEqual(self.apps['m_navigation_pending'], 0)
                self.assertFalse(self.callbacks)
                self.poll()
                self.assertTrue(self.active[3])
                self.assertFalse(self.apps['m_transitioning'])
                if failure == 'timer': self.assertEqual(self.freed, [1, 0, 3])
        self.setUp()
        self.invoke('StartNavigation', self.apps, False)
        self.invoke('ready_result', self.apps)  # An invalid list response cancels the one-shot target.
        self.assertEqual(self.apps['m_livearea_application_id'], 0)
        self.finish(1)
        self.finish(2)
        self.poll()
        self.assertEqual(self.calls, [])

    def test_forced_close_cancels_callbacks_and_restores_main_before_reactivation(self):
        self.invoke('StartNavigation', self.apps, False)
        self.destroy(self.apps)
        self.assertFalse(self.callbacks)
        self.assertFalse(self.tasks)
        self.assertEqual(self.transforms[2, 'alpha'], 1)
        self.assertTrue(self.active[4])
        self.invoke('NavigationFinished', 0, 0, 0, self.apps, 0)
        self.assertEqual(self.apps['m_navigation_pending'], 2)  # Cancelled completion ignored.

    def test_launch_and_back_wait_for_cancelled_artwork_cleanup(self):
        for pending in (42, -1):
            with self.subTest(pending=pending):
                self.setUp()
                self.artwork_running = True
                self.apps['m_livearea_application_id'] = 0
                if pending > 0: self.invoke('SelectApp', self.apps, 0)
                else: self.invoke('OnBack', 0, 0, 0, self.apps)
                self.assertTrue(self.artwork_cancelled)
                self.assertTrue(self.apps['m_transitioning'])
                self.assertFalse(self.active[3])
                self.invoke('CompleteArtworkAction', self.apps)
                self.assertEqual(self.apps['m_pending_app'], pending)
                self.assertEqual(self.calls, [])
                self.assertEqual(self.artwork_cleared, 0)
                self.artwork_running = False
                self.invoke('CompleteArtworkAction', self.apps)
                self.assertEqual(self.apps['m_pending_app'], 0)
                self.assertEqual(self.artwork_cleared, 1)
                self.assertEqual(self.calls, [('launch', 42)] if pending > 0 else [])
                self.assertEqual(bool(self.apps['m_closing']), pending == -1)
                self.invoke('CompleteArtworkAction', self.apps)
                self.assertEqual(self.artwork_cleared, 1)

    def test_invalid_app_id_never_strands_input_in_artwork_wait(self):
        self.apps['m_apps'][0]['id'] = 0
        self.active[3] = True
        self.invoke('SelectApp', self.apps, 0)
        self.assertEqual(self.calls, ['error'])
        self.assertTrue(self.active[3])
        self.assertFalse(self.apps['m_pending_app'])
        self.assertFalse(self.apps['m_transitioning'])

    def test_resource_pivot_backdrop_and_list_bounds_preserve_the_parent_strip(self):
        resource = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').getroot()
        for page, content in (('page_main', 'plane_main_content'), ('page_apps', 'plane_apps_content')):
            node = resource.find(f"./pagetable/page[@id='{page}']/plane[@id='{content}']/layout_hint")
            self.assertEqual(node.get('size'), '960, 544')
            self.assertEqual(node.get('align'), '1, 0')
            self.assertEqual(node.get('pos'), '-480, 0')
        apps = resource.find("./pagetable/page[@id='page_apps']")
        self.assertFalse(apps.findall(".//plane[@texture='_bg_texture']"))
        content = apps.find("plane[@id='plane_apps_content']")
        self.assertIsNotNone(content.find("template_ref[@id='apps_title_ref']"))
        self.assertIsNone(apps.find("template_ref[@id='apps_title_ref']"))
        for template, size in (('template_list_view_generic', '730, 448'),
                               ('template_app_list_item', '730, 90')):
            hint = resource.find(f"./templatetable/template[@id='{template}']/*/layout_hint")
            self.assertEqual(hint.get('size'), size)
        self.assertIn('Base::Find("page_main")', SOURCE)
        self.assertIn('if (!IsValid()) return;', SOURCE[:SOURCE.index('StartNavigation(false);')])


runtime_expression = runtime.expression
runtime_execute = runtime.execute

if __name__ == '__main__':
    unittest.main()
