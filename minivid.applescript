on run
	launchMinivid("")
end run

on open droppedItems
	if droppedItems is {} then return
	launchMinivid(POSIX path of (item 1 of droppedItems))
end open

on launchMinivid(videoPath)
	set appPath to POSIX path of (path to me)
	set appDirectory to do shell script "/usr/bin/dirname " & quoted form of appPath
	set scriptPath to appDirectory & "/minivid.py"
	set pythonPath to "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
	set command to quoted form of pythonPath & space & quoted form of scriptPath
	if videoPath is not "" then
		set command to command & space & quoted form of videoPath
	end if
	do shell script command
end launchMinivid
