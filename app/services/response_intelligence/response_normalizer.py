import re


class ResponseNormalizer:

    @staticmethod
    def normalize(response: str) -> str:

        if not isinstance(response, str):

            raise ValueError(
                "Response must be a string."
            )

        response = response.replace(
            "\r\n",
            "\n",
        )

        response = response.replace(
            "\r",
            "\n",
        )

        # Remove leading and trailing whitespace.
        response = response.strip()

        # Remove trailing spaces from individual lines.
        lines = [
            line.rstrip()
            for line in response.split("\n")
        ]

        response = "\n".join(lines)

        # Prevent excessive blank-line sequences.
        response = re.sub(
            r"\n{3,}",
            "\n\n",
            response,
        )

        # Remove repeated spaces without modifying indentation.
        normalized_lines = []

        for line in response.split("\n"):

            if line.startswith((" ", "\t")):

                normalized_lines.append(line)

            else:

                normalized_lines.append(
                    re.sub(
                        r"[ \t]{2,}",
                        " ",
                        line,
                    )
                )

        return "\n".join(
            normalized_lines
        ).strip()