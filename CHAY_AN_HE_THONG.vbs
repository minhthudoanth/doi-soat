Set WshShell = CreateObject("WScript.Shell")
strCurDir = "C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot"
pythonExe = "C:\Users\a1dtm\.gemini\antigravity\scratch\python\pythonw.exe"

WshShell.CurrentDirectory = strCurDir

' 1. Khoi dong Telegram Real-time Listener ngam bang pythonw (khong hien cua so den)
WshShell.Run """" & pythonExe & """ """ & strCurDir & "\telegram_listener.py""", 0, False

' 2. Khoi dong Web Server Dashboard ngam bang pythonw (khong hien cua so den)
WshShell.Run """" & pythonExe & """ """ & strCurDir & "\app.py""", 0, False

' 3. Mo trinh duyet Web Dashboard
WScript.Sleep 2500
WshShell.Run "http://127.0.0.1:5000", 1, False
