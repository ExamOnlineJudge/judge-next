#!/usr/bin/env python3
import io
import json
import os
import pty
import re
import resource
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import time

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
MAX_MEMORY_KB = 256 * 1024 # 256 MB hard limit
TIMEOUT_LIMIT = 5.0 # 5.0 seconds CPU/active compute limit
SUPER_OPT = ["-O3", "-march=native", "-mtune=native", "-pipe"]

def strip_ansi(text: str) -> str:
    if not text:
        return ""
    return ANSI_ESCAPE_RE.sub("", text)

def send_msg(msg_type: str, data: dict):
    payload = {"type": msg_type, **data}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()

def validate_code_security(lang: str, code: str) -> str | None:
    l = lang.lower().strip()

    # ARM Assembly security
    if "arm" in l:
        banned_arm = [
            (r'\b(svc\s+#?\d+|swi\s+#?\d+)\b', "Direct ARM kernel supervisor syscalls (use standard libc functions like printf/scanf/puts)"),
            (r'\b(msr\s+|mrs\s+|mcr\s+|mrc\s+)\b', "System coprocessor / control register instructions"),
            (r'\b(wfe|wfi|smc|hvc|eret)\b', "ARM privileged execution mode / hypervisor instructions"),
        ]
        for pat, desc in banned_arm:
            if re.search(pat, code, re.IGNORECASE):
                return f"Security Violation: {desc} is blocked in sandbox."
        return None

    # x86 Assembly security inspection
    if l.startswith("asm") or l in ("nasm", "yasm", "gas", "fasm"):
        banned_asm = [
            (r'\b(int\s+0x80|syscall|sysenter)\b', "Direct kernel system calls (use standard libc functions like printf/scanf/puts)"),
            (r'\b(cli|sti|hlt|invd|wbinvd|lidt|lgdt|ltr|lldt|mov\s+cr\d|mov\s+dr\d)\b', "Privileged / Ring 0 hardware CPU instructions"),
            (r'\b(rdmsr|wrmsr|cpuid|clflush)\b', "Hardware MSR and cache timing instructions"),
            (r'(?i)^\s*(in|out|insb|insw|insd|outsb|outsw|outsd)\s+', "Direct port I/O hardware instructions"),
        ]
        for pat, desc in banned_asm:
            if re.search(pat, code, re.IGNORECASE | re.MULTILINE):
                return f"Security Violation: {desc} is blocked in sandbox."
        return None

    # Generic inline assembly in high level languages
    if any(l.startswith(p) for p in ("c", "cpp", "clpp", "clang", "d", "objc")):
        if re.search(r'__asm__|__asm\s*\(|asm\s+volatile', code, re.IGNORECASE):
            return "Inline assembly and direct CPU instructions are blocked."

    # -------------------------------------------------------------
    # Universal Custom Compiler Argument & Pragma Injections Filter
    # -------------------------------------------------------------
    # C / C++ / Objective-C / D custom pragma & attribute overrides
    if any(l.startswith(p) for p in ("c", "cpp", "clpp", "clang", "objc", "d")):
        banned_pragmas = [
            (r'#\s*pragma\s+(GCC|clang)?\s*(optimize|target|attribute|config|option|link|comment)\b', "Custom compiler pragma / optimization / linking injection (#pragma)"),
            (r'__attribute__\s*\(\s*\(\s*(optimize|target|section|naked|constructor|destructor)\b', "Custom compiler attribute injection (__attribute__)"),
        ]
        for pat, desc in banned_pragmas:
            if re.search(pat, code, re.IGNORECASE):
                return f"Custom Argument Violation: {desc} is forbidden."

    # Pascal custom compiler directives
    if l.startswith("pas"):
        banned_pas_directives = [
            (r'\{\s*\$\s*(optimization|opt|link|smartlink|apptype|coperators|macro|dynamiclist|pic|setpeflags)\b', "Custom Pascal compiler directive injection"),
            (r'\{\s*\$\s*O[+-0-9]', "Custom Pascal optimization switch ({$O})"),
            (r'\{\s*\$\s*L\s+[^\}]+\}', "Custom Pascal external object linking directive ({$L})"),
        ]
        for pat, desc in banned_pas_directives:
            if re.search(pat, code, re.IGNORECASE):
                return f"Custom Argument Violation: {desc} is forbidden."

    # Go compiler & linker directives
    if l.startswith("go"):
        banned_go = [
            (r'//go:(cgo_ldflag|cgo_cflags|linkname|cgo_import_dynamic|cgo_export_dynamic|build)', "Custom Go compiler/linker directive (//go:...)"),
        ]
        for pat, desc in banned_go:
            if re.search(pat, code):
                return f"Custom Argument Violation: {desc} is forbidden."

    # Rust compiler features & link flags
    if l.startswith("rust"):
        banned_rs = [
            (r'#!\[feature\(', "Custom Rust unstable feature flag (#![feature(...)] )"),
            (r'#\[(link_args|link_name)\s*=', "Custom Rust linker flag injection (#[link_args] )"),
        ]
        for pat, desc in banned_rs:
            if re.search(pat, code):
                return f"Custom Argument Violation: {desc} is forbidden."

    # C# / F# / VB custom unmanaged / DllImport
    if any(l.startswith(p) for p in ("cs", "csharp", "fs", "fsharp", "vb")):
        banned_net = [
            (r'\[\s*(System\.Runtime\.InteropServices\.)?DllImport\b', "Custom native library import ([DllImport])"),
            (r'\[\s*assembly\s*:\s*', "Custom assembly-level metadata / linker attribute"),
        ]
        for pat, desc in banned_net:
            if re.search(pat, code, re.IGNORECASE):
                return f"Custom Argument Violation: {desc} is forbidden."

    # PHP runtime configuration overrides
    if l.startswith("php"):
        if re.search(r'\b(ini_set|ini_alter|dl)\s*\(', code, re.IGNORECASE):
            return "Custom Argument Violation: Dynamic PHP runtime configuration / extension loading (ini_set/dl) is forbidden."

    # JS / TS V8 flags & process args
    if any(l.startswith(p) for p in ("js", "javascript", "ts", "typescript", "node")):
        if re.search(r'\b(v8\.setFlagsFromString|process\.argv|worker_threads|child_process)\b', code):
            return "Custom Argument Violation: Runtime flag injection / worker thread spawning is forbidden."

    # -------------------------------------------------------------
    # Low-Level Security & System Sandboxing
    # -------------------------------------------------------------
    if any(l.startswith(p) for p in ("c", "cpp", "clpp", "clang", "objc", "d")):
        banned = [
            (r'\b(pthread_create|pthread_join|std::thread|std::async|std::future|std::jthread|omp_get_thread_num|#pragma\s+omp)\b', "Multi-threading (pthreads, std::thread, OpenMP)"),
            (r'\b(fork|vfork|clone|clone3|daemon)\s*\(', "Process creation / fork operations"),
            (r'\b(system|popen|execve|execv|execl|execlp|execvp)\s*\(', "Shell command and sub-process execution"),
            (r'\b(ptrace|personality|chroot|pivot_root|mount|umount|reboot|setuid|setgid)\s*\(', "Low-level system and kernel calls"),
            (r'#\s*include\s*<sys/(socket|mman|ptrace|reboot|mount|types|ipc|shm|msg|sem)\.h>', "Low-level OS, mman, and IPC headers"),
            (r'#\s*include\s*<(netinet/in|arpa/inet|sys/un|netdb)\.h>', "Raw network socket headers"),
            (r'#\s*include\s*<(pthread|thread|future)\.h?>', "Multi-threading headers (<thread>, <pthread.h>, <future>)"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif any(l.startswith(p) for p in ("py", "cpython")):
        banned = [
            (r'\b(threading|multiprocessing|concurrent\.futures|_thread|asyncio)\b', "Multi-threading and asynchronous concurrency modules"),
            (r'\b(socket|http\.client|urllib\.request|requests|httpx)\b', "Network sockets and HTTP connection libraries"),
            (r'\b(subprocess|os\.system|os\.popen|os\.exec|os\.fork|os\.kill|pty)\b', "Subprocess spawning and low-level OS management"),
            (r'\bctypes\b', "Low-level C-types memory manipulation"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif l.startswith("go"):
        banned = [
            (r'\b(os/exec|syscall|net|net/http)\b', "System execution and network socket packages"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif l.startswith("rust"):
        banned = [
            (r'\b(std::process::Command|std::net::TcpStream|std::net::UdpSocket|std::thread::spawn)\b', "Process spawning, raw networking, and multi-threading"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif l.startswith("php"):
        banned = [
            (r'\b(exec|system|passthru|shell_exec|popen|proc_open|pcntl_fork|fsockopen|pfsockopen)\b', "Low-level execution and raw network sockets"),
        ]
        for pat, desc in banned:
            if re.search(pat, code, re.IGNORECASE):
                return f"Security Violation: {desc} is blocked."

    elif any(l.startswith(p) for p in ("java", "jdk", "kotlin")):
        banned = [
            (r'\b(java\.lang\.Thread|implements\s+Runnable|extends\s+Thread|java\.util\.concurrent|ForkJoinPool|ThreadPoolExecutor)\b', "Multi-threading and concurrency frameworks"),
            (r'\b(ProcessBuilder|Runtime\.getRuntime\(\)\.exec|java\.lang\.Process)\b', "Process spawning and system execution"),
            (r'\b(java\.net\.Socket|java\.net\.ServerSocket|java\.net\.URL|java\.net\.http)\b', "Network and raw socket access"),
            (r'\b(sun\.misc\.Unsafe|jdk\.internal\.misc\.Unsafe)\b', "Low-level memory manipulation (Unsafe)"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif any(l.startswith(p) for p in ("cs", "csharp", "fs", "fsharp", "vb")):
        banned = [
            (r'\b(System\.Threading|System\.Diagnostics\.Process|System\.Net\.Sockets)\b', "Multi-threading, process execution, and raw sockets"),
        ]
        for pat, desc in banned:
            if re.search(pat, code):
                return f"Security Violation: {desc} is blocked."

    elif l.startswith("pas"):
        banned = [
            (r'\buses\s+.*?\b(cthreads|pthreads|sockets|dos|process|baseunix)\b', "Low-level system and threading units"),
            (r'\b(fpFork|fpExecve|fpKill|fpSystem)\b', "Low-level process calls"),
        ]
        for pat, desc in banned:
            if re.search(pat, code, re.IGNORECASE):
                return f"Security Violation: {desc} is blocked."

    return None

def get_process_memory_stats(pid: int, lang: str) -> tuple[int, int]:
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            lines = f.readlines()
        data = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                data[parts[0].strip()] = parts[1].strip()

        rss = int(data.get("VmRSS", "0 kB").split()[0])
        rss_anon = int(data.get("RssAnon", "0 kB").split()[0])
        vm_data = int(data.get("VmData", "0 kB").split()[0])
        vm_stk = int(data.get("VmStk", "0 kB").split()[0])
        vm_exe = int(data.get("VmExe", "0 kB").split()[0])

        actual_phys_rss_kb = max(rss, rss_anon)
        lang_lower = lang.lower().strip()

        if any(lang_lower.startswith(p) for p in ("c", "cpp", "clpp", "clang", "pas", "asm", "nasm", "yasm", "gas", "fasm", "rust", "go", "d", "objc", "llvm")):
            code_mem = max(rss_anon, vm_stk + vm_exe)
            return max(16, code_mem), actual_phys_rss_kb

        elif any(lang_lower.startswith(p) for p in ("py", "cpython", "lua")):
            baseline = 16384 if "pypy" in lang_lower else 4096
            code_mem = max(32, rss_anon - baseline if rss_anon > baseline else max(32, rss_anon // 4))
            return code_mem, actual_phys_rss_kb

        elif any(lang_lower.startswith(p) for p in ("java", "jdk", "kotlin", "cs", "csharp", "fs", "vb", "dart")):
            baseline = 16384
            code_mem = max(64, rss_anon - baseline if rss_anon > baseline else max(64, rss_anon // 8))
            return code_mem, actual_phys_rss_kb

        elif any(lang_lower.startswith(p) for p in ("js", "javascript", "node", "ts", "typescript", "php")):
            baseline = 20480
            code_mem = max(64, rss_anon - baseline if rss_anon > baseline else max(64, rss_anon // 8))
            return code_mem, actual_phys_rss_kb

        else:
            return max(16, rss_anon), actual_phys_rss_kb
    except Exception:
        return 0, 0

FPC_UNITS = "-Fu/usr/lib/x86_64-linux-gnu/fpc/3.2.2/units/x86_64-linux/*"

def compile_source(lang: str, code: str, temp_dir: str):
    l = lang.lower().strip()

    # C# (Mono)
    if l in ("cs_mono", "csharp_mono", "mono_cs"):
        src = os.path.join(temp_dir, "Program.cs")
        exe = os.path.join(temp_dir, "Program.exe")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/mcs", "-optimize+", src, f"-out:{exe}"], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["/usr/bin/mono", "-O=all", exe], None

    # C# (.NET / Mono Linux)
    elif l in ("cs_net", "csharp", "cs", "cs_net8", "cs_net9"):
        dotnet_bin = shutil.which("dotnet")
        if not dotnet_bin:
            for c in ("/usr/bin/dotnet", "/usr/share/dotnet/dotnet", "/opt/dotnet/dotnet"):
                if os.path.exists(c):
                    dotnet_bin = c
                    break
        if dotnet_bin and os.path.exists(dotnet_bin):
            try:
                tfm = "net8.0" if "8" in l else "net9.0"
                proj_dir = os.path.join(temp_dir, "csproj")
                os.makedirs(proj_dir, exist_ok=True)
                src = os.path.join(proj_dir, "Program.cs")
                proj = os.path.join(proj_dir, "csproj.csproj")
                with open(src, "w", encoding="utf-8") as f: f.write(code)
                with open(proj, "w", encoding="utf-8") as f:
                    f.write(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework><OptimizationPreference>Speed</OptimizationPreference></PropertyGroup></Project>')
                p = subprocess.run([dotnet_bin, "build", "-c", "Release", "--nologo", "-v", "q", proj_dir], capture_output=True, text=True, timeout=8)
                if p.returncode == 0:
                    dll = os.path.join(proj_dir, "bin", "Release", tfm, "csproj.dll")
                    if os.path.exists(dll):
                        return [dotnet_bin, "exec", dll], None
            except Exception:
                pass

        # Fast Native Linux Mono C# Compiler (< 0.05s)
        src = os.path.join(temp_dir, "Program.cs")
        exe = os.path.join(temp_dir, "Program.exe")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/mcs", "-optimize+", src, f"-out:{exe}"], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["/usr/bin/mono", "-O=all", exe], None

    # F# (.NET / Mono Linux)
    elif l in ("fs_net", "fsharp", "fs", "fs_net8", "fs_net9"):
        dotnet_bin = shutil.which("dotnet")
        if not dotnet_bin:
            for c in ("/usr/bin/dotnet", "/usr/share/dotnet/dotnet", "/opt/dotnet/dotnet"):
                if os.path.exists(c):
                    dotnet_bin = c
                    break
        if dotnet_bin and os.path.exists(dotnet_bin):
            try:
                tfm = "net8.0" if "8" in l else "net9.0"
                proj_dir = os.path.join(temp_dir, "fsproj")
                os.makedirs(proj_dir, exist_ok=True)
                src = os.path.join(proj_dir, "Program.fs")
                proj = os.path.join(proj_dir, "fsproj.fsproj")
                with open(src, "w", encoding="utf-8") as f: f.write(code)
                with open(proj, "w", encoding="utf-8") as f:
                    f.write(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework><OptimizationPreference>Speed</OptimizationPreference></PropertyGroup><ItemGroup><Compile Include="Program.fs" /></ItemGroup></Project>')
                p = subprocess.run([dotnet_bin, "build", "-c", "Release", "--nologo", "-v", "q", proj_dir], capture_output=True, text=True, timeout=8)
                if p.returncode == 0:
                    dll = os.path.join(proj_dir, "bin", "Release", tfm, "fsproj.dll")
                    if os.path.exists(dll):
                        return [dotnet_bin, "exec", dll], None
            except Exception:
                pass

        # Fast Native Linux F# Compiler
        src = os.path.join(temp_dir, "Program.fs")
        exe = os.path.join(temp_dir, "Program.exe")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        fsharpc = shutil.which("fsharpc") or "/usr/bin/fsharpc"
        p = subprocess.run([fsharpc, "--optimize+", src, f"-o:{exe}"], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["/usr/bin/mono", "-O=all", exe], None

    # Visual Basic (.NET / Mono Linux)
    elif l in ("vb_net", "vb", "visualbasic", "vb_net8", "vb_net9"):
        dotnet_bin = shutil.which("dotnet")
        if not dotnet_bin:
            for c in ("/usr/bin/dotnet", "/usr/share/dotnet/dotnet", "/opt/dotnet/dotnet"):
                if os.path.exists(c):
                    dotnet_bin = c
                    break
        if dotnet_bin and os.path.exists(dotnet_bin):
            try:
                tfm = "net8.0" if "8" in l else "net9.0"
                proj_dir = os.path.join(temp_dir, "vbproj")
                os.makedirs(proj_dir, exist_ok=True)
                src = os.path.join(proj_dir, "Program.vb")
                proj = os.path.join(proj_dir, "vbproj.vbproj")
                with open(src, "w", encoding="utf-8") as f: f.write(code)
                with open(proj, "w", encoding="utf-8") as f:
                    f.write(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework><OptimizationPreference>Speed</OptimizationPreference></PropertyGroup><ItemGroup><Compile Include="Program.vb" /></ItemGroup></Project>')
                p = subprocess.run([dotnet_bin, "build", "-c", "Release", "--nologo", "-v", "q", proj_dir], capture_output=True, text=True, timeout=8)
                if p.returncode == 0:
                    dll = os.path.join(proj_dir, "bin", "Release", tfm, "vbproj.dll")
                    if os.path.exists(dll):
                        return [dotnet_bin, "exec", dll], None
            except Exception:
                pass

        # Fast Native Linux VB Compiler
        src = os.path.join(temp_dir, "Program.vb")
        exe = os.path.join(temp_dir, "Program.exe")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        vbnc = shutil.which("vbnc") or "/usr/bin/vbnc"
        p = subprocess.run([vbnc, "-optimize+", src, f"-out:{exe}"], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["/usr/bin/mono", "-O=all", exe], None

    # Rust (-O3 Super-Opt)
    elif l in ("rust", "rs"):
        src = os.path.join(temp_dir, "prog.rs")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/rustc", "-O", "-C", "opt-level=3", "-C", "target-cpu=native", "-C", "codegen-units=1", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # Go (-ldflags="-s -w" stripped & optimized)
    elif l in ("go", "golang"):
        src = os.path.join(temp_dir, "prog.go")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/go", "build", "-ldflags=-s -w", "-o", exe, src], capture_output=True, text=True, cwd=temp_dir)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # Lua (5.4, 5.3, 5.1, LuaJIT)
    elif l in ("lua54", "lua", "lua5.4"):
        src = os.path.join(temp_dir, "prog.lua")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/lua5.4", src], None

    elif l in ("lua53", "lua5.3"):
        src = os.path.join(temp_dir, "prog.lua")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/lua5.3", src], None

    elif l in ("lua51", "lua5.1"):
        src = os.path.join(temp_dir, "prog.lua")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/lua5.1", src], None

    elif l in ("luajit", "jit"):
        src = os.path.join(temp_dir, "prog.lua")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/luajit", "-O3", src], None

    # Dart (Direct VM JIT Engine)
    elif l in ("dart", "dartsdk"):
        src = os.path.join(temp_dir, "prog.dart")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        dart_bin = shutil.which("dart")
        if not dart_bin:
            for candidate in ("/opt/dart-sdk/bin/dart", "/usr/lib/dart/bin/dart", "/usr/bin/dart"):
                if os.path.exists(candidate):
                    dart_bin = candidate
                    break
        dart_bin = dart_bin or "dart"
        return [dart_bin, "--verbosity=error", src], None

    # Kotlin (Kotlin 2.1 K2 Compiler on JDK 21 HotSpot)
    elif l.startswith("kotlin") or l in ("kt", "kotlinc"):
        src = os.path.join(temp_dir, "Prog.kt")
        jar = os.path.join(temp_dir, "prog.jar")
        with open(src, "w", encoding="utf-8") as f: f.write(code)

        kotlinc_bin = "/opt/kotlin-2.1/bin/kotlinc" if os.path.exists("/opt/kotlin-2.1/bin/kotlinc") else "/usr/bin/kotlinc"
        env = os.environ.copy()
        env["JAVA_HOME"] = "/usr/lib/jvm/java-21-openjdk-amd64"

        p = subprocess.run([kotlinc_bin, src, "-include-runtime", "-d", jar], env=env, capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)

        jvm_flags = ["-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", "-Xss256k", "-Xms4m", "-Xmx256m", "-jar", jar]
        java_bin = "/usr/lib/jvm/java-21-openjdk-amd64/bin/java"
        return [java_bin] + jvm_flags, None

    # D Language (GDC -O3 Super-Opt)
    elif l in ("d_gdc", "d", "gdc"):
        src = os.path.join(temp_dir, "prog.d")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gdc"] + SUPER_OPT + ["-frelease", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # Objective-C
    elif l in ("objc_gcc", "objc", "objectivec", "objective-c"):
        src = os.path.join(temp_dir, "prog.m")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + [src, "-lobjc", "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("objc_clang", "clang_objc"):
        src = os.path.join(temp_dir, "prog.m")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + [src, "-lobjc", "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # LLVM IR
    elif l in ("llvm_lli", "llvmir", "llvm", "ll"):
        src = os.path.join(temp_dir, "prog.ll")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/lli", "-O3", src], None

    elif l in ("llvm_clang", "clang_ll"):
        src = os.path.join(temp_dir, "prog.ll")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + [src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # PHP (Tracing JIT Enabled)
    elif l in ("php", "php8"):
        src = os.path.join(temp_dir, "prog.php")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/php", "-d", "opcache.enable_cli=1", "-d", "opcache.jit=tracing", "-d", "opcache.jit_buffer_size=64M", "-d", "memory_limit=256M", src], None

    # TypeScript (TSX)
    elif l in ("ts_tsx", "typescript", "ts"):
        src = os.path.join(temp_dir, "prog.ts")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        tsx_bin = shutil.which("tsx")
        if not tsx_bin:
            for candidate in (
                "/usr/local/bin/tsx",
                "/usr/bin/tsx",
                "/home/pc/.nvm/versions/node/v22.23.2/bin/tsx",
                "/home/pc/.nvm/versions/node/v26.7.0/bin/tsx",
            ):
                if os.path.exists(candidate):
                    tsx_bin = candidate
                    break
        if tsx_bin and os.path.exists(tsx_bin):
            return [tsx_bin, src], None
        return ["npx", "--silent", "--no-warnings", "tsx", src], None

    # JavaScript / Node.js multi-version
    elif l.startswith("js_node") or l in ("js", "javascript", "node"):
        src = os.path.join(temp_dir, "prog.js")
        with open(src, "w", encoding="utf-8") as f: f.write(code)

        node_ver = "26.7.0"
        if "node18" in l: node_ver = "18.20.8"
        elif "node20" in l: node_ver = "20.20.2"
        elif "node22" in l: node_ver = "22.23.2"
        elif "node24" in l: node_ver = "24.19.0"

        node_bin = f"/home/pc/.nvm/versions/node/v{node_ver}/bin/node"
        if not os.path.exists(node_bin):
            node_bin = "/usr/bin/node" if os.path.exists("/usr/bin/node") else "node"
        return [node_bin, "--max-old-space-size=256", src], None

    # ARM64 (AArch64) via QEMU User Emulation
    elif l in ("asm_arm64", "arm64", "aarch64"):
        src = os.path.join(temp_dir, "prog.s")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["aarch64-linux-gnu-gcc", "-no-pie", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["qemu-aarch64", "-L", "/usr/aarch64-linux-gnu", exe], None

    # ARM32 (ARMv7 HF) via QEMU User Emulation
    elif l in ("asm_arm32", "arm32", "armhf", "arm"):
        src = os.path.join(temp_dir, "prog.s")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["arm-linux-gnueabihf-gcc", "-no-pie", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["qemu-arm", "-L", "/usr/arm-linux-gnueabihf", exe], None

    # x86-64 Assembly (NASM, YASM, GNU AS, FASM)
    elif l in ("asm_nasm", "nasm", "assembly"):
        src = os.path.join(temp_dir, "prog.asm")
        obj = os.path.join(temp_dir, "prog.o")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p1 = subprocess.run(["/usr/bin/nasm", "-f", "elf64", src, "-o", obj], capture_output=True, text=True)
        if p1.returncode != 0: return None, strip_ansi(p1.stderr)
        p2 = subprocess.run(["/usr/bin/gcc", "-no-pie", obj, "-o", exe], capture_output=True, text=True)
        if p2.returncode != 0: return None, strip_ansi(p2.stderr)
        return [exe], None

    elif l in ("asm_yasm", "yasm"):
        src = os.path.join(temp_dir, "prog.asm")
        obj = os.path.join(temp_dir, "prog.o")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p1 = subprocess.run(["/usr/bin/yasm", "-f", "elf64", src, "-o", obj], capture_output=True, text=True)
        if p1.returncode != 0: return None, strip_ansi(p1.stderr)
        p2 = subprocess.run(["/usr/bin/gcc", "-no-pie", obj, "-o", exe], capture_output=True, text=True)
        if p2.returncode != 0: return None, strip_ansi(p2.stderr)
        return [exe], None

    elif l in ("asm_gas", "gas", "as"):
        src = os.path.join(temp_dir, "prog.s")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc", "-no-pie", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("asm_fasm", "fasm"):
        src = os.path.join(temp_dir, "prog.asm")
        obj = os.path.join(temp_dir, "prog.o")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p1 = subprocess.run(["/usr/bin/fasm", src, obj], capture_output=True, text=True)
        if p1.returncode != 0: return None, strip_ansi(p1.stderr + p1.stdout)
        p2 = subprocess.run(["/usr/bin/gcc", "-no-pie", obj, "-o", exe], capture_output=True, text=True)
        if p2.returncode != 0: return None, strip_ansi(p2.stderr)
        return [exe], None

    # C++ (Clang Toolchain: C++03, C++11, C++14, C++17, C++20, C++23, C++26)
    elif l in ("clpp26", "clangpp26", "clang++26"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++26", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp23", "clangpp23", "clang++23"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++23", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp20", "clangpp20", "clang++20"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++20", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp17", "clangpp17", "clang++17"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++17", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp14", "clangpp14", "clang++14"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++14", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp11", "clangpp11", "clang++11"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++11", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clpp03", "clangpp03", "clpp98", "clang++03"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang++"] + SUPER_OPT + ["-std=c++03", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # C++ (GCC Toolchain: C++98/03, C++11, C++14, C++17, C++20, C++23, C++26)
    elif l in ("cpp26", "g++26"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++26", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp23", "g++23"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++23", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp20", "cpp", "c++", "g++20", "g++"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++20", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp17", "g++17"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++17", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp14", "g++14"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++14", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp11", "g++11"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++11", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("cpp03", "cpp98", "g++03", "g++98"):
        src = os.path.join(temp_dir, "prog.cpp")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/g++"] + SUPER_OPT + ["-std=c++03", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # C (Clang Toolchain: C89, C99, C11, C17, C23)
    elif l in ("clang23", "clang_c23"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + ["-std=c23", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clang17", "clang_c17"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + ["-std=c17", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clang11", "clang_c11"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + ["-std=c11", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clang99", "clang_c99"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + ["-std=c99", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("clang89", "clang_c89", "clang90"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/clang"] + SUPER_OPT + ["-std=c89", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # C (GCC Toolchain: C89, C99, C11, C17, C23)
    elif l in ("c23", "gcc23"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + ["-std=c23", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("c17", "c18", "gcc17"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + ["-std=c17", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("c11", "c", "gcc11", "gcc"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + ["-std=c11", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("c99", "gcc99"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + ["-std=c99", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    elif l in ("c89", "c90", "gcc89", "gcc90"):
        src = os.path.join(temp_dir, "prog.c")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/gcc"] + SUPER_OPT + ["-std=c89", src, "-o", exe], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return [exe], None

    # Pascal (Turbo Pascal 7.0 mode vs Free Pascal vs Delphi mode)
    elif l in ("pas_tp", "tp", "turbopascal"):
        src = os.path.join(temp_dir, "prog.pas")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/fpc", "-Mtp", "-O3", "-Xs", "-XX", FPC_UNITS, src, f"-o{exe}"], capture_output=True, text=True, cwd=temp_dir)
        if p.returncode != 0: return None, strip_ansi(p.stdout + p.stderr)
        return [exe], None

    elif l in ("pas_tp", "tp", "turbopascal"):
        src = os.path.join(temp_dir, "prog.pas")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/fpc", "-Mtp", "-O3", "-Xs", "-XX", FPC_UNITS, src, f"-o{exe}"], capture_output=True, text=True, cwd=temp_dir)
        if p.returncode != 0: return None, strip_ansi(p.stdout + p.stderr)
        return [exe], None

    elif l in ("pas_delphi", "delphi"):
        src = os.path.join(temp_dir, "prog.pas")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/fpc", "-Mdelphi", "-O3", "-Xs", "-XX", FPC_UNITS, src, f"-o{exe}"], capture_output=True, text=True, cwd=temp_dir)
        if p.returncode != 0: return None, strip_ansi(p.stdout + p.stderr)
        return [exe], None

    elif l in ("pas_fpc", "pascal", "pas", "fpc"):
        src = os.path.join(temp_dir, "prog.pas")
        exe = os.path.join(temp_dir, "prog")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/fpc", "-Mobjfpc", "-O3", "-Xs", "-XX", FPC_UNITS, src, f"-o{exe}"], capture_output=True, text=True, cwd=temp_dir)
        if p.returncode != 0: return None, strip_ansi(p.stdout + p.stderr)
        return [exe], None

    # Python (CPython 2.7, PyPy 2.7, CPython 3.14, PyPy 3.11)
    elif l in ("python2", "py2", "cpython2"):
        src = os.path.join(temp_dir, "prog.py")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        py2_bin = "/usr/local/bin/python2" if os.path.exists("/usr/local/bin/python2") else "/opt/python2.7/bin/python2.7"
        return [py2_bin, "-u", src], None

    elif l in ("pypy2", "pypy2.7"):
        src = os.path.join(temp_dir, "prog.py")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        pypy2_bin = "/usr/local/bin/pypy2" if os.path.exists("/usr/local/bin/pypy2") else "/opt/pypy2.7/bin/pypy"
        return [pypy2_bin, "-u", src], None

    elif l in ("pypy3", "pypy"):
        src = os.path.join(temp_dir, "prog.py")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        return ["/usr/bin/pypy3", "-u", src], None

    elif l in ("python3", "python", "py", "cpython3"):
        src = os.path.join(temp_dir, "prog.py")
        with open(src, "w", encoding="utf-8") as f: f.write(code)
        p = subprocess.run(["/usr/bin/python3", "-m", "py_compile", src], capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)
        return ["/usr/bin/python3", "-u", src], None

    # Java (OpenJDK, GraalVM, Eclipse Temurin, BellSoft Liberica, Oracle JDK)
    elif l.startswith("java") or l.startswith("jdk"):
        src = os.path.join(temp_dir, "Main.java")
        with open(src, "w", encoding="utf-8") as f: f.write(code)

        base_dir = "/usr/lib/jvm/java-21-openjdk-amd64"
        if "26" in l:
            if os.path.exists("/opt/jdk-26/bin/javac"): base_dir = "/opt/jdk-26"
            else: base_dir = "/usr/lib/jvm/java-26-openjdk-amd64"
        elif "25" in l:
            if os.path.exists("/opt/jdk-25/bin/javac"): base_dir = "/opt/jdk-25"
            else: base_dir = "/usr/lib/jvm/java-25-openjdk-amd64"
        elif "graalvm" in l:
            if "17" in l and os.path.exists("/opt/graalvm-17/bin/javac"): base_dir = "/opt/graalvm-17"
            elif os.path.exists("/opt/graalvm-21/bin/javac"): base_dir = "/opt/graalvm-21"
            elif os.path.exists("/opt/graalvm/bin/javac"): base_dir = "/opt/graalvm"
            else: base_dir = "/opt/jvm/graalvm-21"
        elif "oracle" in l:
            if "17" in l and os.path.exists("/opt/oracle-17/bin/javac"): base_dir = "/opt/oracle-17"
            elif os.path.exists("/opt/oracle-21/bin/javac"): base_dir = "/opt/oracle-21"
            else: base_dir = "/opt/jvm/oracle"
        elif "temurin" in l:
            if "8" in l or "1_4" in l or "1_0" in l:
                base_dir = "/usr/lib/jvm/temurin-8-jdk-amd64" if os.path.exists("/usr/lib/jvm/temurin-8-jdk-amd64/bin/javac") else "/opt/jvm/temurin-8"
            elif "11" in l:
                base_dir = "/usr/lib/jvm/temurin-11-jdk-amd64" if os.path.exists("/usr/lib/jvm/temurin-11-jdk-amd64/bin/javac") else "/opt/jvm/temurin-11"
            elif "17" in l:
                base_dir = "/usr/lib/jvm/temurin-17-jdk-amd64" if os.path.exists("/usr/lib/jvm/temurin-17-jdk-amd64/bin/javac") else "/opt/jvm/temurin-17"
            else:
                base_dir = "/usr/lib/jvm/temurin-21-jdk-amd64" if os.path.exists("/usr/lib/jvm/temurin-21-jdk-amd64/bin/javac") else "/opt/jvm/temurin-21"
        elif "liberica" in l:
            if "8" in l:
                base_dir = "/usr/lib/jvm/bellsoft-java8-amd64" if os.path.exists("/usr/lib/jvm/bellsoft-java8-amd64/bin/javac") else "/usr/lib/jvm/java-8-openjdk-amd64"
            elif "11" in l:
                base_dir = "/usr/lib/jvm/bellsoft-java11-amd64" if os.path.exists("/usr/lib/jvm/bellsoft-java11-amd64/bin/javac") else "/usr/lib/jvm/java-11-openjdk-amd64"
            elif "17" in l:
                base_dir = "/usr/lib/jvm/bellsoft-java17-amd64" if os.path.exists("/usr/lib/jvm/bellsoft-java17-amd64/bin/javac") else "/usr/lib/jvm/java-17-openjdk-amd64"
            else:
                base_dir = "/usr/lib/jvm/bellsoft-java21-amd64" if os.path.exists("/usr/lib/jvm/bellsoft-java21-amd64/bin/javac") else "/opt/jvm/liberica-21"
        elif "17" in l:
            base_dir = "/usr/lib/jvm/java-17-openjdk-amd64"
        elif "11" in l:
            base_dir = "/usr/lib/jvm/java-11-openjdk-amd64"
        elif any(k in l for k in ("compat", "1_4", "1_0", "java5", "java6", "java7", "java8")):
            base_dir = "/usr/lib/jvm/java-8-openjdk-amd64"

        javac_bin = os.path.join(base_dir, "bin", "javac")
        java_bin = os.path.join(base_dir, "bin", "java")
        if not os.path.exists(javac_bin):
            javac_bin = "/usr/bin/javac"
            java_bin = "/usr/bin/java"

        flags = []
        if "compat7" in l or "java7" in l:
            flags = ["-source", "1.7", "-target", "1.7"]
        elif "compat6" in l or "java6" in l:
            flags = ["-source", "1.6", "-target", "1.6"]
        elif "compat5" in l or "java5" in l:
            flags = ["-source", "1.5", "-target", "1.5"]
        elif "1_4" in l or "java1_4" in l:
            flags = ["-source", "1.4", "-target", "1.4"]
        elif "1_0" in l or "java1_0" in l:
            flags = ["-source", "1.3", "-target", "1.3"]

        compile_cmd = [javac_bin] + flags + [src]
        p = subprocess.run(compile_cmd, capture_output=True, text=True)
        if p.returncode != 0: return None, strip_ansi(p.stderr)

        jvm_run_flags = [
            "-XX:+UseSerialGC",
            "-XX:TieredStopAtLevel=1",
            "-XX:ActiveProcessorCount=1",
            "-XX:CICompilerCount=2",
            "-Xss256k",
            "-Xms4m",
            "-Xmx256m",
            "-cp", temp_dir,
            "Main"
        ]
        return [java_bin] + jvm_run_flags, None

    else:
        return None, f"Unsupported language: {lang}"

def is_process_waiting_for_input(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            stat_parts = f.read().split()
            if len(stat_parts) >= 3 and stat_parts[2] == "R":
                return False
        with open(f"/proc/{pid}/wchan", "r") as f:
            wchan = f.read().strip().lower()
            if any(k in wchan for k in ("wait_woken", "n_tty_read", "read_chan", "tty_read", "anon_pipe_read", "pipe_read")):
                return True
    except Exception:
        pass
    return False

def run_interactive():
    line = sys.stdin.readline()
    if not line:
        return
    req = json.loads(line)
    lang = req.get("language", "cpp20")
    code = req.get("code", "")

    # Security validation (check for assembly unsafe syscalls, multi-threading, low-level sys calls, raw sockets, process spawning)
    sec_err = validate_code_security(lang, code)
    if sec_err:
        send_msg("compile_error", {"error": f"🛡️ [SECURITY REJECTED]: {sec_err}"})
        return

    temp_dir = tempfile.mkdtemp(prefix="eoj_interactive_")
    cmd, err = compile_source(lang, code, temp_dir)
    if err:
        send_msg("compile_error", {"error": err})
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    send_msg("started", {"status": "Running"})

    master_fd, slave_fd = pty.openpty()
    try:
        attrs = termios.tcgetattr(slave_fd)
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
    except Exception:
        pass

    start_cpu_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    t_start = time.time()
    total_input_wait_time = 0.0
    peak_code_memory_kb = 0
    mle_triggered = False
    tle_triggered = False

    def preexec_sandbox():
        os.setsid()
        try:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0)) # No core dumps
            resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024)) # Adequate file descriptors for JIT runtimes
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10)) # Hard kernel CPU time fallback
        except Exception:
            pass

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"

    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=temp_dir,
        close_fds=True,
        preexec_fn=preexec_sandbox,
        env=env
    )
    os.close(slave_fd)

    os.set_blocking(master_fd, False)
    os.set_blocking(sys.stdin.fileno(), False)

    waiting_for_input = False
    input_wait_start = 0.0

    try:
        while proc.poll() is None:
            current_wall_time = time.time() - t_start
            current_compute_time = current_wall_time - total_input_wait_time - (time.time() - input_wait_start if waiting_for_input else 0.0)

            # Check if process is actively blocked on stdin read
            blocked = is_process_waiting_for_input(proc.pid)
            if blocked and not waiting_for_input:
                waiting_for_input = True
                input_wait_start = time.time()
                send_msg("waiting_input", {})
            elif not blocked and waiting_for_input:
                total_input_wait_time += (time.time() - input_wait_start)
                waiting_for_input = False
                send_msg("resumed", {})

            # Timeout check: 5.0s limit
            if current_compute_time >= TIMEOUT_LIMIT:
                tle_triggered = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                send_msg("output", {
                    "data": f"\n\n🚨 [ALERT: Time Limit Exceeded (TLE)]: Process killed — Computation exceeded {TIMEOUT_LIMIT:.1f}s limit.\n"
                })
                break

            # Memory tracking and hard 256MB kill check
            code_mem_kb, total_phys_kb = get_process_memory_stats(proc.pid, lang)
            if code_mem_kb > peak_code_memory_kb:
                peak_code_memory_kb = code_mem_kb

            if total_phys_kb > MAX_MEMORY_KB:
                mle_triggered = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                send_msg("output", {
                    "data": f"\n\n🚨 [ALERT: Memory Limit Exceeded (MLE)]: Process killed — Memory reached {total_phys_kb // 1024} MB (Limit: 256 MB)\n"
                })
                break

            rlist, _, _ = select.select([master_fd, sys.stdin.fileno()], [], [], 0.02)

            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        text = data.decode("utf-8", errors="replace")
                        send_msg("output", {"data": text})
                except (OSError, IOError):
                    pass

            if sys.stdin.fileno() in rlist:
                try:
                    input_line = sys.stdin.readline()
                    if input_line:
                        msg = json.loads(input_line)
                        if msg.get("type") == "input":
                            user_input = msg.get("data", "")
                            if waiting_for_input:
                                total_input_wait_time += (time.time() - input_wait_start)
                                waiting_for_input = False
                                send_msg("resumed", {})
                            os.write(master_fd, user_input.encode("utf-8"))
                        elif msg.get("type") == "stop":
                            try:
                                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                            except Exception:
                                pass
                            break
                except (json.JSONDecodeError, OSError, IOError):
                    pass

        try:
            while True:
                rlist, _, _ = select.select([master_fd], [], [], 0.02)
                if master_fd in rlist:
                    data = os.read(master_fd, 4096)
                    if data:
                        text = data.decode("utf-8", errors="replace")
                        send_msg("output", {"data": text})
                    else:
                        break
                else:
                    break
        except Exception:
            pass

        proc.wait()
        total_wall_time = time.time() - t_start
        execution_time = max(0.001, total_wall_time - total_input_wait_time)

        end_cpu_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_time = (end_cpu_usage.ru_utime - start_cpu_usage.ru_utime) + (end_cpu_usage.ru_stime - start_cpu_usage.ru_stime)
        final_time = round(cpu_time if cpu_time > 0 else execution_time, 4)
        final_memory = max(16, peak_code_memory_kb)

        ret = proc.returncode

        # Map exit code & crash signals
        if tle_triggered:
            status = "Time Limit Exceeded (TLE - 5.0s)"
            exit_code = 124
        elif mle_triggered:
            status = "Memory Limit Exceeded (MLE - 256MB)"
            exit_code = 137
        elif ret == 0:
            status = "Success"
            exit_code = 0
        elif ret in (-11, 139):
            status = "Runtime Error (Segmentation Fault - SIGSEGV)"
            exit_code = 139
            send_msg("output", {"data": "\n💥 [CRASH ALERT]: Segmentation Fault (SIGSEGV) — Out-of-bounds memory access, invalid pointer dereference, or stack overflow.\n"})
        elif ret in (-8, 136):
            status = "Runtime Error (Division by Zero - SIGFPE)"
            exit_code = 136
            send_msg("output", {"data": "\n💥 [CRASH ALERT]: Floating Point Exception (SIGFPE) — Division by zero or arithmetic overflow.\n"})
        elif ret in (-6, 134):
            status = "Runtime Error (Aborted - SIGABRT)"
            exit_code = 134
            send_msg("output", {"data": "\n💥 [CRASH ALERT]: Program Aborted (SIGABRT) — Assertion failed or unhandled exception.\n"})
        elif ret in (-7, 135):
            status = "Runtime Error (Bus Error - SIGBUS)"
            exit_code = 135
            send_msg("output", {"data": "\n💥 [CRASH ALERT]: Bus Error (SIGBUS) — Non-existent physical address or unaligned memory access.\n"})
        elif ret in (-4, 132):
            status = "Runtime Error (Illegal Instruction - SIGILL)"
            exit_code = 132
            send_msg("output", {"data": "\n💥 [CRASH ALERT]: Illegal Instruction (SIGILL) — Invalid or corrupt opcode.\n"})
        else:
            status = f"Runtime Error (Exit Code {ret})"
            exit_code = ret

        send_msg("exit", {
            "exitCode": exit_code,
            "time": min(TIMEOUT_LIMIT, final_time),
            "memory": final_memory,
            "status": status
        })

    finally:
        try:
            os.close(master_fd)
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_interactive()
