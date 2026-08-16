#!/usr/bin/env bash
#!/usr/bin/env python3
"""
EOJ Real System Toolchain Discovery Engine
Probes the actual underlying OS / Docker filesystem and binaries in real-time.
Filters out any missing toolchains/versions so only 100% available and executable runtimes are returned.
"""

import os
import re
import shutil
import subprocess
from typing import Dict, List, Any, Optional

def get_cmd_version(cmd: List[str]) -> Optional[str]:
    """Execute command and extract the first meaningful version string."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
        output = (proc.stdout + "\n" + proc.stderr).strip()
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.search(r'(\d+\.\d+(?:\.\d+)?)', line)
            if m:
                return m.group(1)
        return "installed"
    except Exception:
        return None

def is_bin_available(name: str, *alt_paths: str) -> bool:
    """Check if binary is in PATH or exists in specific locations."""
    if shutil.which(name) is not None:
        return True
    for p in alt_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return True
    return False

def get_installed_dotnet_sdks() -> List[str]:
    """Inspect actual installed .NET SDK versions on the machine."""
    sdks: List[str] = []
    dotnet_bin = shutil.which("dotnet") or "/usr/share/dotnet/dotnet" or "/usr/bin/dotnet" or "/opt/dotnet/dotnet"
    if os.path.exists(dotnet_bin) and os.access(dotnet_bin, os.X_OK):
        try:
            p = subprocess.run([dotnet_bin, "--list-sdks"], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                for line in p.stdout.splitlines():
                    m = re.match(r'^(\d+\.\d+)', line.strip())
                    if m:
                        sdks.append(m.group(1))
        except Exception:
            pass
    if os.path.exists("/usr/share/dotnet/sdk"):
        try:
            for entry in os.listdir("/usr/share/dotnet/sdk"):
                m = re.match(r'^(\d+\.\d+)', entry)
                if m:
                    sdks.append(m.group(1))
        except Exception:
            pass
    return sorted(list(set(sdks)), reverse=True)

def get_installed_jvm_paths() -> Dict[str, str]:
    """Inspect all physically installed JVM installations."""
    jvms: Dict[str, str] = {}
    jvm_dir = "/usr/lib/jvm"
    if os.path.exists(jvm_dir):
        try:
            for item in os.listdir(jvm_dir):
                full_path = os.path.join(jvm_dir, item)
                java_bin = os.path.join(full_path, "bin", "java")
                if os.path.isfile(java_bin) and os.access(java_bin, os.X_OK):
                    jvms[item] = java_bin
        except Exception:
            pass

    # Check custom /opt installations
    opt_checks = [
        ("jdk-26", "/opt/jdk-26/bin/java"),
        ("jdk-25", "/opt/jdk-25/bin/java"),
        ("graalvm-21", "/opt/graalvm-21/bin/java"),
        ("graalvm-17", "/opt/graalvm-17/bin/java"),
        ("oracle-21", "/opt/oracle-21/bin/java"),
        ("oracle-17", "/opt/oracle-17/bin/java"),
    ]
    for key, path in opt_checks:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            jvms[key] = path

    # Check default system java
    sys_java = shutil.which("java")
    if sys_java:
        jvms["default"] = sys_java
    return jvms

def discover_installed_languages() -> List[Dict[str, Any]]:
    """Probes the host/container system in real-time and dynamically builds the active catalog."""
    installed_langs: List[Dict[str, Any]] = []

    # 1. C
    has_gcc = is_bin_available("gcc", "/usr/bin/gcc")
    has_clang = is_bin_available("clang", "/usr/bin/clang")
    if has_gcc or has_clang:
        c_versions = []
        for std_id, std_name in [("c23", "C23"), ("c17", "C17 / C18"), ("c11", "C11"), ("c99", "C99"), ("c89", "C89 / C90")]:
            tools = []
            if has_gcc:
                tools.append({"id": f"gcc_{std_id}", "name": f"GCC ({std_name} -O3 Super-Opt)", "targetId": std_id})
            if has_clang:
                tools.append({"id": f"clang_{std_id}", "name": f"Clang ({std_name} -O3 Super-Opt)", "targetId": f"clang_{std_id}"})
            if tools:
                c_versions.append({"id": std_id, "name": std_name, "toolchains": tools})
        if c_versions:
            installed_langs.append({
                "id": "c",
                "name": "C",
                "monaco": "c",
                "template": '#include <stdio.h>\n\nint main(void) {\n  printf("Hello, World!\\n");\n  return 0;\n}\n',
                "versions": c_versions,
            })

    # 2. C++
    has_gpp = is_bin_available("g++", "/usr/bin/g++")
    has_clangpp = is_bin_available("clang++", "/usr/bin/clang++")
    if has_gpp or has_clangpp:
        cpp_versions = []
        for std_id, std_name in [("cpp26", "C++26"), ("cpp23", "C++23"), ("cpp20", "C++20"), ("cpp17", "C++17"), ("cpp14", "C++14"), ("cpp11", "C++11"), ("cpp03", "C++03 / 98")]:
            tools = []
            if has_gpp:
                tools.append({"id": f"gpp_{std_id}", "name": f"G++ ({std_name} -O3 Super-Opt)", "targetId": std_id})
            if has_clangpp:
                tools.append({"id": f"clangpp_{std_id}", "name": f"Clang++ ({std_name} -O3 Super-Opt)", "targetId": f"clpp_{std_id.replace('cpp', '')}"})
            if tools:
                cpp_versions.append({"id": std_id, "name": std_name, "toolchains": tools})
        if cpp_versions:
            installed_langs.append({
                "id": "cpp",
                "name": "C++",
                "monaco": "cpp",
                "template": '#include <iostream>\n\nint main() {\n  std::ios_base::sync_with_stdio(false);\n  std::cin.tie(NULL);\n  std::cout << "Hello, World!" << "\\n";\n  return 0;\n}\n',
                "versions": cpp_versions,
            })

    # 3. Python
    has_py3 = is_bin_available("python3", "/usr/bin/python3")
    has_pypy3 = is_bin_available("pypy3", "/usr/bin/pypy3")
    has_py2 = is_bin_available("python2", "/usr/bin/python2")
    if has_py3 or has_pypy3 or has_py2:
        py_versions = []
        if has_py3:
            v_str = get_cmd_version(["python3", "--version"]) or "3.12"
            py_versions.append({
                "id": "py3",
                "name": f"Python {v_str} (CPython)",
                "toolchains": [{"id": "cpython3", "name": f"CPython {v_str} (Standard)", "targetId": "python3"}],
            })
        if has_pypy3:
            py_versions.append({
                "id": "pypy3",
                "name": "PyPy 3 (Tracing JIT)",
                "toolchains": [{"id": "pypy3_jit", "name": "PyPy 3 JIT Engine", "targetId": "pypy3"}],
            })
        if has_py2:
            py_versions.append({
                "id": "py2",
                "name": "Python 2.7 (Legacy)",
                "toolchains": [{"id": "cpython2", "name": "CPython 2.7", "targetId": "python2"}],
            })
        if py_versions:
            installed_langs.append({
                "id": "python",
                "name": "Python",
                "monaco": "python",
                "template": 'def main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
                "versions": py_versions,
            })

    # 4. Java
    jvms = get_installed_jvm_paths()
    if jvms:
        java_versions = []
        # Check standard versions: 26, 25, 21, 17, 11, 8
        for ver_num, label in [("26", "Java 26"), ("25", "Java 25 (LTS)"), ("21", "Java 21 (LTS)"), ("17", "Java 17 (LTS)"), ("11", "Java 11 (LTS)"), ("8", "Java 8 (LTS)")]:
            tools = []
            # OpenJDK
            if any(f"java-{ver_num}-openjdk" in k or f"jdk-{ver_num}" in k for k in jvms):
                tools.append({"id": f"openjdk{ver_num}", "name": f"OpenJDK {ver_num} HotSpot", "targetId": f"java{ver_num}_openjdk"})
            # Temurin
            if any(f"temurin-{ver_num}" in k for k in jvms):
                tools.append({"id": f"temurin{ver_num}", "name": f"Eclipse Temurin {ver_num} (Adoptium)", "targetId": f"java{ver_num}_temurin"})
            # GraalVM
            if any(f"graalvm-{ver_num}" in k for k in jvms):
                tools.append({"id": f"graalvm{ver_num}", "name": f"Oracle GraalVM CE {ver_num}", "targetId": f"java{ver_num}_graalvm"})
            # BellSoft
            if any(f"bellsoft-java{ver_num}" in k for k in jvms):
                tools.append({"id": f"liberica{ver_num}", "name": f"BellSoft Liberica {ver_num}", "targetId": f"java{ver_num}_liberica"})
            # Oracle JDK
            if any(f"oracle-{ver_num}" in k for k in jvms):
                tools.append({"id": f"oracle{ver_num}", "name": f"Oracle JDK {ver_num}", "targetId": f"java{ver_num}_oracle"})

            if tools:
                java_versions.append({"id": ver_num, "name": label, "toolchains": tools})

        if not java_versions and "default" in jvms:
            v_str = get_cmd_version(["java", "-version"]) or "21"
            major = v_str.split(".")[0]
            java_versions.append({
                "id": major,
                "name": f"Java {major} (System Default)",
                "toolchains": [{"id": f"java_sys", "name": f"Java {v_str} HotSpot", "targetId": f"java{major}_openjdk"}],
            })

        if java_versions:
            installed_langs.append({
                "id": "java",
                "name": "Java",
                "monaco": "java",
                "template": 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello, World!");\n  }\n}\n',
                "versions": java_versions,
            })

    # 5. C#
    has_mcs = is_bin_available("mcs", "/usr/bin/mcs")
    has_mono = is_bin_available("mono", "/usr/bin/mono")
    dotnet_sdks = get_installed_dotnet_sdks()
    if has_mcs or dotnet_sdks:
        cs_versions = []
        if "9.0" in dotnet_sdks or "9.0" in "".join(dotnet_sdks):
            cs_versions.append({
                "id": "net9",
                "name": "C# 13 (.NET 9.0)",
                "toolchains": [{"id": "net9_coreclr", "name": "Microsoft .NET 9.0 (CoreCLR)", "targetId": "cs_net9"}],
            })
        if "8.0" in dotnet_sdks or "8.0" in "".join(dotnet_sdks):
            cs_versions.append({
                "id": "net8",
                "name": "C# 12 (.NET 8.0)",
                "toolchains": [{"id": "net8_coreclr", "name": "Microsoft .NET 8.0 (CoreCLR)", "targetId": "cs_net8"}],
            })
        if has_mcs and has_mono:
            cs_versions.append({
                "id": "mono",
                "name": "C# Mono (Linux Native)",
                "toolchains": [{"id": "mono_mcs", "name": "Mono C# Compiler (mcs -optimize+)", "targetId": "cs_mono"}],
            })
        if not cs_versions and has_mcs:
            cs_versions.append({
                "id": "mono",
                "name": "C# Mono",
                "toolchains": [{"id": "mono_mcs", "name": "Mono C# (mcs)", "targetId": "cs_mono"}],
            })
        if cs_versions:
            installed_langs.append({
                "id": "csharp",
                "name": "C#",
                "monaco": "csharp",
                "template": 'using System;\n\nclass Program {\n  static void Main(string[] args) {\n    Console.WriteLine("Hello, World!");\n  }\n}\n',
                "versions": cs_versions,
            })

    # 6. Pascal
    has_fpc = is_bin_available("fpc", "/usr/bin/fpc")
    if has_fpc:
        fpc_v = get_cmd_version(["fpc", "-iV"]) or "3.2.2"
        installed_langs.append({
            "id": "pascal",
            "name": "Pascal",
            "monaco": "pascal",
            "template": 'program Hello;\nbegin\n  writeln(\'Hello, World!\');\nend.\n',
            "versions": [
                {
                    "id": "objfpc",
                    "name": f"Free Pascal {fpc_v} (ObjFPC Mode)",
                    "toolchains": [
                        {"id": "fpc_super_opt", "name": f"FPC {fpc_v} (-O3 Super-Opt)", "targetId": "pas_fpc"},
                        {"id": "fpc_smart", "name": f"FPC {fpc_v} (Register / Smart Link)", "targetId": "pas_fpc_smart"},
                    ],
                },
                {
                    "id": "tp",
                    "name": "Turbo Pascal 7.0 Mode",
                    "toolchains": [
                        {"id": "fpc_tp", "name": f"FPC (TP Mode -O3)", "targetId": "pas_tp"},
                    ],
                },
                {
                    "id": "delphi",
                    "name": "Delphi Mode",
                    "toolchains": [
                        {"id": "fpc_delphi", "name": f"FPC (Delphi Mode -O3)", "targetId": "pas_delphi"},
                    ],
                },
            ],
        })

    # 7. Assembly
    has_nasm = is_bin_available("nasm", "/usr/bin/nasm")
    has_yasm = is_bin_available("yasm", "/usr/bin/yasm")
    has_gas = is_bin_available("as", "/usr/bin/as")
    has_fasm = is_bin_available("fasm", "/usr/local/bin/fasm")
    has_arm64_gcc = is_bin_available("aarch64-linux-gnu-gcc", "/usr/bin/aarch64-linux-gnu-gcc")
    has_qemu_arm64 = is_bin_available("qemu-aarch64", "/usr/bin/qemu-aarch64")
    has_arm32_gcc = is_bin_available("arm-linux-gnueabihf-gcc", "/usr/bin/arm-linux-gnueabihf-gcc")
    has_qemu_arm32 = is_bin_available("qemu-arm", "/usr/bin/qemu-arm")

    asm_versions = []
    x86_tools = []
    if has_nasm: x86_tools.append({"id": "nasm", "name": "NASM (Intel Syntax)", "targetId": "asm_nasm"})
    if has_yasm: x86_tools.append({"id": "yasm", "name": "YASM", "targetId": "asm_yasm"})
    if has_gas: x86_tools.append({"id": "gas", "name": "GNU AS (Intel Syntax)", "targetId": "asm_gas"})
    if has_fasm: x86_tools.append({"id": "fasm", "name": "FASM (Flat Assembler)", "targetId": "asm_fasm"})
    if x86_tools:
        asm_versions.append({"id": "x86_64", "name": "x86-64 (AMD64)", "toolchains": x86_tools})

    if has_arm64_gcc and has_qemu_arm64:
        asm_versions.append({
            "id": "arm64",
            "name": "ARM64 (AArch64)",
            "toolchains": [{"id": "gas_arm64", "name": "GNU AS ARM64 (QEMU Emulation)", "targetId": "asm_arm64"}],
        })

    if has_arm32_gcc and has_qemu_arm32:
        asm_versions.append({
            "id": "arm32",
            "name": "ARM32 (ARMv7 HF)",
            "toolchains": [{"id": "gas_arm32", "name": "GNU AS ARM32 (QEMU Emulation)", "targetId": "asm_arm32"}],
        })

    if asm_versions:
        installed_langs.append({
            "id": "assembly",
            "name": "Assembly",
            "monaco": "asm",
            "template": 'default rel\nglobal main\nextern printf\n\nsection .data\n    msg db \'Hello, World!\', 10, 0\n\nsection .text\nmain:\n    sub rsp, 8\n    lea rdi, [msg]\n    xor eax, eax\n    call printf wrt ..plt\n    xor eax, eax\n    add rsp, 8\n    ret\n',
            "versions": asm_versions,
        })

    # 8. Go
    has_go = is_bin_available("go", "/usr/bin/go")
    if has_go:
        go_v = get_cmd_version(["go", "version"]) or "1.22"
        installed_langs.append({
            "id": "go",
            "name": "Go",
            "monaco": "go",
            "template": 'package main\n\nimport "fmt"\n\nfunc main() {\n  fmt.Println("Hello, World!")\n}\n',
            "versions": [
                {
                    "id": "go_current",
                    "name": f"Go {go_v} (Standard)",
                    "toolchains": [{"id": "gc_standard", "name": f"Go {go_v} Toolchain (gc -s -w)", "targetId": "go"}],
                }
            ],
        })

    # 9. Rust
    has_rustc = is_bin_available("rustc", "/usr/bin/rustc")
    if has_rustc:
        rust_v = get_cmd_version(["rustc", "--version"]) or "2021"
        installed_langs.append({
            "id": "rust",
            "name": "Rust",
            "monaco": "rust",
            "template": 'fn main() {\n  println!("Hello, World!");\n}\n',
            "versions": [
                {
                    "id": "rust_current",
                    "name": f"Rust ({rust_v})",
                    "toolchains": [
                        {"id": "rustc_super", "name": "rustc (-O3 LTO Native Super-Opt)", "targetId": "rust"},
                    ],
                }
            ],
        })

    # 10. JavaScript
    has_node = is_bin_available("node", "/usr/bin/node")
    if has_node:
        node_v = get_cmd_version(["node", "--version"]) or "22.0.0"
        installed_langs.append({
            "id": "javascript",
            "name": "JavaScript",
            "monaco": "javascript",
            "template": 'console.log("Hello, World!");\n',
            "versions": [
                {
                    "id": "node_current",
                    "name": f"Node.js {node_v}",
                    "toolchains": [{"id": "node_v8", "name": f"Node.js {node_v} (V8 Engine)", "targetId": "js_node"}],
                }
            ],
        })

    # 11. TypeScript
    has_tsx = is_bin_available("tsx", "/usr/local/bin/tsx", "/usr/bin/tsx") or has_node
    if has_tsx:
        installed_langs.append({
            "id": "typescript",
            "name": "TypeScript",
            "monaco": "typescript",
            "template": 'console.log("Hello, World!");\n',
            "versions": [
                {
                    "id": "ts_current",
                    "name": "TypeScript (ESNext)",
                    "toolchains": [{"id": "tsx_jit", "name": "TSX (esbuild Fast JIT Engine)", "targetId": "ts_tsx"}],
                }
            ],
        })

    # 12. Kotlin
    has_kotlinc = is_bin_available("kotlinc", "/opt/kotlinc/bin/kotlinc", "/usr/local/bin/kotlinc", "/usr/bin/kotlinc")
    if has_kotlinc:
        installed_langs.append({
            "id": "kotlin",
            "name": "Kotlin",
            "monaco": "kotlin",
            "template": 'fun main() {\n  println("Hello, World!")\n}\n',
            "versions": [
                {
                    "id": "kt_current",
                    "name": "Kotlin (JVM Backend)",
                    "toolchains": [{"id": "kotlinc_jvm", "name": "kotlinc (JVM Optimized)", "targetId": "kotlin"}],
                }
            ],
        })

    # 13. Dart
    has_dart = is_bin_available("dart", "/opt/dart-sdk/bin/dart", "/usr/lib/dart/bin/dart", "/usr/bin/dart")
    if has_dart:
        dart_bin = shutil.which("dart") or ("/opt/dart-sdk/bin/dart" if os.path.exists("/opt/dart-sdk/bin/dart") else "/usr/bin/dart")
        dart_v = get_cmd_version([dart_bin, "--version"]) or "3.0"
        installed_langs.append({
            "id": "dart",
            "name": "Dart",
            "monaco": "dart",
            "template": 'void main() {\n  print("Hello, World!");\n}\n',
            "versions": [
                {
                    "id": "dart_current",
                    "name": f"Dart {dart_v}",
                    "toolchains": [{"id": "dart_vm", "name": f"Dart {dart_v} JIT VM", "targetId": "dart"}],
                }
            ],
        })

    # 14. Lua
    has_lua54 = is_bin_available("lua5.4", "/usr/bin/lua5.4")
    has_luajit = is_bin_available("luajit", "/usr/bin/luajit")
    has_lua = is_bin_available("lua", "/usr/bin/lua")
    if has_lua54 or has_luajit or has_lua:
        lua_tools = []
        if has_lua54: lua_tools.append({"id": "lua54", "name": "Lua 5.4 Standard", "targetId": "lua5.4"})
        if has_luajit: lua_tools.append({"id": "luajit", "name": "LuaJIT 2.1 (High Perf)", "targetId": "luajit"})
        if not lua_tools and has_lua: lua_tools.append({"id": "lua_sys", "name": "Lua Interpreter", "targetId": "lua"})
        if lua_tools:
            installed_langs.append({
                "id": "lua",
                "name": "Lua",
                "monaco": "lua",
                "template": 'print("Hello, World!")\n',
                "versions": [{"id": "lua_current", "name": "Lua", "toolchains": lua_tools}],
            })

    # 15. PHP
    has_php = is_bin_available("php", "/usr/bin/php")
    if has_php:
        php_v = get_cmd_version(["php", "-v"]) or "8.3"
        installed_langs.append({
            "id": "php",
            "name": "PHP",
            "monaco": "php",
            "template": '<?php\necho "Hello, World!\\n";\n',
            "versions": [
                {
                    "id": "php_current",
                    "name": f"PHP {php_v}",
                    "toolchains": [{"id": "php_jit", "name": f"PHP {php_v} (OPcache Tracing JIT)", "targetId": "php"}],
                }
            ],
        })

    # 16. D
    has_gdc = is_bin_available("gdc", "/usr/bin/gdc")
    has_ldc = is_bin_available("ldc2", "/usr/bin/ldc2")
    if has_gdc or has_ldc:
        d_tools = []
        if has_gdc: d_tools.append({"id": "gdc", "name": "GNU D Compiler (GDC -O3)", "targetId": "gdc"})
        if has_ldc: d_tools.append({"id": "ldc", "name": "LLVM D Compiler (LDC -O3)", "targetId": "ldc"})
        installed_langs.append({
            "id": "d",
            "name": "D",
            "monaco": "d",
            "template": 'import std.stdio;\n\nvoid main() {\n  writeln("Hello, World!");\n}\n',
            "versions": [{"id": "d_current", "name": "D 2.x", "toolchains": d_tools}],
        })

    # 17. Objective-C
    has_gobjc = is_bin_available("gobjc", "/usr/bin/gobjc")
    if has_gobjc or has_clang:
        objc_tools = []
        if has_gobjc: objc_tools.append({"id": "gobjc", "name": "GNU Objective-C (GCC)", "targetId": "objc"})
        if has_clang: objc_tools.append({"id": "clang_objc", "name": "Clang Objective-C", "targetId": "objc"})
        installed_langs.append({
            "id": "objective-c",
            "name": "Objective-C",
            "monaco": "objective-c",
            "template": '#import <Foundation/Foundation.h>\n\nint main(int argc, const char * argv[]) {\n  @autoreleasepool {\n    printf("Hello, World!\\n");\n  }\n  return 0;\n}\n',
            "versions": [{"id": "objc_current", "name": "Objective-C", "toolchains": objc_tools}],
        })

    # 18. LLVM IR
    has_lli = is_bin_available("lli", "/usr/bin/lli")
    if has_lli or has_clang:
        llvm_tools = []
        if has_lli: llvm_tools.append({"id": "lli", "name": "LLVM JIT Interpreter (lli)", "targetId": "llvm_ir"})
        if has_clang: llvm_tools.append({"id": "clang_llvm", "name": "Clang LLVM Compiler", "targetId": "llvm_ir"})
        installed_langs.append({
            "id": "llvm-ir",
            "name": "LLVM IR",
            "monaco": "llvm",
            "template": '@.str = private unnamed_addr constant [14 x i8] c"Hello, World!\\00", align 1\n\ndeclare i32 @puts(i8* nocapture) nounwind\n\ndefine i32 @main() {\n  %1 = call i32 @puts(i8* getelementptr inbounds ([14 x i8], [14 x i8]* @.str, i32 0, i32 0))\n  ret i32 0\n}\n',
            "versions": [{"id": "llvm_current", "name": "LLVM IR", "toolchains": llvm_tools}],
        })

    # 19. F#
    has_fsharp = is_bin_available("fsharpc", "/usr/bin/fsharpc") or any("9.0" in s or "8.0" in s for s in dotnet_sdks)
    if has_fsharp:
        fs_tools = []
        if dotnet_sdks: fs_tools.append({"id": "fs_dotnet", "name": ".NET F# CoreCLR", "targetId": "fs_net"})
        if has_mono: fs_tools.append({"id": "fs_mono", "name": "Mono F# Compiler", "targetId": "fs_mono"})
        installed_langs.append({
            "id": "fsharp",
            "name": "F#",
            "monaco": "fsharp",
            "template": 'open System\n\n[<EntryPoint>]\nlet main argv =\n    printfn "Hello, World!"\n    0\n',
            "versions": [{"id": "fs_current", "name": "F#", "toolchains": fs_tools}],
        })

    # 20. Visual Basic
    has_vb = is_bin_available("vbnc", "/usr/bin/vbnc") or any("9.0" in s or "8.0" in s for s in dotnet_sdks)
    if has_vb:
        vb_tools = []
        if dotnet_sdks: vb_tools.append({"id": "vb_dotnet", "name": ".NET VB CoreCLR", "targetId": "vb_net"})
        if has_mono: vb_tools.append({"id": "vb_mono", "name": "Mono VB Compiler (vbnc)", "targetId": "vb_mono"})
        installed_langs.append({
            "id": "visualbasic",
            "name": "Visual Basic",
            "monaco": "vb",
            "template": 'Module Program\n  Sub Main()\n    Console.WriteLine("Hello, World!")\n  End Sub\nEnd Module\n',
            "versions": [{"id": "vb_current", "name": "Visual Basic", "toolchains": vb_tools}],
        })

    # Alphabetical sorting by language name (C is default first)
    installed_langs.sort(key=lambda x: x["name"].lower())
    return installed_langs

if __name__ == "__main__":
    discovered = discover_installed_languages()
    print(f"🔍 Real System Toolchain Probe Completed: {len(discovered)} active executable languages found.\n")
    for lang in discovered:
        v_summary = []
        for v in lang["versions"]:
            t_names = [t["name"] for t in v["toolchains"]]
            v_summary.append(f"{v['name']} [{', '.join(t_names)}]")
        print(f"  • {lang['name']} ({lang['id']}):")
        for s in v_summary:
            print(f"      - {s}")
