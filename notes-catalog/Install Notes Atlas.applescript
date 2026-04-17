set packageVersion to "0.1"
set packageName to "Notes Atlas v" & packageVersion
set atlasURL to "http://127.0.0.1:8765/"
set automationSettingsURL to "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"

set installerBundlePath to POSIX path of (path to me)
if installerBundlePath ends with "/" then
	set installerBundlePath to text 1 thru -2 of installerBundlePath
end if
set sourceRoot to do shell script "/usr/bin/dirname " & quoted form of installerBundlePath
set sourceCatalog to sourceRoot & "/notes-catalog"
set sourceLauncher to sourceRoot & "/Notes Atlas.app"

try
	do shell script "/bin/test -d " & quoted form of sourceCatalog
	do shell script "/bin/test -d " & quoted form of sourceLauncher
on error
	display alert "Installer package is incomplete" message "This installer needs to sit next to the Notes Atlas package root and the Notes Atlas launcher app." as warning
	return
end try

try
	do shell script "/usr/bin/python3 --version"
on error
	set pythonDialog to display dialog "Notes Atlas needs Python 3 on macOS. Click “Install Python Support” to trigger Apple’s Command Line Tools installer, then run this installer again after that finishes." buttons {"Cancel", "Install Python Support"} default button "Install Python Support"
	if button returned of pythonDialog is "Install Python Support" then
		try
			do shell script "/usr/bin/xcode-select --install"
		end try
	end if
	return
end try

display dialog "This will install " & packageName & " from:\n" & sourceRoot & "\n\nThe installer will copy the full working package, including the Notes Atlas launcher app, installer app, local catalog database, and recovery files." buttons {"Cancel", "Continue"} default button "Continue"

try
	set chosenFolder to choose folder with prompt "Choose the folder where " & packageName & " should be installed. The installer will create a '" & packageName & "' folder there."
on error number -128
	return
end try

set destinationParent to POSIX path of chosenFolder
if destinationParent ends with "/" then
	set destinationParent to text 1 thru -2 of destinationParent
end if
set installRoot to destinationParent & "/" & packageName
set installReadme to installRoot & "/README.md"
set installLauncher to installRoot & "/Notes Atlas.app"

set alreadyExists to false
try
	do shell script "/bin/test -e " & quoted form of installRoot
	set alreadyExists to true
end try

if alreadyExists then
	set replaceDialog to display dialog "A folder already exists at:\n" & installRoot & "\n\nReplace it with this " & packageName & " package?" buttons {"Cancel", "Replace"} default button "Replace" with icon caution
	if button returned of replaceDialog is not "Replace" then return
	do shell script "/bin/rm -rf " & quoted form of installRoot
end if

do shell script "/usr/bin/ditto " & quoted form of sourceRoot & " " & quoted form of installRoot
do shell script "/bin/chmod +x " & quoted form of (installRoot & "/notes-catalog/launch.sh") & " " & quoted form of (installRoot & "/notes-catalog/launch_background.sh")

set dockChoice to button returned of (display dialog packageName & " has been installed at:\n" & installRoot & "\n\nNext steps:\n1. Open Notes Atlas.\n2. When macOS asks for permission to control Notes or Safari, click Allow.\n3. If you ever deny permission, reopen System Settings > Privacy & Security > Automation and enable Notes Atlas, Python, and osascript for Notes and Safari.\n\nWould you like to add the installed launcher to the Dock?" buttons {"Skip Dock", "Add to Dock"} default button "Add to Dock")

if dockChoice is "Add to Dock" then
	do shell script "/usr/bin/python3 - <<'PY'\nimport plistlib\nfrom pathlib import Path\nplist_path = Path.home() / 'Library/Preferences/com.apple.dock.plist'\napp_path = Path(" & quoted form of installLauncher & ")\napp_uri = app_path.as_uri() + '/'\nwith plist_path.open('rb') as f:\n    data = plistlib.load(f)\napps = data.get('persistent-apps', [])\nexists = False\nfor item in apps:\n    file_data = item.get('tile-data', {}).get('file-data', {})\n    if file_data.get('_CFURLString') in {app_uri, str(app_path), str(app_path) + '/'}:\n        exists = True\n        break\nif not exists:\n    apps.append({\n        'tile-data': {\n            'file-data': {\n                '_CFURLString': app_uri,\n                '_CFURLStringType': 15,\n            },\n            'file-label': 'Notes Atlas',\n        },\n        'tile-type': 'file-tile',\n    })\n    data['persistent-apps'] = apps\n    with plist_path.open('wb') as f:\n        plistlib.dump(data, f)\nPY\nkillall Dock"
end if

set finalChoice to button returned of (display dialog packageName & " is installed.\n\nYou can launch it from:\n" & installLauncher & "\n\nWould you like to open the installed README, open Automation settings, or launch Notes Atlas now?" buttons {"Done", "Open README", "Open Settings", "Launch Notes Atlas"} default button "Launch Notes Atlas")

if finalChoice is "Open README" then
	do shell script "/usr/bin/open -a TextEdit " & quoted form of installReadme
else if finalChoice is "Open Settings" then
	open location automationSettingsURL
else if finalChoice is "Launch Notes Atlas" then
	do shell script "/usr/bin/open " & quoted form of installLauncher
end if
