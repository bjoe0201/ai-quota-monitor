Dim fso, dir, python, candidates, i
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' Find Python executable
candidates = Array("py", "c:\Python313\python.exe", "c:\Python312\python.exe", "c:\Python311\python.exe")
python = ""
For i = 0 To UBound(candidates)
    If fso.FileExists(candidates(i)) Or InStr(candidates(i), "\") = 0 Then
        python = candidates(i)
        Exit For
    End If
Next
If python = "" Then python = "python"

' Run without any window (0 = hidden, False = don't wait)
Dim shell
Set shell = CreateObject("WScript.Shell")
shell.Run """" & python & """ """ & dir & "\main.py""", 0, False
Set shell = Nothing
Set fso = Nothing
