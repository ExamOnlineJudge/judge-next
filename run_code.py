#!/usr/bin/env python3
import io
import json
import os
import re
import subprocess
import sys
import traceback
import yaml

# Add judge-server to sys.path
JUDGE_DIR = os.path.dirname(os.path.abspath(__file__))
if JUDGE_DIR not in sys.path:
    sys.path.insert(0, JUDGE_DIR)

from dmoj import judgeenv
from dmoj.error import CompileError

# Load judge configuration
config_path = os.path.join(JUDGE_DIR, "judge.yml")
if os.path.exists(config_path):
    with open(config_path) as f:
        conf = yaml.safe_load(f)
    judgeenv.env.update(conf)
judgeenv.skip_self_test = True

# Silence stdout during executor loading
_stdout = sys.stdout
sys.stdout = io.StringIO()
from dmoj import executors
executors.load_executors()
sys.stdout = _stdout

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    if not text:
        return ""
    return ANSI_ESCAPE_RE.sub("", text)

LANG_MAP = {
    # C++ (GCC)
    "cpp26": ["CPP26", "CPP23", "CPP20"],
    "cpp23": ["CPP23", "CPP20"],
    "cpp20": ["CPP20", "CPP17"],
    "cpp17": ["CPP17", "CPP14"],
    "cpp14": ["CPP14", "CPP11"],
    "cpp11": ["CPP11", "CPP03"],
    "cpp03": ["CPP03"],
    "cpp": ["CPP20", "CPP17", "CPP14", "CPP11"],
    "c++": ["CPP20", "CPP17", "CPP14", "CPP11"],

    # C++ (Clang)
    "clpp26": ["CLPP26", "CLPP23", "CLPP20"],
    "clpp23": ["CLPP23", "CLPP20"],
    "clpp20": ["CLPP20", "CLPP17"],
    "clpp17": ["CLPP17", "CLPP14"],
    "clpp14": ["CLPP14", "CLPP11"],
    "clpp11": ["CLPP11"],
    "clpp03": ["CLANG"],

    # C (GCC)
    "c23": ["C23", "C11"],
    "c17": ["C11", "C"],
    "c11": ["C11", "C"],
    "c99": ["C", "C11"],
    "c89": ["C"],
    "c": ["C11", "C23", "C"],

    # C (Clang)
    "clang23": ["CLANG"],
    "clang17": ["CLANG"],
    "clang11": ["CLANG"],
    "clang99": ["CLANG"],
    "clang89": ["CLANG"],
    "clang": ["CLANG"],

    # Python & PyPy
    "python3": ["PY3"],
    "python": ["PY3"],
    "py": ["PY3"],
    "pypy3": ["PYPY3", "PY3"],
    "pypy": ["PYPY3", "PY3"],
    "python2": ["PY2", "PY3"],
    "py2": ["PY2", "PY3"],
    "pypy2": ["PY2", "PY3"],

    # Pascal
    "pas_fpc": ["PAS"],
    "pas_tp": ["PAS"],
    "pas_delphi": ["PAS"],
    "pascal": ["PAS"],
    "pas": ["PAS"],

    # Other runtimes
    "java": ["JAVA", "JAVA8"],
    "js": ["NODEJS", "V8JS"],
    "javascript": ["NODEJS", "V8JS"],
    "node": ["NODEJS"],
    "kotlin": ["KOTLIN"],
    "perl": ["PERL"],
    "awk": ["AWK"],
    "sed": ["SED"],
    "tcl": ["TCL"]
}

def resolve_executor(lang_id: str):
    lang_id_lower = lang_id.lower().strip()
    candidates = LANG_MAP.get(lang_id_lower, [lang_id.upper()])
    for cand in candidates:
        if cand in executors.executors:
            return executors.executors[cand].Executor
    return None

def execute_code(req: dict) -> dict:
    lang = req.get("language", "cpp")
    code = req.get("code", "")
    stdin_data = req.get("stdin", "").encode("utf-8")
    time_limit = float(req.get("time_limit", 5.0))
    # Default 256MB RAM so JVM and V8 can initialize their virtual memory spaces
    memory_limit = int(req.get("memory_limit", 262144))

    ExecutorClass = resolve_executor(lang)
    if not ExecutorClass:
        return {
            "success": False,
            "status": "Unsupported Language",
            "compile_error": f"No available executor for language '{lang}'",
            "stdout": "",
            "stderr": "",
            "time": 0.0,
            "memory": 0,
            "exit_code": 1
        }

    exc = None
    try:
        exc = ExecutorClass("run", code.encode("utf-8"))
    except CompileError as e:
        err_msg = str(e.message if hasattr(e, 'message') else e)
        return {
            "success": False,
            "status": "Compilation Error",
            "compile_error": strip_ansi(err_msg),
            "stdout": "",
            "stderr": "",
            "time": 0.0,
            "memory": 0,
            "exit_code": 1
        }
    except Exception as e:
        return {
            "success": False,
            "status": "Compilation Error",
            "compile_error": strip_ansi(traceback.format_exc()),
            "stdout": "",
            "stderr": "",
            "time": 0.0,
            "memory": 0,
            "exit_code": 1
        }

    try:
        proc = exc.launch(
            time=time_limit,
            memory=memory_limit,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = proc.communicate(stdin_data)
        
        status = "Success"
        if proc.is_tle:
            status = "Time Limit Exceeded"
        elif proc.is_mle:
            status = "Memory Limit Exceeded"
        elif proc.is_rte or proc.is_ir:
            status = "Runtime Error"
        elif proc.returncode != 0 and not proc.is_tle and not proc.is_mle:
            status = f"Runtime Error (exit {proc.returncode})"

        return {
            "success": status == "Success",
            "status": status,
            "compile_error": None,
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": strip_ansi(stderr_bytes.decode("utf-8", errors="replace")),
            "time": round(proc.execution_time or 0.0, 4),
            "memory": int(proc.max_memory or 0),
            "exit_code": proc.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "status": "Internal Error",
            "compile_error": None,
            "stdout": "",
            "stderr": strip_ansi(traceback.format_exc()),
            "time": 0.0,
            "memory": 0,
            "exit_code": 1
        }
    finally:
        if exc:
            try:
                exc.cleanup()
            except Exception:
                pass

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            req = {}
        else:
            req = json.loads(input_data)
        res = execute_code(req)
        print(json.dumps(res))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "status": "Error",
            "compile_error": strip_ansi(str(e)),
            "stdout": "",
            "stderr": strip_ansi(traceback.format_exc()),
            "time": 0.0,
            "memory": 0,
            "exit_code": 1
        }))

if __name__ == "__main__":
    main()
