import json
import subprocess
import sys
import urllib.error
import urllib.request


BASE_URL = "http://localhost:8080"


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Command failed."
        )

    return result.stdout


def check_http(path):
    try:
        with urllib.request.urlopen(
            BASE_URL + path,
            timeout=10,
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"{path}: HTTP {response.status}"
                )

            return response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"{path}: HTTP {exc.code}"
        ) from exc


def main():
    print("\nScholarAI Docker Deployment Verification\n")

    output = run_command([
        "docker",
        "compose",
        "ps",
        "-a",
        "--format",
        "json",
    ])

    # Docker Compose outputs JSON Lines, not one JSON document.
    services = [
        json.loads(line)
        for line in output.splitlines()
        if line.strip()
    ]

    required = {"db", "backend", "frontend"}

    service_map = {
        item.get("Service"): item
        for item in services
    }

    missing = required - service_map.keys()

    if missing:
        raise RuntimeError(
            f"Missing services: {sorted(missing)}"
        )

    for name in sorted(required):
        service = service_map[name]

        state = service.get("State")
        health = service.get("Health", "")

        print(
            f"{name}: state={state}, health={health}"
        )

        if state != "running":
            raise RuntimeError(
                f"{name} is not running."
            )

        if health != "healthy":
            raise RuntimeError(
                f"{name} is not healthy."
            )

    # Migration is a one-time job and should exit successfully.
    migration = service_map.get("migrate")

    if not migration:
        raise RuntimeError("Migration service is missing.")

    state = migration.get("State")
    exit_code = int(migration.get("ExitCode", -1))

    print(f"migrate: state={state}, exit_code={exit_code}")

    if state != "exited" or exit_code != 0:
        raise RuntimeError("Database migration did not complete successfully.")
    home = check_http("/")

    if "ScholarAI" not in home:
        raise RuntimeError(
            "Frontend HTML does not contain ScholarAI."
        )

    check_http("/nginx-health")

    health = json.loads(check_http("/health"))

    if health.get("status") != "healthy":
        raise RuntimeError(
            "Backend health check failed."
        )

    database = json.loads(
        check_http("/health/database")
    )

    if (
        database.get("status") != "healthy"
        or database.get("database") != "connected"
    ):
        raise RuntimeError(
            "Database health check failed."
        )

    print("\nAll deployment verification checks passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"\nDEPLOYMENT VERIFICATION FAILED: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)