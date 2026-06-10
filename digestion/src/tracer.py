from lean_dojo_v2.lean_dojo import LeanGitRepo
from lean_dojo_v2.lean_dojo.data_extraction.trace import trace
from lean_dojo_v2.lean_dojo.data_extraction.traced_data import TracedRepo


def trace_github_repo(url: str, commit: str) -> TracedRepo:
    return trace(LeanGitRepo(url, commit), build_deps=False)


def trace_local_repo(path: str) -> TracedRepo:
    return trace(LeanGitRepo.from_path(path), build_deps=False)
