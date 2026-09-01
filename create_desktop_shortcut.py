import os
import subprocess

desktop = r'C:\Users\a1dtm\OneDrive\Desktop'
target_bat = r'C:\Users\a1dtm\.gemini\antigravity\scratch\kingfood_scm_bot\CHAY_DASHBOARD.bat'
shortcut_path = os.path.join(desktop, 'DOI_SOAT_KRC.lnk')



vbs_code = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "{os.path.dirname(target_bat)}"
oLink.Description = "He thong Doi Soat KRC"
oLink.Save
'''

vbs_file = os.path.join(os.path.dirname(target_bat), 'make_shortcut.vbs')
with open(vbs_file, 'w', encoding='utf-8') as f:
    f.write(vbs_code)

subprocess.run(['cscript', '//nologo', vbs_file], check=False)
print("Da tao shortcut tren Desktop thanh cong!")
