import hashlib, pandas as pd, os, tempfile, boto3

def _basic_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna()                            # drop null rows
    df.columns = [c.lower().strip() for c in df.columns]
    # convert any “*_date” column to proper datetime
    for col in df.columns:
        if col.endswith("_date"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def save_and_checksum(df: pd.DataFrame, fname: str) -> tuple[str, str]:
    tmp_dir = tempfile.gettempdir()
    path = os.path.join(tmp_dir, fname)
    df.to_csv(path, index=False)
    md5 = hashlib.md5(open(path, "rb").read()).hexdigest()
    return path, md5

def upload_to_s3(local_path: str, key: str) -> str:
    """Return presigned URL (5 days) or local path if no S3 env vars set."""
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        return local_path
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    s3.upload_file(local_path, bucket, key)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=86400 * 5,
    )

def process_df(df: pd.DataFrame, outfile_stub: str = "clean.csv") -> tuple[str, str]:
    df = _basic_preprocess(df)
    local, md5 = save_and_checksum(df, outfile_stub)
    url = upload_to_s3(local, outfile_stub)
    return url, md5
