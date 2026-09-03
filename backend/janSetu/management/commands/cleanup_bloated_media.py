from django.core.management.base import BaseCommand
from janSetu.models import CustomUser, CivicIssue
from janSetu.storage_utils import sanitize_avatar, sanitize_issue_images

class Command(BaseCommand):
    help = "Inspects and cleans bloated base64 media from database rows, shrinking payload sizes from megabytes to kilobytes or uploading to Supabase Storage."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting JanSeva database media optimization..."))

        total_bytes_saved = 0
        users_updated = 0
        issues_updated = 0

        # 1. Clean bloated user avatars
        users = CustomUser.objects.all()
        self.stdout.write(f"Scanning {users.count()} users for bloated avatars...")
        for u in users:
            avatar = u.avatar
            if avatar and (avatar.startswith('data:image/') or len(avatar) > 25000):
                old_len = len(avatar)
                cleaned_avatar = sanitize_avatar(avatar, user_identifier=u.username)
                new_len = len(cleaned_avatar)

                u.avatar = cleaned_avatar
                u.save(update_fields=['avatar'])

                diff = old_len - new_len
                total_bytes_saved += diff
                users_updated += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  [OK] User '{u.username}' avatar optimized: {old_len:,} bytes -> {new_len:,} bytes (saved {diff:,} bytes)")
                )

        # 2. Clean bloated issue images
        issues = CivicIssue.objects.all()
        self.stdout.write(f"\nScanning {issues.count()} civic issues for bloated images...")
        for issue in issues:
            images = issue.images
            if isinstance(images, dict):
                import json
                old_json = json.dumps(images)
                old_len = len(old_json)

                # Check if any image string in images dictionary is base64 and large
                has_bloat = any(
                    isinstance(v, str) and (v.startswith('data:image/') or len(v) > 30000)
                    for v in images.values()
                )

                if has_bloat:
                    cleaned_images = sanitize_issue_images(images, issue_id=issue.id)
                    new_json = json.dumps(cleaned_images)
                    new_len = len(new_json)

                    issue.images = cleaned_images
                    issue.save(update_fields=['images'])

                    diff = old_len - new_len
                    total_bytes_saved += diff
                    issues_updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  [OK] Issue #{issue.id} images optimized: {old_len:,} bytes -> {new_len:,} bytes (saved {diff:,} bytes)")
                    )

        mb_saved = total_bytes_saved / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS("\n======================================================="))
        self.stdout.write(self.style.SUCCESS("Optimization Complete!"))
        self.stdout.write(self.style.SUCCESS(f"Users Cleaned:  {users_updated}"))
        self.stdout.write(self.style.SUCCESS(f"Issues Cleaned: {issues_updated}"))
        self.stdout.write(self.style.SUCCESS(f"Total Bandwidth Saved in DB: {mb_saved:.2f} MB ({total_bytes_saved:,} bytes)"))
        self.stdout.write(self.style.SUCCESS("=======================================================\n"))
