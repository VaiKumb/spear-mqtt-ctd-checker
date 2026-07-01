import glob
import os
import shutil
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildProtobuf(build_py):
    """Generate *_pb2.py from .proto files using protoc."""

    def run(self):
        if not shutil.which("protoc"):
            raise SystemExit(
                "\n"
                "ERROR: 'protoc' (the Protocol Buffers compiler) was not found.\n"
                "Install it before running pip install:\n"
                "\n"
                "  macOS:   brew install protobuf\n"
                "  Ubuntu:  sudo apt install protobuf-compiler\n"
            )

        root = os.path.dirname(os.path.abspath(__file__))
        proto_dir = os.path.join(root, "proto")
        out_dir = os.path.join(root, "src", "spear_mqtt_ctd")

        proto_files = glob.glob(os.path.join(proto_dir, "*.proto"))
        if not proto_files:
            raise SystemExit(f"ERROR: No .proto files found in {proto_dir}")

        include_paths = [proto_dir]
        system_include = "/usr/include"
        if os.path.isdir(os.path.join(system_include, "google", "protobuf")):
            include_paths.append(system_include)

        cmd = ["protoc"]
        for path in include_paths:
            cmd.append(f"--proto_path={path}")
        cmd.append(f"--python_out={out_dir}")
        cmd.extend(proto_files)

        subprocess.check_call(cmd)
        super().run()


setup(cmdclass={"build_py": BuildProtobuf})
