#!/usr/bin/env bash
# provision_telemetry_bucket.sh — stand up the write-only S3 drop bucket for racecar
# fleet telemetry, idempotently, inside one specific AWS account.
#
# The "put but not see" sink (see shared/DRIFT.md): contributors get an IAM user whose
# ONLY permission is s3:PutObject under s3://<bucket>/<prefix>/* — no Get, no List — so a
# machine can drop its anonymized telemetry object but can neither read the aggregate nor
# see other repos. The aggregator gets a separate Get+List policy. Objects are immutable
# (each push is a new key) and expire on a lifecycle rule (retention/rollup).
#
# STATUS. This is the S3 option for racecar's still-undecided telemetry transport (the
# network write; see shared/DRIFT.md). It is UNWIRED — no push/pull companion consumes it
# yet — and UNTESTED against live AWS. It is committed so the working, parameterized tooling
# is not lost while the sink (S3 drop-bucket vs. a write-API + DB) stays deferred. It changes
# nothing until run, and --dry-run is the default; review the printed commands before --apply.
#
# TARGETING AN ORG MEMBER ACCOUNT. Run with a --profile that resolves INTO the dedicated
# account (an IAM Identity Center / SSO profile, or an assumed OrganizationAccountAccessRole).
# The script asserts the caller's account matches --account-id before it touches anything, so
# it can never provision into the wrong account.
#
# SAFETY. Defaults to a DRY RUN: it prints every aws command (and runs only the read-only
# preflight) so you can review. Re-run with --apply to execute. Idempotent — safe to re-run.
#
# Requires: aws CLI v2, configured with admin rights in the target account.
#
# Usage:
#   scripts/provision_telemetry_bucket.sh \
#     --account-id 123456789012 \
#     --bucket racecar-telemetry-acme \
#     --region us-east-1 \
#     --retention-days 90 \
#     [--prefix telemetry] [--profile my-sso-profile] [--apply]
set -euo pipefail

REGION="us-east-1"
RETENTION_DAYS=90
PREFIX="telemetry"
PROFILE=""
APPLY=0
ACCOUNT_ID=""
BUCKET=""

CONTRIB_USER="racecar-telemetry-contributor"
CONTRIB_POLICY="racecar-telemetry-put"
AGG_POLICY="racecar-telemetry-read"

die() { echo "provision_telemetry_bucket: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --account-id) ACCOUNT_ID="$2"; shift 2 ;;
        --bucket) BUCKET="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
        --prefix) PREFIX="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --apply) APPLY=1; shift ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$ACCOUNT_ID" ] || die "--account-id is required (the 12-digit target account)"
[ -n "$BUCKET" ] || die "--bucket is required (globally-unique bucket name)"
command -v aws >/dev/null 2>&1 || die "aws CLI not found; install aws CLI v2"

AWS=(aws)
[ -n "$PROFILE" ] && AWS+=(--profile "$PROFILE")

# Read-only preflight always runs (even in dry-run): confirm we are in the intended account.
CALLER_ACCT="$("${AWS[@]}" sts get-caller-identity --query Account --output text)" \
    || die "could not call sts get-caller-identity; is --profile set and logged in?"
if [ "$CALLER_ACCT" != "$ACCOUNT_ID" ]; then
    die "credentials are in account $CALLER_ACCT, not the intended $ACCOUNT_ID.
  Set --profile to a profile/role that resolves into the dedicated org member account."
fi
echo "provision_telemetry_bucket: account $CALLER_ACCT confirmed; region $REGION; bucket $BUCKET"
[ "$APPLY" = 1 ] || echo ">>> DRY RUN — printing commands only. Re-run with --apply to execute. <<<"

# run: echo the command, and execute it only under --apply.
run() {
    echo "+ ${AWS[*]} $*"
    [ "$APPLY" = 1 ] && "${AWS[@]}" "$@"
    return 0
}

ARN_PREFIX="arn:aws:s3:::${BUCKET}/${PREFIX}/*"
POLICY_ARN_PUT="arn:aws:iam::${ACCOUNT_ID}:policy/${CONTRIB_POLICY}"
POLICY_ARN_READ="arn:aws:iam::${ACCOUNT_ID}:policy/${AGG_POLICY}"

# 1. Bucket (region-aware: us-east-1 must NOT send a LocationConstraint; others must).
if "${AWS[@]}" s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
    echo "= bucket $BUCKET already exists; skipping create"
elif [ "$REGION" = "us-east-1" ]; then
    run s3api create-bucket --bucket "$BUCKET"
else
    run s3api create-bucket --bucket "$BUCKET" \
        --create-bucket-configuration "LocationConstraint=$REGION"
fi

# 2. Block ALL public access.
run s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 3. Default server-side encryption (SSE-S3).
run s3api put-bucket-encryption --bucket "$BUCKET" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# 4. Lifecycle: expire telemetry objects after the retention window (rollup by deletion).
run s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" \
    --lifecycle-configuration "{\"Rules\":[{\"ID\":\"expire-telemetry\",\"Status\":\"Enabled\",\"Filter\":{\"Prefix\":\"${PREFIX}/\"},\"Expiration\":{\"Days\":${RETENTION_DAYS}}}]}"

# 5. Contributor policy: PutObject ONLY, on the prefix — nothing else (the write-only wall).
CONTRIB_DOC="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PutOnly\",\"Effect\":\"Allow\",\"Action\":\"s3:PutObject\",\"Resource\":\"${ARN_PREFIX}\"}]}"
if "${AWS[@]}" iam get-policy --policy-arn "$POLICY_ARN_PUT" >/dev/null 2>&1; then
    echo "= policy $CONTRIB_POLICY already exists; skipping (delete+recreate to change it)"
else
    run iam create-policy --policy-name "$CONTRIB_POLICY" \
        --policy-document "$CONTRIB_DOC" \
        --description "racecar telemetry: PutObject-only drop (write, no read)"
fi

# 6. Aggregator policy: Get + List, for the one identity that reduces the fleet.
AGG_DOC="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"ReadAggregate\",\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:ListBucket\"],\"Resource\":[\"arn:aws:s3:::${BUCKET}\",\"arn:aws:s3:::${BUCKET}/${PREFIX}/*\"]}]}"
if "${AWS[@]}" iam get-policy --policy-arn "$POLICY_ARN_READ" >/dev/null 2>&1; then
    echo "= policy $AGG_POLICY already exists; skipping"
else
    run iam create-policy --policy-name "$AGG_POLICY" \
        --policy-document "$AGG_DOC" \
        --description "racecar telemetry: read the aggregate (aggregator only)"
fi

# 7. Contributor IAM user + attach the put-only policy.
if "${AWS[@]}" iam get-user --user-name "$CONTRIB_USER" >/dev/null 2>&1; then
    echo "= user $CONTRIB_USER already exists; skipping create"
else
    run iam create-user --user-name "$CONTRIB_USER" \
        --tags Key=Project,Value=racecar-telemetry
fi
run iam attach-user-policy --user-name "$CONTRIB_USER" --policy-arn "$POLICY_ARN_PUT"

# 8. Access key for the contributor — guarded, so re-runs don't sprawl keys (max 2).
EXISTING_KEYS="$("${AWS[@]}" iam list-access-keys --user-name "$CONTRIB_USER" \
    --query 'AccessKeyMetadata[?Status==`Active`].AccessKeyId' --output text 2>/dev/null || true)"
if [ -n "$EXISTING_KEYS" ]; then
    echo "= user $CONTRIB_USER already has an active access key ($EXISTING_KEYS)."
    echo "  Reuse it, or rotate manually: aws iam create-access-key / delete-access-key."
elif [ "$APPLY" = 1 ]; then
    echo ""
    echo ">>> Creating the contributor access key. The SECRET is shown ONCE — store it in a"
    echo "    secret manager and distribute to contributor machines; never commit it. <<<"
    "${AWS[@]}" iam create-access-key --user-name "$CONTRIB_USER" \
        --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text
else
    echo "+ ${AWS[*]} iam create-access-key --user-name $CONTRIB_USER   (skipped in dry-run)"
fi

cat <<SUMMARY

provision_telemetry_bucket: ${APPLY:+done}${APPLY:-dry-run complete}.
  Sink config for the push/pull scripts:
    bucket=${BUCKET}  region=${REGION}  prefix=${PREFIX}  retention_days=${RETENTION_DAYS}
  Contributor (write-only): user ${CONTRIB_USER}, policy ${CONTRIB_POLICY} (s3:PutObject on ${PREFIX}/*).
  Aggregator (read): attach policy ${AGG_POLICY} to your own SSO role / identity — the script
    does not guess your Identity Center setup. Attach with:
    aws iam attach-user-policy --user-name <you> --policy-arn ${POLICY_ARN_READ}
    (or add it to the relevant permission set / role).
SUMMARY
