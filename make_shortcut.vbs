Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "C:\Users\a1dtm\OneDrive\Desktop\DOI_SOAT_KRC.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot\CHAY_DASHBOARD.bat"
oLink.WorkingDirectory = "C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot"
oLink.Description = "He thong Doi Soat KRC"
oLink.Save
