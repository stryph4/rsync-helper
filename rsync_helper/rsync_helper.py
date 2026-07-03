"""Lightweight entry point for the rsync_helper package.

This module supports two invocation methods:
- As a package: `python -m rsync_helper.rsync_helper` (preferred).
- Direct script execution: `python rsync_helper/rsync_helper.py`.

When executed as a script the package-relative import (`from .ui`) will
fail because Python does not know the parent package. We detect that
case and fall back to adding the package parent directory to `sys.path`
so the absolute import `rsync_helper.ui` works.
"""

try:
    # Preferred when run as a package: python -m rsync_helper.rsync_helper
    from .ui import run_app, show_gtk_install_instructions_dialog, build_ui
    from . import logger
except Exception:
    # Fallback when executed directly as a script.
    import os
    import sys

    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_parent not in sys.path:
        sys.path.insert(0, pkg_parent)
    from rsync_helper.ui import run_app, show_gtk_install_instructions_dialog, build_ui
    from rsync_helper import logger


if __name__ == "__main__":
    import sys
    import os

    if "--test" in sys.argv:
        # Run unit tests first, then open the GTK install dialog for manual testing.
        import subprocess

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Run pytest with JUnit XML output so we can parse structured results.
        import tempfile
        import xml.etree.ElementTree as ET
        import os

        with tempfile.NamedTemporaryFile(prefix="pytest-junit-", suffix=".xml", delete=False) as tf:
            xml_path = tf.name

        cmd = [sys.executable, "-m", "pytest", "-q", f"--junitxml={xml_path}"]
        proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)

        # Print pytest stdout/stderr to the console for developer visibility
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)

        # Try to parse the junit xml and log per-test results and a summary.
        test_lines = []
        passed = failed = skipped = 0
        if os.path.exists(xml_path):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                # Find all testcase elements
                testcases = root.findall('.//testcase')
                for tc in testcases:
                    name = tc.attrib.get('name') or tc.attrib.get('classname') or '<unknown>'
                    # Check for failure/error/skipped children
                    status = 'Pass'
                    if tc.find('failure') is not None or tc.find('error') is not None:
                        status = 'Fail'
                        failed += 1
                    elif tc.find('skipped') is not None:
                        status = 'Skipped'
                        skipped += 1
                    else:
                        passed += 1
                    test_lines.append(f"{name} : {status}")
            except Exception:
                print('Failed to parse pytest junit xml:', xml_path)
        else:
            print('No junit xml produced by pytest')

        summary_line = f"Total Tests: {passed} passed, {failed} failed, {skipped} skipped"

        # Clean up junit xml file
        try:
            os.remove(xml_path)
        except Exception:
            pass
        # Build the full application UI so the main window is populated,
        # then write the test results into the UI log and show the install dialog.
        win = build_ui()

        # Write per-test lines and summary to the UI log via `logger.log`.
        try:
            from . import logger as _logger
        except Exception:
            _logger = None

        for line in test_lines:
            if _logger is not None:
                try:
                    _logger.log(line)
                except Exception:
                    pass

        if _logger is not None:
            try:
                _logger.log(summary_line)
            except Exception:
                pass

        # Show the install dialog for manual testing
        show_gtk_install_instructions_dialog(win)
        win.mainloop()
    else:
        run_app()