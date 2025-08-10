def print_pdf(path):
	import sys, os
	if sys.platform != "win32":
		return False
	try:
		os.startfile(path, "print")
		return True
	except Exception:
		return False


def open_file(path):
	import sys, os, subprocess
	if sys.platform == "win32":
		try:
			os.startfile(path)
			return True
		except Exception:
			return False
	else:
		try:
			subprocess.Popen(["xdg-open", path]); return True
		except Exception:
			return False

