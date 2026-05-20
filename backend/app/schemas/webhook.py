from pydantic import BaseModel


class GitHubCommit(BaseModel):
    id: str
    message: str
    author: dict
    url: str | None = None


class GitHubPusher(BaseModel):
    name: str
    email: str | None = None


class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    clone_url: str | None = None


class GitHubPushPayload(BaseModel):
    ref: str
    before: str | None = None
    after: str | None = None
    commits: list[GitHubCommit] = []
    pusher: GitHubPusher | None = None
    repository: GitHubRepository | None = None


class WebhookTriggerResponse(BaseModel):
    received: bool
    eval_run_id: str | None = None
    message: str
