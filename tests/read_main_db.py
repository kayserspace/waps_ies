import sqlite3

db = sqlite3.connect("waps_pd.db")
cur = db.cursor()

packet_table = cur.execute("SELECT name FROM sqlite_master")

print('Database contains:')

res = cur.execute("SELECT * FROM packets")
packets = res.fetchall()

res = cur.execute("SELECT * FROM images")
images = res.fetchall()

for image in images:
	res = cur.execute("SELECT * FROM packets WHERE image_id=?",
					  [image[0]])
	packet_count = len(res.fetchall())
	print('Image', image[4], 'with', image[10], '/', image[9], 'packets. In database:', packet_count)

res = cur.execute("SELECT * FROM packets WHERE image_id=?",
				  [-1])
unassigned_packets = res.fetchall()
print('Packets with no image assigned:', len(unassigned_packets))

print('Packets:', len(packets))
print('Images:', len(images))
db.close()