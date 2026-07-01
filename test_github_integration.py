import unittest

from services.intent_router import IntentRouter


class GitHubIntentRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()

    def test_repository_commands_route_to_github_tools(self) -> None:
        self.assertEqual(
            self.router.route("show my repositories"),
            {"tool": "list_repositories", "arguments": {}},
        )
        self.assertEqual(
            self.router.route("list repositories"),
            {"tool": "list_repositories", "arguments": {}},
        )
        self.assertEqual(
            self.router.route("recent commits"),
            {"tool": "list_recent_commits", "arguments": {"repo": None, "limit": 5}},
        )
        self.assertEqual(
            self.router.route("latest commit"),
            {"tool": "get_commit", "arguments": {"repo": None, "sha": "HEAD"}},
        )
        self.assertEqual(
            self.router.route("repository details"),
            {"tool": "get_repository", "arguments": {"repo": None}},
        )


if __name__ == "__main__":
    unittest.main()
