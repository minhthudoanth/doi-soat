import os
import subprocess

user_profile = os.environ.get('USERPROFILE', '')
onedrive_desktop = os.path.join(user_profile, 'OneDrive', 'Desktop')
regular_desktop = os.path.join(user_profile, 'Desktop')
desktop = onedrive_desktop if os.path.exists(onedrive_desktop) else regular_desktop

current_dir = os.path.dirname(os.path.abspath(__file__))
target_vbs = os.path.join(current_dir, 'CHAY_AN_HE_THONG.vbs')
shortcut_path = os.path.join(desktop, 'DOI_SOAT_KRC.lnk')

vbs_code = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "wscript.exe"
oLink.Arguments = Chr(34) & "{target_vbs}" & Chr(34)
oLink.WorkingDirectory = "{current_dir}"
oLink.Description = "He thong Doi Soat KRC - Kingfood SCM"
oLink.Save
'''

vbs_file = os.path.join(current_dir, 'make_shortcut.vbs')
with open(vbs_file, 'w', encoding='utf-8') as f:
    f.write(vbs_code)

subprocess.run(['cscript', '//nologo', vbs_file], check=False)
if os.path.exists(vbs_file):
    try:
        os.remove(vbs_file)
    except Exception:
        pass
print("Da tao shortcut tren Desktop thanh cong!")
