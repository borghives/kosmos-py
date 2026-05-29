from kosmos.ether import UniversalConstants
from dataclasses import dataclass, field
from typing import Protocol
from google.cloud import secretmanager

def is_secret_source_format(s: str) -> bool:
    return s.startswith("__secret:") and s.endswith("__")

def collapse_secret_string(s: str) -> str:
    if is_secret_source_format(s):
        return collapse_secret_source(s)

    parts = s.split(":")

    if len(parts) == 2:
        return summon_secret_manager().access_secret(parts[0], parts[1])

    return summon_secret_manager().access_secret(s, "latest")


def collapse_secret_source(s: str) -> str:
    # check if the string is a holder string
    if not is_secret_source_format(s):
        raise ValueError("Not a secret source string")

    # remove the underscores
    s = s[2 : len(s)-2]

    # split the string by ":"
    parts = s.split(":")

    # check if the string is a source string
    if len(parts) != 3:
        raise ValueError("Invalid secret source string format expect __secret:<name>:<version>__")

    if parts[0] != "secret":
        raise ValueError("Invalid secret source string format expect __secret:<name>:<version>__")

    # return the secret
    return summon_secret_manager().access_secret(parts[1], parts[2])

class SecretManager(Protocol):
    def access_secret(
        self,
        secret_id: str,
        version_id: str = "latest",
        encoding: str = "utf-8",
    ) -> str:
        ...

@dataclass
class GCPSecretManager:
    project_id: str
    _client: secretmanager.SecretManagerServiceClient | None = field(default=None, init=False, repr=False)

    def access_secret(
        self,
        secret_id: str,
        version_id: str = "latest",
        encoding: str = "utf-8",
    ) -> str:
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        response = self._client.access_secret_version(request={"name": name})
        return response.payload.data.decode(encoding)

def summon_secret_manager() -> SecretManager:
    constants = UniversalConstants.collapse()
    if constants.project_id == "":
        raise ValueError("Project ID is missing.  Required for secret manager")
    return GCPSecretManager(project_id=constants.project_id)

