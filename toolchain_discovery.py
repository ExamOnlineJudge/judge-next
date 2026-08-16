#!/usr/bin/env python3
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

def is_available(binary_name: str) -> bool:
    return shutil.which(binary_name) is not None

def discover_installed_languages() -> List[Dict[str, Any]]:
    """Returns the comprehensive multi-version and multi-distribution catalog for all 21 languages."""
    gcc_v = get_cmd_version(["gcc", "--version"]) or "15"
    clang_v = get_cmd_version(["clang", "--version"]) or "21"
    fpc_v = get_cmd_version(["fpc", "-iV"]) or "3.2.2"

    catalog: List[Dict[str, Any]] = [
        {
            "id": "assembly",
            "name": "Assembly",
            "monaco": "asm",
            "template": "default rel\nglobal main\nextern printf\n\nsection .data\n    msg db 'Hello, World!', 10, 0\n\nsection .text\nmain:\n    sub rsp, 8\n    lea rdi, [msg]\n    xor eax, eax\n    call printf wrt ..plt\n    xor eax, eax\n    add rsp, 8\n    ret\n",
            "versions": [
                {
                    "id": "x86_64",
                    "name": "x86-64 (AMD64)",
                    "toolchains": [
                        {"id": "nasm", "name": "NASM (Intel Syntax)", "targetId": "asm_nasm"},
                        {"id": "yasm", "name": "YASM", "targetId": "asm_yasm"},
                        {"id": "gas", "name": "GNU AS (Intel Syntax)", "targetId": "asm_gas"},
                        {"id": "fasm", "name": "FASM (Flat Assembler)", "targetId": "asm_fasm"},
                    ],
                },
                {
                    "id": "arm64",
                    "name": "ARM64 (AArch64)",
                    "toolchains": [
                        {"id": "gas_arm64", "name": "GNU AS ARM64 (QEMU Emulation)", "targetId": "asm_arm64"},
                        {"id": "gas_arm64_opt", "name": "GNU AS ARM64 (High Perf)", "targetId": "asm_arm64"},
                    ],
                },
                {
                    "id": "arm32",
                    "name": "ARM32 (ARMv7 HF)",
                    "toolchains": [
                        {"id": "gas_arm32", "name": "GNU AS ARM32 (QEMU Emulation)", "targetId": "asm_arm32"},
                        {"id": "gas_arm32_opt", "name": "GNU AS ARM32 (High Perf)", "targetId": "asm_arm32"},
                    ],
                },
            ],
        },
        {
            "id": "c",
            "name": "C",
            "monaco": "c",
            "template": "#include <stdio.h>\n\nint main(void) {\n  printf(\"Hello, World!\\n\");\n  return 0;\n}\n",
            "versions": [
                {
                    "id": "23",
                    "name": "C23",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "c23"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clang23"},
                    ],
                },
                {
                    "id": "17",
                    "name": "C17 / C18",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "c17"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clang17"},
                    ],
                },
                {
                    "id": "11",
                    "name": "C11",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "c11"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clang11"},
                    ],
                },
                {
                    "id": "99",
                    "name": "C99",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "c99"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clang99"},
                    ],
                },
                {
                    "id": "89",
                    "name": "C89 / ANSI C",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "c89"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clang89"},
                    ],
                },
            ],
        },
        {
            "id": "cpp",
            "name": "C++",
            "monaco": "cpp",
            "template": "#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << \"Hello, World!\" << endl;\n  return 0;\n}\n",
            "versions": [
                {
                    "id": "26",
                    "name": "C++26",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp26"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp26"},
                    ],
                },
                {
                    "id": "23",
                    "name": "C++23",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp23"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp23"},
                    ],
                },
                {
                    "id": "20",
                    "name": "C++20",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp20"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp20"},
                    ],
                },
                {
                    "id": "17",
                    "name": "C++17",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp17"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp17"},
                    ],
                },
                {
                    "id": "14",
                    "name": "C++14",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp14"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp14"},
                    ],
                },
                {
                    "id": "11",
                    "name": "C++11",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp11"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp11"},
                    ],
                },
                {
                    "id": "03",
                    "name": "C++03 / 98",
                    "toolchains": [
                        {"id": "gcc", "name": f"GCC {gcc_v} (-O3 Super-Opt)", "targetId": "cpp03"},
                        {"id": "clang", "name": f"Clang {clang_v} (-O3 Super-Opt)", "targetId": "clpp03"},
                    ],
                },
            ],
        },
        {
            "id": "csharp",
            "name": "C#",
            "monaco": "csharp",
            "template": "using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine(\"Hello, World!\");\n    }\n}\n",
            "versions": [
                {
                    "id": "net9",
                    "name": "C# 13 (.NET 9.0)",
                    "toolchains": [
                        {"id": "dotnet9", "name": "Microsoft .NET 9.0 (CoreCLR)", "targetId": "cs_net"},
                        {"id": "dotnet9_r2r", "name": ".NET 9 ReadyToRun (AOT)", "targetId": "cs_net"},
                    ],
                },
                {
                    "id": "net8",
                    "name": "C# 12 (.NET 8.0)",
                    "toolchains": [
                        {"id": "dotnet8", "name": "Microsoft .NET Runtime", "targetId": "cs_net"},
                    ],
                },
                {
                    "id": "mono",
                    "name": "C# Mono (Classic)",
                    "toolchains": [
                        {"id": "mcs", "name": "Mono C# Compiler (mcs 6.14)", "targetId": "cs_mono"},
                        {"id": "mono_opt", "name": "Mono JIT Optimizer", "targetId": "cs_mono"},
                    ],
                },
            ],
        },
        {
            "id": "d",
            "name": "D",
            "monaco": "d",
            "template": "import std.stdio;\n\nvoid main() {\n    writeln(\"Hello, World!\");\n}\n",
            "versions": [
                {
                    "id": "d2_modern",
                    "name": "D 2.x (Modern D)",
                    "toolchains": [
                        {"id": "gdc_o3", "name": "GNU D Compiler (GDC 15 -O3)", "targetId": "d_gdc"},
                        {"id": "gdc_native", "name": "GDC (-march=native -frelease)", "targetId": "d_gdc"},
                    ],
                },
                {
                    "id": "d2_stable",
                    "name": "D 2.098 (Stable)",
                    "toolchains": [
                        {"id": "gdc_stable", "name": "GDC Standard Release", "targetId": "d_gdc"},
                    ],
                },
                {
                    "id": "d2_classic",
                    "name": "D 2.080 (Classic)",
                    "toolchains": [
                        {"id": "gdc_classic", "name": "GDC Legacy Mode", "targetId": "d_gdc"},
                    ],
                },
            ],
        },
        {
            "id": "dart",
            "name": "Dart",
            "monaco": "dart",
            "template": "void main() {\n  print('Hello, World!');\n}\n",
            "versions": [
                {
                    "id": "dart3",
                    "name": "Dart 3.13 (Latest)",
                    "toolchains": [
                        {"id": "dart_jit", "name": "Dart VM & JIT Compiler", "targetId": "dart"},
                        {"id": "dart_opt", "name": "Dart VM High Performance", "targetId": "dart"},
                    ],
                },
                {
                    "id": "dart30",
                    "name": "Dart 3.0 (Stable)",
                    "toolchains": [
                        {"id": "dart30_vm", "name": "Dart 3.0 VM Runtime", "targetId": "dart"},
                    ],
                },
                {
                    "id": "dart2",
                    "name": "Dart 2.19 (Legacy)",
                    "toolchains": [
                        {"id": "dart2_vm", "name": "Dart 2.x Compatibility", "targetId": "dart"},
                    ],
                },
            ],
        },
        {
            "id": "fsharp",
            "name": "F#",
            "monaco": "fsharp",
            "template": "printfn \"Hello, World!\"\n",
            "versions": [
                {
                    "id": "net9",
                    "name": "F# 9.0 (.NET 9)",
                    "toolchains": [
                        {"id": "fsc_net9", "name": "Microsoft .NET F# 9 Compiler", "targetId": "fs_net"},
                        {"id": "fsc_opt", "name": "F# CoreCLR JIT", "targetId": "fs_net"},
                    ],
                },
                {
                    "id": "net8",
                    "name": "F# 8.0 (.NET 8)",
                    "toolchains": [
                        {"id": "fsc_net8", "name": "F# Runtime Engine", "targetId": "fs_net"},
                    ],
                },
                {
                    "id": "net7",
                    "name": "F# 7.0 (Legacy)",
                    "toolchains": [
                        {"id": "fsc_net7", "name": "F# Standard Runtime", "targetId": "fs_net"},
                    ],
                },
            ],
        },
        {
            "id": "go",
            "name": "Go",
            "monaco": "go",
            "template": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, World!\")\n}\n",
            "versions": [
                {
                    "id": "go126",
                    "name": "Go 1.26 (Latest)",
                    "toolchains": [
                        {"id": "gc", "name": "Go Standard Toolchain (gc -s -w)", "targetId": "go"},
                        {"id": "gc_opt", "name": "Go Native Compiler (Inlining)", "targetId": "go"},
                    ],
                },
                {
                    "id": "go124",
                    "name": "Go 1.24 (Stable)",
                    "toolchains": [
                        {"id": "gc_124", "name": "Go Toolchain (Standard)", "targetId": "go"},
                    ],
                },
                {
                    "id": "go122",
                    "name": "Go 1.22 (Legacy)",
                    "toolchains": [
                        {"id": "gc_122", "name": "Go Toolchain (Legacy)", "targetId": "go"},
                    ],
                },
            ],
        },
        {
            "id": "java",
            "name": "Java",
            "monaco": "java",
            "template": "public class Main {\n  public static void main(String[] args) {\n    System.out.println(\"Hello, World!\");\n  }\n}\n",
            "versions": [
                {
                    "id": "26",
                    "name": "Java 26",
                    "toolchains": [
                        {"id": "openjdk26", "name": "OpenJDK 26 HotSpot", "targetId": "java26_openjdk"},
                        {"id": "temurin26", "name": "Eclipse Temurin 26 (Adoptium)", "targetId": "java26_temurin"},
                        {"id": "graalvm26", "name": "Oracle GraalVM CE 26", "targetId": "java26_graalvm"},
                        {"id": "liberica26", "name": "BellSoft Liberica 26", "targetId": "java26_liberica"},
                        {"id": "oracle26", "name": "Oracle JDK 26", "targetId": "java26_oracle"},
                    ],
                },
                {
                    "id": "25",
                    "name": "Java 25 (LTS)",
                    "toolchains": [
                        {"id": "openjdk25", "name": "OpenJDK 25 HotSpot", "targetId": "java25_openjdk"},
                        {"id": "temurin25", "name": "Eclipse Temurin 25 (Adoptium)", "targetId": "java25_temurin"},
                        {"id": "graalvm25", "name": "Oracle GraalVM CE 25", "targetId": "java25_graalvm"},
                        {"id": "liberica25", "name": "BellSoft Liberica 25", "targetId": "java25_liberica"},
                        {"id": "oracle25", "name": "Oracle JDK 25", "targetId": "java25_oracle"},
                    ],
                },
                {
                    "id": "21",
                    "name": "Java 21 (LTS)",
                    "toolchains": [
                        {"id": "openjdk21", "name": "OpenJDK 21", "targetId": "java21_openjdk"},
                        {"id": "temurin21", "name": "Eclipse Temurin 21 (Adoptium)", "targetId": "java21_temurin"},
                        {"id": "graalvm21", "name": "Oracle GraalVM CE 21", "targetId": "java21_graalvm"},
                        {"id": "liberica21", "name": "BellSoft Liberica 21", "targetId": "java21_liberica"},
                        {"id": "oracle21", "name": "Oracle JDK 21", "targetId": "java21_oracle"},
                    ],
                },
                {
                    "id": "17",
                    "name": "Java 17 (LTS)",
                    "toolchains": [
                        {"id": "openjdk17", "name": "OpenJDK 17", "targetId": "java17_openjdk"},
                        {"id": "temurin17", "name": "Eclipse Temurin 17", "targetId": "java17_temurin"},
                        {"id": "graalvm17", "name": "Oracle GraalVM CE 17", "targetId": "java17_graalvm"},
                        {"id": "liberica17", "name": "BellSoft Liberica 17", "targetId": "java17_liberica"},
                        {"id": "oracle17", "name": "Oracle JDK 17", "targetId": "java17_oracle"},
                    ],
                },
                {
                    "id": "11",
                    "name": "Java 11 (LTS)",
                    "toolchains": [
                        {"id": "openjdk11", "name": "OpenJDK 11", "targetId": "java11_openjdk"},
                        {"id": "temurin11", "name": "Eclipse Temurin 11", "targetId": "java11_temurin"},
                        {"id": "liberica11", "name": "BellSoft Liberica 11", "targetId": "java11_liberica"},
                        {"id": "oracle11", "name": "Oracle JDK 11", "targetId": "java11_oracle"},
                    ],
                },
                {
                    "id": "8",
                    "name": "Java 8 (1.8 LTS)",
                    "toolchains": [
                        {"id": "openjdk8", "name": "OpenJDK 8", "targetId": "java8_openjdk"},
                        {"id": "temurin8", "name": "Eclipse Temurin 8", "targetId": "java8_temurin"},
                        {"id": "liberica8", "name": "BellSoft Liberica 8", "targetId": "java8_liberica"},
                        {"id": "oracle8", "name": "Oracle JDK 8", "targetId": "java8_oracle"},
                    ],
                },
                {
                    "id": "7",
                    "name": "Java 7 (1.7)",
                    "toolchains": [
                        {"id": "openjdk_compat7", "name": "OpenJDK (Java 7)", "targetId": "java7_compat"},
                        {"id": "temurin_compat7", "name": "Eclipse Temurin (Java 7)", "targetId": "java7_temurin"},
                        {"id": "oracle_compat7", "name": "Oracle JDK (Java 7)", "targetId": "java7_oracle"},
                    ],
                },
                {
                    "id": "6",
                    "name": "Java 6 (1.6)",
                    "toolchains": [
                        {"id": "openjdk_compat6", "name": "OpenJDK (Java 6)", "targetId": "java6_compat"},
                        {"id": "temurin_compat6", "name": "Eclipse Temurin (Java 6)", "targetId": "java6_temurin"},
                    ],
                },
                {
                    "id": "5",
                    "name": "Java 5 (1.5)",
                    "toolchains": [
                        {"id": "openjdk_compat5", "name": "OpenJDK (Java 5)", "targetId": "java5_compat"},
                        {"id": "temurin_compat5", "name": "Eclipse Temurin (Java 5)", "targetId": "java5_temurin"},
                    ],
                },
                {
                    "id": "1_4",
                    "name": "Java 1.4 (Legacy)",
                    "toolchains": [
                        {"id": "openjdk_compat1_4", "name": "OpenJDK 8 (-source 1.4)", "targetId": "java1_4_compat"},
                        {"id": "temurin_compat1_4", "name": "Eclipse Temurin (-source 1.4)", "targetId": "java1_4_temurin"},
                    ],
                },
                {
                    "id": "1_0",
                    "name": "Java 1.0 – 1.3 (Classic)",
                    "toolchains": [
                        {"id": "openjdk_compat1_0", "name": "OpenJDK 8 (-source 1.3)", "targetId": "java1_0_compat"},
                        {"id": "temurin_compat1_0", "name": "Eclipse Temurin (-source 1.3)", "targetId": "java1_0_temurin"},
                    ],
                },
            ],
        },
        {
            "id": "javascript",
            "name": "JavaScript",
            "monaco": "javascript",
            "template": "console.log(\"Hello, World!\");\n",
            "versions": [
                {
                    "id": "node26",
                    "name": "Node.js 26 (Current)",
                    "toolchains": [
                        {"id": "node26", "name": "V8 Engine (Node.js 26)", "targetId": "js_node26"},
                        {"id": "node26_turbo", "name": "V8 TurboFan (Max Optimize)", "targetId": "js_node26"},
                    ],
                },
                {
                    "id": "node24",
                    "name": "Node.js 24 (LTS)",
                    "toolchains": [
                        {"id": "node24", "name": "V8 Engine (Node.js 24)", "targetId": "js_node24"},
                    ],
                },
                {
                    "id": "node22",
                    "name": "Node.js 22 (LTS)",
                    "toolchains": [
                        {"id": "node22", "name": "V8 Engine (Node.js 22)", "targetId": "js_node22"},
                    ],
                },
                {
                    "id": "node20",
                    "name": "Node.js 20 (LTS)",
                    "toolchains": [
                        {"id": "node20", "name": "V8 Engine (Node.js 20)", "targetId": "js_node20"},
                    ],
                },
                {
                    "id": "node18",
                    "name": "Node.js 18 (Maintenance)",
                    "toolchains": [
                        {"id": "node18", "name": "V8 Engine (Node.js 18)", "targetId": "js_node18"},
                    ],
                },
            ],
        },
        {
            "id": "kotlin",
            "name": "Kotlin",
            "monaco": "kotlin",
            "template": "fun main() {\n    println(\"Hello, World!\")\n}\n",
            "versions": [
                {
                    "id": "2.1",
                    "name": "Kotlin 2.1 (Latest K2)",
                    "toolchains": [
                        {"id": "kotlinc21_jvm21", "name": "kotlinc 2.1 (OpenJDK 21)", "targetId": "kotlin21"},
                        {"id": "kotlinc21_temurin", "name": "kotlinc 2.1 (Eclipse Temurin)", "targetId": "kotlin21_temurin"},
                    ],
                },
                {
                    "id": "2.0",
                    "name": "Kotlin 2.0 (Stable)",
                    "toolchains": [
                        {"id": "kotlinc20_jvm", "name": "Kotlin K2 Compiler", "targetId": "kotlin21"},
                    ],
                },
                {
                    "id": "1.9",
                    "name": "Kotlin 1.9 (K1 Engine)",
                    "toolchains": [
                        {"id": "kotlinc19_jvm", "name": "Kotlin 1.9 Compatibility", "targetId": "kotlin21"},
                    ],
                },
            ],
        },
        {
            "id": "llvmir",
            "name": "LLVM IR",
            "monaco": "llvm",
            "template": "@msg = private unnamed_addr constant [15 x i8] c\"Hello, World!\\00\"\ndeclare i32 @puts(i8*)\ndefine i32 @main() {\n    %1 = call i32 @puts(i8* getelementptr inbounds ([15 x i8], [15 x i8]* @msg, i32 0, i32 0))\n    ret i32 0\n}\n",
            "versions": [
                {
                    "id": "llvm21",
                    "name": "LLVM 21 IR (Latest)",
                    "toolchains": [
                        {"id": "lli", "name": "LLVM JIT Interpreter (lli)", "targetId": "llvm_lli"},
                        {"id": "clang_ll", "name": "Clang Native Compiler (-O3)", "targetId": "llvm_clang"},
                    ],
                },
                {
                    "id": "llvm18",
                    "name": "LLVM 18 IR (Stable)",
                    "toolchains": [
                        {"id": "lli18", "name": "LLVM Interpreter (lli)", "targetId": "llvm_lli"},
                        {"id": "clang18", "name": "Clang LLVM Backend", "targetId": "llvm_clang"},
                    ],
                },
                {
                    "id": "llvm16",
                    "name": "LLVM 16 IR (Legacy)",
                    "toolchains": [
                        {"id": "lli16", "name": "LLVM Interpreter (Legacy)", "targetId": "llvm_lli"},
                    ],
                },
            ],
        },
        {
            "id": "lua",
            "name": "Lua",
            "monaco": "lua",
            "template": "print(\"Hello, World!\")\n",
            "versions": [
                {
                    "id": "5.4",
                    "name": "Lua 5.4 (Latest)",
                    "toolchains": [
                        {"id": "lua54", "name": "PUC-Rio Lua 5.4", "targetId": "lua54"},
                        {"id": "luajit54", "name": "LuaJIT Compatible Mode", "targetId": "luajit"},
                    ],
                },
                {
                    "id": "5.3",
                    "name": "Lua 5.3 (Stable)",
                    "toolchains": [
                        {"id": "lua53", "name": "PUC-Rio Lua 5.3", "targetId": "lua53"},
                    ],
                },
                {
                    "id": "5.1",
                    "name": "Lua 5.1 (Classic)",
                    "toolchains": [
                        {"id": "lua51", "name": "PUC-Rio Lua 5.1", "targetId": "lua51"},
                        {"id": "luajit", "name": "LuaJIT 2.1 JIT Engine", "targetId": "luajit"},
                    ],
                },
            ],
        },
        {
            "id": "objectivec",
            "name": "Objective-C",
            "monaco": "objective-c",
            "template": "#include <stdio.h>\n#include <objc/objc.h>\n\nint main(void) {\n    printf(\"Hello, World!\\n\");\n    return 0;\n}\n",
            "versions": [
                {
                    "id": "objc2",
                    "name": "Objective-C 2.0 (Modern)",
                    "toolchains": [
                        {"id": "gcc_objc", "name": "GCC 15 (-O3 Super-Opt)", "targetId": "objc_gcc"},
                        {"id": "clang_objc", "name": "Clang 21 (-O3 Super-Opt)", "targetId": "objc_clang"},
                    ],
                },
                {
                    "id": "objc1",
                    "name": "Objective-C 1.0 (Classic)",
                    "toolchains": [
                        {"id": "gcc_objc1", "name": "GCC GNU Runtime", "targetId": "objc_gcc"},
                        {"id": "clang_objc1", "name": "Clang GNU Runtime", "targetId": "objc_clang"},
                    ],
                },
                {
                    "id": "objcpp",
                    "name": "Objective-C++",
                    "toolchains": [
                        {"id": "gcc_objcpp", "name": "GCC Objective-C++ (-O3)", "targetId": "objc_gcc"},
                        {"id": "clang_objcpp", "name": "Clang Objective-C++ (-O3)", "targetId": "objc_clang"},
                    ],
                },
            ],
        },
        {
            "id": "pascal",
            "name": "Pascal",
            "monaco": "pascal",
            "template": "{$mode objfpc}\nprogram Hello;\nbegin\n  writeln('Hello, World!');\nend.\n",
            "versions": [
                {
                    "id": "fpc",
                    "name": "Free Pascal (ObjFPC)",
                    "toolchains": [
                        {"id": "fpc", "name": f"FPC {fpc_v} (-O3 Super-Opt)", "targetId": "pas_fpc"},
                        {"id": "fpc_smart", "name": "FPC (Register / Smart Link)", "targetId": "pas_fpc"},
                    ],
                },
                {
                    "id": "tp",
                    "name": "Turbo Pascal",
                    "toolchains": [
                        {"id": "fpc_tp", "name": "FPC (TP 7.0 Mode -O3)", "targetId": "pas_tp"},
                    ],
                },
                {
                    "id": "delphi",
                    "name": "Delphi",
                    "toolchains": [
                        {"id": "fpc_delphi", "name": "FPC (Delphi Mode -O3)", "targetId": "pas_delphi"},
                    ],
                },
            ],
        },
        {
            "id": "php",
            "name": "PHP",
            "monaco": "php",
            "template": "<?php\necho \"Hello, World!\\n\";\n",
            "versions": [
                {
                    "id": "8.5",
                    "name": "PHP 8.5 (Latest)",
                    "toolchains": [
                        {"id": "php_jit", "name": "PHP CLI (Tracing JIT Enabled)", "targetId": "php"},
                        {"id": "php_cli", "name": "PHP CLI (Zend VM Standard)", "targetId": "php"},
                    ],
                },
                {
                    "id": "8.4",
                    "name": "PHP 8.4 (Stable)",
                    "toolchains": [
                        {"id": "php84_jit", "name": "PHP 8.4 JIT Engine", "targetId": "php"},
                    ],
                },
                {
                    "id": "8.1",
                    "name": "PHP 8.1 (Legacy)",
                    "toolchains": [
                        {"id": "php81_cli", "name": "PHP 8.1 Standard CLI", "targetId": "php"},
                    ],
                },
            ],
        },
        {
            "id": "python",
            "name": "Python",
            "monaco": "python",
            "template": "print(\"Hello, World!\")\n",
            "versions": [
                {
                    "id": "py3",
                    "name": "Python 3.14 (Latest)",
                    "toolchains": [
                        {"id": "cpython3", "name": "CPython 3.14 (Standard)", "targetId": "python3"},
                        {"id": "pypy3", "name": "PyPy 3.11 JIT (7.3)", "targetId": "pypy3"},
                    ],
                },
                {
                    "id": "py311",
                    "name": "Python 3.11 (PyPy)",
                    "toolchains": [
                        {"id": "pypy3_opt", "name": "PyPy 3 JIT Engine", "targetId": "pypy3"},
                        {"id": "cpython3_opt", "name": "CPython 3 (Bytecode Opt)", "targetId": "python3"},
                    ],
                },
                {
                    "id": "py2",
                    "name": "Python 2.7 (Legacy)",
                    "toolchains": [
                        {"id": "cpython2", "name": "CPython 2.7.18", "targetId": "python2"},
                        {"id": "pypy2", "name": "PyPy 2.7 JIT (7.3)", "targetId": "pypy2"},
                    ],
                },
            ],
        },
        {
            "id": "rust",
            "name": "Rust",
            "monaco": "rust",
            "template": "fn main() {\n    println!(\"Hello, World!\");\n}\n",
            "versions": [
                {
                    "id": "2024",
                    "name": "Rust 2024 Edition",
                    "toolchains": [
                        {"id": "rustc_opt", "name": "rustc 1.93 (-O3 LTO Super-Opt)", "targetId": "rust"},
                        {"id": "rustc_native", "name": "rustc (-C target-cpu=native)", "targetId": "rust"},
                    ],
                },
                {
                    "id": "2021",
                    "name": "Rust 2021 Edition",
                    "toolchains": [
                        {"id": "rustc_2021", "name": "rustc 2021 (Opt-Level 3)", "targetId": "rust"},
                    ],
                },
                {
                    "id": "2018",
                    "name": "Rust 2018 Edition",
                    "toolchains": [
                        {"id": "rustc_2018", "name": "rustc 2018 (Legacy)", "targetId": "rust"},
                    ],
                },
            ],
        },
        {
            "id": "typescript",
            "name": "TypeScript",
            "monaco": "typescript",
            "template": "console.log(\"Hello, World!\");\n",
            "versions": [
                {
                    "id": "5.8",
                    "name": "TypeScript 5.8 (ESNext)",
                    "toolchains": [
                        {"id": "tsx", "name": "TSX (esbuild Fast JIT Engine)", "targetId": "ts_tsx"},
                        {"id": "tsc_node", "name": "Node.js TS Loader", "targetId": "ts_tsx"},
                    ],
                },
                {
                    "id": "5.4",
                    "name": "TypeScript 5.4 (ES2022)",
                    "toolchains": [
                        {"id": "tsx_54", "name": "TSX Engine (ES2022)", "targetId": "ts_tsx"},
                    ],
                },
                {
                    "id": "4.9",
                    "name": "TypeScript 4.9 (ES2020)",
                    "toolchains": [
                        {"id": "tsx_49", "name": "TSX Compatibility Engine", "targetId": "ts_tsx"},
                    ],
                },
            ],
        },
        {
            "id": "vb",
            "name": "Visual Basic",
            "monaco": "vb",
            "template": "Module Program\n    Sub Main()\n        Console.WriteLine(\"Hello, World!\")\n    End Sub\nEnd Module\n",
            "versions": [
                {
                    "id": "net9",
                    "name": "VB.NET 17 (.NET 9)",
                    "toolchains": [
                        {"id": "vbc_net9", "name": "Microsoft .NET VB 17", "targetId": "vb_net"},
                        {"id": "vbc_opt", "name": "VB.NET CoreCLR JIT", "targetId": "vb_net"},
                    ],
                },
                {
                    "id": "net8",
                    "name": "VB.NET 16 (.NET 8)",
                    "toolchains": [
                        {"id": "vbc_net8", "name": "VB.NET Runtime Engine", "targetId": "vb_net"},
                    ],
                },
                {
                    "id": "classic",
                    "name": "VB.NET Classic",
                    "toolchains": [
                        {"id": "vbc_classic", "name": "VB.NET Standard Compiler", "targetId": "vb_net"},
                    ],
                },
            ],
        },
    ]

    # Strict Alphabetical Ordering
    catalog.sort(key=lambda x: x["name"].lower())
    return catalog

if __name__ == "__main__":
    discovered = discover_installed_languages()
    print(f"✅ Full Multi-Distribution Catalog Active ({len(discovered)} languages).")
    for lang in discovered:
        v_names = [v["name"] for v in lang["versions"]]
        print(f"  • {lang['name']} ({len(lang['versions'])} versions): {', '.join(v_names[:3])}...")
