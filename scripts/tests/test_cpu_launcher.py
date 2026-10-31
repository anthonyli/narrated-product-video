import os
from pathlib import Path
import subprocess
import tempfile
import unittest
class LauncherTests(unittest.TestCase):
    def test_environment_precedes_python_start(self):
        launcher=Path(__file__).resolve().parents[1]/'run_cpu_voice.sh'
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'fake-python'
            fake.write_text('#!/bin/sh\nprintf "%s|%s|%s|%s" "$ORT_DISABLE_TELEMETRY" "$HF_HUB_OFFLINE" "$TRANSFORMERS_OFFLINE" "$1"\n')
            fake.chmod(0o700)
            env=dict(os.environ,PYTHON=str(fake));env.pop('ORT_DISABLE_TELEMETRY',None)
            r=subprocess.run([str(launcher),'--segments','--help'],env=env,capture_output=True,text=True,check=True)
            self.assertTrue(r.stdout.startswith('1|1|1|'))
            self.assertTrue(r.stdout.endswith('/local_voice_segments.py'))
if __name__=='__main__':unittest.main()
