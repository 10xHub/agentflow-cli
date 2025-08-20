# import json
# import os
#
# import requests
#
#
# def post_comment(repo, pr_number, token, comment_body):
#     url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
#     headers = {
#         "Authorization": f"token {token}",
#         "Accept": "application/vnd.github.v3+json",
#     }
#     data = {"body": comment_body}
#     response = requests.post(url, headers=headers, json=data, timeout=10)
#     response.raise_for_status()
#
#
# def format_comment(report_data):
#     data = json.loads(report_data)
#     return f"""
#         ## Pull Request Test Coverage Report for Build {data['build_number']}
#
#         - {data['changed_files']} of {data['changed_files']}
#             (100.0%) changed or added relevant lines in 1 file are covered.
#         - No unchanged relevant lines lost coverage.
#         - Overall coverage increased ({data['coverage_increase']})
#             to {data['coverage_percentage']}
#
#         | Totals | |
#         |:--|:--|
#         | Coverage | {data['coverage_percentage']} |
#         | Change from base Build {data['previous_build']} |
#         | {data['coverage_increase']} |
#         | Covered Lines | {data['covered_lines']} |
#         | Relevant Lines | {data['total_lines']} |
#
#         """
#
#
# if __name__ == "__main__":
#     with open("coverage_report.json") as f:
#         report_data = f.read()
#
#     comment_body = format_comment(report_data)
#     repo = os.environ["GITHUB_REPOSITORY"]
#     pr_number = os.environ["PR_NUMBER"]
#     token = os.environ["GITHUB_TOKEN"]
#
#     post_comment(repo, pr_number, token, comment_body)
