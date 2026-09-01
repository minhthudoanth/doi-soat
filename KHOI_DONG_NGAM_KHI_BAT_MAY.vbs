Set WshShell = CreateObject("WScript.Shell")
strCurDir = "C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot"
pythonExe = "C:\Users\a1dtm\.gemini\antigravity\scratch\python\pythonw.exe"

WshShell.CurrentDirectory = strCurDir

WshShell.Run """" & pythonExe & """ """ & strCurDir & "\telegram_listener.py""", 0, False
WshShell.Run """" & pythonExe & """ """ & strCurDir & "\app.py""", 0, False
