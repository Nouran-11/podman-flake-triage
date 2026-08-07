import json, zipfile

index = json.load(open("cache/index.json"))
entry = index["31093799884_1"]
z = zipfile.ZipFile(entry["logs_path"])

data = z.read("44_windows machine hyperv.txt").decode("utf-8", errors="replace")
lines = data.splitlines()

error_lines = [n for n, line in enumerate(lines) if "##[error]" in line]
last = error_lines[-1]

print(f"last error at line {last} of {len(lines)}\n")
for line in lines[last - 30:last + 1]:
    print(line[29:])
