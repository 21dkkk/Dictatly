Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
strPython = strPath & "\venv\Scripts\pythonw.exe"
If Not fso.FileExists(strPython) Then
    strPython = "pythonw.exe"
End If
strScript = strPath & "\main.py"
WshShell.CurrentDirectory = strPath
WshShell.Run """" & strPython & """ """ & strScript & """", 0, False
Set WshShell = Nothing
Set fso = Nothing
