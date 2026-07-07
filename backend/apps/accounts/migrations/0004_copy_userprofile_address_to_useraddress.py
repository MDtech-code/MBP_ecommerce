# accounts/migrations/0004_copy_userprofile_address_to_useraddress.py

from django.db import migrations


def copy_addresses_forward(apps, schema_editor):
    """
    Copy address data from UserProfile into UserAddress.
    Only creates a UserAddress if the profile has address_line1
    populated — skip empty profiles.
    Sets is_default=True for all migrated addresses since
    each user had only one address before this migration.
    """
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserAddress = apps.get_model("accounts", "UserAddress")

    profiles_with_address = UserProfile.objects.exclude(
        address_line1=""
    ).select_related("user")

    addresses_to_create = []

    for profile in profiles_with_address:
        addresses_to_create.append(
            UserAddress(
                user=profile.user,
                label="home",          # sensible default for migrated data
                address_line1=profile.address_line1,
                address_line2=profile.address_line2,
                city=profile.city,
                province=profile.province,
                postal_code=profile.postal_code,
                country=profile.country,
                is_default=True,       # was their only address — make it default
            )
        )

    UserAddress.objects.bulk_create(addresses_to_create)
    print(f"\n[Migration] Copied {len(addresses_to_create)} addresses to UserAddress.")


def copy_addresses_backward(apps, schema_editor):
    """
    Reverse migration — copy first address back to UserProfile.
    Restores address data if migration is reversed.
    """
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserAddress = apps.get_model("accounts", "UserAddress")

    for address in UserAddress.objects.filter(is_default=True).select_related("user"):
        try:
            profile = UserProfile.objects.get(user=address.user)
            profile.address_line1 = address.address_line1
            profile.address_line2 = address.address_line2
            profile.city = address.city
            profile.province = address.province
            profile.postal_code = address.postal_code
            profile.country = address.country
            profile.save(update_fields=[
                "address_line1",
                "address_line2",
                "city",
                "province",
                "postal_code",
                "country",
            ])
        except UserProfile.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_add_useraddress_model"),
    ]

    operations = [
        migrations.RunPython(
            copy_addresses_forward,
            reverse_code=copy_addresses_backward,
        ),
    ]