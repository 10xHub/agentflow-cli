# import json
# import sys
# import xml.etree.ElementTree as ET
#
#
# def parse_coverage(xml_file):
#     tree = ET.parse(xml_file)
#     root = tree.getroot()
#
#     total_lines = int(root.attrib["lines-valid"])
#     covered_lines = int(root.attrib["lines-covered"])
#     coverage = float(root.attrib["line-rate"]) * 100
#
#     return total_lines, covered_lines, coverage
#
#
# def generate_report(
#     xml_file, build_number, previous_build_number, changed_files
# ):
#     total_lines, covered_lines, coverage = parse_coverage(xml_file)
#
#     report = {
#         "build_number": build_number,
#         "coverage_percentage": f"{coverage:.3f}%",
#         "covered_lines": covered_lines,
#         "total_lines": total_lines,
#         "changed_files": changed_files,
#         "previous_build": previous_build_number,
#         "coverage_increase": "+0.004%",  # need to update real scenerio
#     }
#
#     return json.dumps(report)
#
#
# if __name__ == "__main__":
#     xml_file = "coverage.xml"
#     build_number = sys.argv[1]
#     previous_build_number = sys.argv[2]
#     changed_files = int(sys.argv[3])
#
#     report = generate_report(
#         xml_file, build_number, previous_build_number, changed_files
#     )
