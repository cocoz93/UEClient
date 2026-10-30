"""Run one project-owned editor script offscreen without operating the OS cursor."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from render_lock import render_slot

PROJECT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--engine", type=Path, default=Path("C:/Program Files/Epic Games/UE_5.8"))
    parser.add_argument("--fps", type=int, choices=(30, 60), default=60)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--baseline", type=Path)
    # Load the DebugGame project modules - a separate DLL a user editor does not hold, so a fresh build can be tested while that
    # editor stays open (the Development DLL it loaded is locked and the link fails with LNK1104). UnrealEditor.exe ignores -debug
    # (the launch module fixes the configuration when it is compiled); the DebugGame target's own launcher is
    # UnrealEditor-Win64-DebugGame.exe (Binaries/Win64/LearnTopDownEditor-Win64-DebugGame.target "Launch").
    parser.add_argument("--debug-game", action="store_true")
    arguments = parser.parse_args()
    script = arguments.script.resolve()
    output = arguments.output.resolve()
    if not script.is_relative_to(PROJECT / "Tools/CharacterPipeline") or not script.is_file():
        raise ValueError("Editor scripts must be existing CharacterPipeline tools")
    if not output.is_relative_to(PROJECT / "Saved/QA"):
        raise ValueError("Editor output must be inside this project Saved/QA")
    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, SPARROW_QA_OUTPUT=str(output), SPARROW_QA_FPS=str(arguments.fps))
    if arguments.baseline:
        environment['CHARACTER_PIPELINE_BASELINE'] = str(arguments.baseline.resolve())
    environment["UE-LocalDataCachePath"] = str(PROJECT / "Saved/CharacterPipelineDDC")
    log = output / "editor.log"
    launcher = "UnrealEditor-Win64-DebugGame.exe" if arguments.debug_game else "UnrealEditor.exe"
    editor_arguments = [str(arguments.engine / "Engine/Binaries/Win64" / launcher),
                        str(PROJECT / "LearnTopDown.uproject"), "-RenderOffscreen", "-unattended",
                        "-nop4", "-nosplash", "-NoLiveCoding", "-NoAutoSave", "-windowed",
                        "-ResX=1280", "-ResY=960", "-UseFixedTimeStep", f"-FPS={arguments.fps}",
                        "-AudioMixer", "-ddc=InstalledNoZenLocalFallback",
                        "-ShaderWorkingDir=" + str(PROJECT / "Saved/ShaderWork"), "-abslog=" + str(log)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    command_line = subprocess.list2cmdline(editor_arguments) + ' -ExecCmds="py ' + script.as_posix() + '"'
    with render_slot(PROJECT):
        process = subprocess.Popen(command_line, env=environment, startupinfo=startup)
        (output / "process.json").write_text(json.dumps({"pid": process.pid, "script": str(script),
                                                       "log": str(log), "fps": arguments.fps}), encoding="utf-8")
        print(json.dumps({"pid": process.pid, "output": str(output)}), flush=True)
        try:
            return_code = process.wait(timeout=arguments.timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=30)
            (output / "process-result.json").write_text(json.dumps({"timed_out": True, "return_code": process.returncode}), encoding="utf-8")
            raise RuntimeError("This task's own unattended editor timed out; inspect " + str(log))
        (output / "process-result.json").write_text(json.dumps({"timed_out": False, "return_code": return_code}), encoding="utf-8")
        print(json.dumps({"return_code": return_code, "log": str(log)}), flush=True)
        return return_code



if __name__ == "__main__":
    raise SystemExit(main())
