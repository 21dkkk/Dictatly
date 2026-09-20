"""
Compiles native lightweight Dictatly.exe launcher using built-in Windows csc.exe.
Embeds resources/app_icon.ico, sets assembly metadata (Name: Dictatly),
and launches pythonw.exe main.py with 0 console window flickering.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSHARP_CODE = r"""using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

[assembly: AssemblyTitle("Dictatly")]
[assembly: AssemblyProduct("Dictatly")]
[assembly: AssemblyDescription("Dictatly - Local Speech Dictation")]
[assembly: AssemblyCompany("Dictatly")]
[assembly: AssemblyCopyright("Copyright 2026 Dictatly")]
[assembly: AssemblyFileVersion("1.1.1.0")]
[assembly: AssemblyVersion("1.1.1.0")]

namespace DictatlyLauncher
{
    static class Program
    {
        [STAThread]
        static int Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string venvPython = Path.Combine(baseDir, "venv", "Scripts", "pythonw.exe");
                string pythonExe = File.Exists(venvPython) ? venvPython : "pythonw.exe";
                string mainPy = Path.Combine(baseDir, "main.py");

                if (!File.Exists(mainPy))
                {
                    return 1;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonExe;
                
                string passArgs = "\"" + mainPy + "\"";
                if (args != null && args.Length > 0)
                {
                    passArgs += " " + string.Join(" ", args);
                }
                
                psi.Arguments = passArgs;
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
                return 0;
            }
            catch
            {
                return 1;
            }
        }
    }
}
"""

def build():
    csc = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
    if not csc.exists():
        csc = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
    
    if not csc.exists():
        print("[Build] csc.exe not found on system.")
        return False

    temp_cs = ROOT / "Dictatly_Launcher.cs"
    out_exe = ROOT / "Dictatly.exe"
    icon_ico = ROOT / "resources" / "app_icon.ico"

    try:
        temp_cs.write_text(CSHARP_CODE, encoding="utf-8")
        
        cmd = [
            str(csc),
            "/nologo",
            "/target:winexe",
            f"/win32icon:{icon_ico}",
            f"/out:{out_exe}",
            str(temp_cs)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_exe.exists():
            print(f"[Build] Successfully compiled {out_exe} ({out_exe.stat().st_size} bytes)")
            return True
        else:
            print(f"[Build] Compilation failed: {res.stderr}\n{res.stdout}")
            return False
    finally:
        if temp_cs.exists():
            temp_cs.unlink()

if __name__ == "__main__":
    build()
