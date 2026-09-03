Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strCurDir = FSO.GetParentFolderName(WScript.ScriptFullName)
pythonExe = FSO.GetAbsolutePathName(strCurDir & "\..\python\python.exe")

If Not FSO.FileExists(pythonExe) Then
    pythonExe = "python.exe"
End If

WshShell.CurrentDirectory = strCurDir

' Kiem tra neu he thong da dang chay roi thi khong khoi dong trung lap
On Error Resume Next
Set objHTTP = CreateObject("MSXML2.ServerXMLHTTP.6.0")
objHTTP.setTimeouts 1000, 1000, 1000, 1000
objHTTP.open "GET", "http://127.0.0.1:5000/api/stats", False
objHTTP.send

If Err.Number = 0 And (objHTTP.Status = 200 Or objHTTP.Status = 302) Then
    WScript.Quit
End If
Err.Clear
On Error GoTo 0

WshShell.Run """" & pythonExe & """ """ & strCurDir & "\telegram_listener.py""", 0, False
WshShell.Run """" & pythonExe & """ """ & strCurDir & "\app.py""", 0, False
