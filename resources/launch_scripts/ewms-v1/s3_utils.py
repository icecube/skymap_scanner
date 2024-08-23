"""Utils for putting files in S3."""

from pathlib import Path

import boto3  # type: ignore[import-untyped]


class S3Utils:
    """Wrapper around boto3."""

    def __init__(
        self,
        endpoint_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        bucket: str,
        key: str,
    ):
        self.s3_client = boto3.client(
            "s3",
            "us-east-1",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self.bucket = bucket
        self.key = key

    def generate_presigned_url(self, expiration: int) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": self.key,
            },
            ExpiresIn=expiration,  # seconds
        )


def s3ify(filepath: Path) -> S3File:
    """Put the file in s3 and return info about it."""

    # get GET url
    s3_file = S3File(get_url, key)

    # check if already there (via other process/container)
    try:
        resp = requests.get(get_url)
        resp.raise_for_status()
        LOGGER.debug(resp)
        LOGGER.info(f"File is already in S3. Using url: {get_url}")
        return s3_file
    except requests.exceptions.HTTPError:
        LOGGER.info("File is not in S3 yet. Posting...")

    # POST
    upload_details = s3_client.generate_presigned_post(bucket, key)
    with open(filepath, "rb") as f:
        response = requests.post(
            upload_details["url"],
            data=upload_details["fields"],
            files={"file": (filepath.name, f)},  # maps filename to obj
        )
    LOGGER.info(f"Upload response: {response.status_code}")
    LOGGER.info(str(response.content))

    return s3_file
