"""Exercise build argument selection only; never run build.sh's main body or tools."""
from pathlib import Path
import subprocess
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / 'build.sh').read_text()
HELPERS = SCRIPT.split('\nparse_arguments "$@"', 1)[0]


class BuildProfiles(unittest.TestCase):
    def parse(self, *args):
        return subprocess.run(
            ['bash', '-c', HELPERS + '\nparse_arguments "$@"\nprintf "%s\\n" "$BUILD_SELECTION" "${CMAKE_ARGS[@]}"',
             'build-profile-test', *args], capture_output=True, text=True)

    def test_system_default_and_explicit_profile_selection(self):
        for args, profile in (
            ((), 'system'),
            (('-DMOONLIGHT_HEAP_TRACE=ON',), 'system'),
            (('-DMOONLIGHT_SYSTEM_APP=OFF',), 'normal'),
            (('-D', 'MOONLIGHT_SYSTEM_APP:BOOL=FALSE'), 'normal'),
            (('-DMOONLIGHT_SYSTEM_APP=ON',), 'system'),
            (('-DMOONLIGHT_SYSTEM_APP=OFF', '-DMOONLIGHT_SYSTEM_APP=ON'), 'system'),
            (('-DMOONLIGHT_SYSTEM_APP=ON', '-DMOONLIGHT_SYSTEM_APP=OFF'), 'normal'),
        ):
            with self.subTest(args=args):
                result = self.parse(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [profile, *args])

    def test_missing_cmake_definition_stops_parsing(self):
        result = self.parse('-D')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('-D requires a CMake definition', result.stderr)


if __name__ == '__main__':
    unittest.main()
