from typing import Tuple
from time   import time
from sys    import argv
import smolXML as xml
import os

class LOG:
	INFO = 0
	WARN = 1
	ERR  = 2
	DATA  = 3
	DBG  = 4
	STR_INFO = '\033[37m[INFO]: '
	STR_WARN = '\033[33m[WARN]: '
	STR_ERR  = '\033[31m[ERR]:  '
	STR_DATA = '\033[32m[DATA]: '
	STR_DBG  = '\033[32m[DBG]:  '
	COL_DONE = '\033[0m'

	@staticmethod
	def get_str(log_level: int, s: str) -> str:
		if log_level == LOG.INFO:
			s = LOG.STR_INFO + s + LOG.COL_DONE
		elif log_level == LOG.WARN:
			s = LOG.STR_WARN + s + LOG.COL_DONE
		elif log_level == LOG.ERR:
			s = LOG.STR_ERR  + s + LOG.COL_DONE
		elif log_level == LOG.DATA:
			s = LOG.STR_DATA + s + LOG.COL_DONE
		elif log_level == LOG.DBG:
			s = LOG.STR_DBG  + s + LOG.COL_DONE
		else:
			print(f"log() received unexpected value for log_level: {log_level}".ljust(max_line))
			assert(False)
		return s

max_line: int = 0
def log(log_level: int, s: str, new_line: bool = True):
	global max_line
	s = LOG.get_str(log_level, s)
	max_line = max(max_line, len(s))
	s = s.ljust(max_line)
	endc: str
	if new_line:
		max_line = 0
		endc = '\n'
	else:
		endc = '\r'
	print(s, end=endc)

def create_network(data_dir: str, out_csv_path: str):
	log(LOG.INFO, "Creating Network from data files in {data_dir}...")
	csv = open(out_csv_path, "wb")
	csv.write("source,target\n".encode("utf8"))

	files = []
	for d1 in os.listdir(data_dir):
		p1 = os.path.join(data_dir, d1)
		if not os.path.isdir(p1):
			continue
		for d2 in os.listdir(p1):
			p2 = os.path.join(p1, d2)
			if not os.path.isdir(p1):
				continue
			for f in os.listdir(p2):
				fpath = os.path.join(p2, f)
				if fpath.endswith(".xml"):
					files.append(fpath)

	files_wo_edges = []
	edge_count     = 0
	files_count    = len(files)
	log(LOG.DATA, f"Found {files_count} XML files")

	for i in range(files_count):
		log(LOG.DATA, f"{100*(i/files_count):.3f}% done | {edge_count} edges found", False)
		fpath = files[i]
		root = xml.parseFile(fpath)
		docNums = root.getAllElementsOfType("docNumber")
		if len(docNums) == 0:
			log(LOG.ERR, f"No doc-number in {fpath}")
			continue
		if len(docNums[0].children) != 1:
			log(LOG.ERR, f"Found doc-number without exactly one string-child in {fpath}: {docNums[0]}")
			continue

		initial_edge_count = edge_count
		docNum = docNums[0].getStrVal()
		anchors = root.getAllElementsOfType("a")
		for anchor in anchors:
			if "href" not in anchor.attrs:
				log(LOG.WARN, f"anchor without href attribute in {fpath}: {anchor}")
				continue
			link: str = anchor.attrs["href"].strip()
			link_parts = link.split("undocs.org/")
			if len(link_parts) != 2:
				# log(LOG.WARN, f"Found link referring outside of undocs.org in {fpath}: '{link}'")
				continue
			other = "".join(link_parts[1].split("en/")).split("(")[0]
			csv.write(f"{docNum},{other}\n".encode("utf8"))
			edge_count += 1
		if edge_count == initial_edge_count:
			files_wo_edges.append(fpath)
	if len(files_wo_edges) > 0:
		log(LOG.WARN, f"{len(files_wo_edges)} files found without outgoing edges")
	csv.close()
	log(LOG.DATA, f"{edge_count} edges successfully written to {out_csv_path}")


class Node():
	incoming: int
	outgoing: int
	def __init__(self, incoming: int, outgoing: int):
		self.incoming = incoming
		self.outgoing = outgoing

def analyze_network(csv_path: str):
	log(LOG.INFO, f"Analyzing Network stored in {csv_path}...")
	net: dict[str, Node] = {}
	with open(csv_path, "r", encoding="utf8") as csv:
		lines = csv.read().splitlines()[1:] # Ignore header
		for line in lines:
			src, dst = line.split(",")
			if src in net:
				net[src].outgoing += 1
			else:
				net[src] = Node(0, 1)
			if dst in net:
				net[dst].incoming += 1
			else:
				net[dst] = Node(1, 0)
	log(LOG.DATA, f"{len(net)} different nodes found")

	only_incoming_count = 0
	only_outgoing_count = 0
	both_edges_count = 0
	incoming_max = 0
	outgoing_max = 0
	degrees_max  = 0
	max_incoming_node: str
	max_outgoing_node: str
	max_degrees_node:  str
	for (node, val) in net.items():
		if val.incoming == 0:
			only_outgoing_count += 1
		elif val.outgoing == 0:
			only_incoming_count += 1
		else:
			both_edges_count += 1
		if val.incoming > incoming_max:
			incoming_max = val.incoming
			max_incoming_node = node
		if val.outgoing > outgoing_max:
			outgoing_max = val.outgoing
			max_outgoing_node = node
		if val.incoming + val.outgoing > degrees_max:
			degrees_max = val.incoming + val.outgoing
			max_degrees_node = node
	log(LOG.DATA, f"{only_incoming_count} nodes without outgoing connections")
	log(LOG.DATA, f"{only_outgoing_count} nodes without incoming connections")
	log(LOG.DATA, f"{both_edges_count} nodes with incoming & outgoing connections")
	log(LOG.DATA, f"Node with most incoming connections: '{max_incoming_node}' ({incoming_max})")
	log(LOG.DATA, f"Node with most outgoing connections: '{max_outgoing_node}' ({outgoing_max})")
	log(LOG.DATA, f"Node with highest degree: '{max_degrees_node}' ({degrees_max})")


def main():
	start_time = time()

	data_dir: str = "data"
	csv_path: str = os.path.join(data_dir, "edges.csv")
	if not os.path.exists(csv_path):
		create_network(data_dir, csv_path)
	analyze_network(csv_path)

	elapsed = time() - start_time
	if elapsed > 60:
		minutes = int(elapsed/60)
		log(LOG.INFO, f"Program took {minutes}m {(elapsed - minutes*60):.3f}s")
	else:
		log(LOG.INFO, f"Program took {elapsed:.3f}s")


if __name__ == "__main__":
	main()