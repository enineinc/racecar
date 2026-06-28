"""Admin path (there is no web admin login): issue a Temporary Access Pass.

Run by an operator on the server: `manage.py issue_tap <username> [--hours N]`. Prints the
pass ONCE; deliver it out of band. The user redeems it at /recovery/ to enroll a new
hardware key after losing every key."""
import datetime
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.authserver.models import TemporaryAccessPass


class Command(BaseCommand):
    help = "Issue a single-use, time-limited Temporary Access Pass for a user."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--hours", type=int, default=1)

    def handle(self, *args, **options):
        user_model = get_user_model()
        field = user_model.USERNAME_FIELD
        try:
            user = user_model.objects.get(**{field: options["username"]})
        except user_model.DoesNotExist as exc:
            raise CommandError(f"no such user: {options['username']}") from exc
        code = secrets.token_hex(8)
        TemporaryAccessPass.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=timezone.now() + datetime.timedelta(hours=options["hours"]),
        )
        hours = options["hours"]
        self.stdout.write(f"TAP for {options['username']} (valid {hours}h): {code}")
