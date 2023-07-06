import os

dir_list = [x[0] for x in os.walk('.') ]

print(dir_list)


for dr in dir_list[1:]:

	os.chdir(dr)

	dr = dr[2:]

	print(dr)

	command = "mdb-tables -1 "+ dr + ".mdb | xargs -I{} bash -c 'mdb-export " + dr + ".mdb " + '"$1"' + "> " + '"$1"'+ ".csv' -- {}"

	print(command)

	os.system(command)

	os.chdir('..')


