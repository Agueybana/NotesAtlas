set atlasURL to "http://127.0.0.1:8765/"
set atlasURLPrefix to "http://127.0.0.1:8765"

set appBundlePath to POSIX path of (path to me)
if appBundlePath ends with "/" then
	set appBundlePath to text 1 thru -2 of appBundlePath
end if
set packageRoot to do shell script "/usr/bin/dirname " & quoted form of appBundlePath
set launcherScript to packageRoot & "/notes-catalog/launch_background.sh"

do shell script "/bin/zsh " & quoted form of launcherScript

set ready to false
repeat 20 times
	try
		do shell script "/usr/bin/curl -fsS " & quoted form of atlasURLPrefix & " >/dev/null"
		set ready to true
		exit repeat
	on error
		delay 0.4
	end try
end repeat

if ready is false then
	display alert "Notes Atlas could not start" message "The local Notes Atlas server did not respond on http://127.0.0.1:8765." as warning
	return
end if

tell application "Safari"
	activate
	if (count of windows) is 0 then
		make new document with properties {URL:atlasURL}
		return
	end if

	set foundTab to missing value
	set foundWindow to missing value
	repeat with w in windows
		repeat with t in tabs of w
			try
				set tabURL to URL of t
			on error
				set tabURL to ""
			end try
			if tabURL starts with atlasURLPrefix then
				set foundTab to t
				set foundWindow to w
				exit repeat
			end if
		end repeat
		if foundTab is not missing value then exit repeat
	end repeat

	if foundTab is missing value then
		tell front window
			set current tab to (make new tab with properties {URL:atlasURL})
		end tell
	else
		set index of foundWindow to 1
		set current tab of foundWindow to foundTab
		set URL of foundTab to atlasURL
	end if
end tell
